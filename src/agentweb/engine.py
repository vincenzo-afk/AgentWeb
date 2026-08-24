"""Phase 0/1 orchestration for grounded research and page monitoring."""

from __future__ import annotations

import os
import re
import time
import uuid
from urllib.parse import urlparse

from .alerting import DeliveryResult, send_webhook
from .auth import KeyStore
from .browser import BrowserEngine
from .browser_sessions import BrowserSessionStore
from .crawler import Crawler
from .credentials import BrowserCredentialStore
from .fetch import extract_metadata, fetch_url, html_to_text, validate_url
from .memory import MemoryStore
from .maintenance import purge_retention
from .metrics import MetricStore, MetricsRegistry, PostgresMetricStore
from .models import Citation, Monitor, SolveResponse, Source, utc_now
from .normalizer import normalize
from .synthesis import synthesize
from .parser import parse
from .ranking import rank
from .redaction import redact_text, redact_url
from .rdbms import PostgresDistributedQueue
from .scheduler import Scheduler
from .search import SearchProvider, build_search_provider, search
from .secrets import SecretProvider, build_provider
from .trace import Span, TraceStore
from .trust_engine import TrustEngine

URL_RE = re.compile(r"https?://[^\s)\]>]+")
_MISSING_FIELD = object()


class AgentWebEngine:
    def __init__(
        self,
        memory: MemoryStore | None = None,
        secret_provider: SecretProvider | None = None,
        search_provider: SearchProvider | None = None,
        queue_coordinator: object | None = None,
    ) -> None:
        self.memory = memory or MemoryStore()
        self.queue_coordinator = queue_coordinator
        metric_backend = (
            PostgresMetricStore(queue_coordinator)
            if isinstance(queue_coordinator, PostgresDistributedQueue)
            else MetricStore(self.memory.path)
        )
        self.metrics = MetricsRegistry(metric_backend)
        self.secret_provider = secret_provider or build_provider()
        self.credentials = BrowserCredentialStore(self.memory.path, self.secret_provider)
        self.session_states = BrowserSessionStore(self.memory.path, self.secret_provider)
        self.search_provider = search_provider or build_search_provider(self.secret_provider)
        self.traces = TraceStore(self.memory.path)
        self.audit_store = KeyStore(self.memory.path)
        self.trust_engine = TrustEngine(
            blocked_domains={domain for domain in os.getenv("AGENTWEB_BLOCKED_DOMAINS", "").split(",") if domain}
        )
        self.crawler = Crawler(self.trust_engine, memory=self.memory, coordinator=queue_coordinator)
        self.browser = BrowserEngine(self.trust_engine)
        self.scheduler = Scheduler(self.memory, self.check_monitor, webhook_sender=self._deliver_webhook, retention_runner=self.run_retention, coordinator=queue_coordinator)

    @staticmethod
    def _trust_score(url: str, title: str = "") -> float:
        host = urlparse(url).netloc.lower().split(":", 1)[0]
        score = 0.55
        if host.endswith(".gov") or host.endswith(".edu"):
            score += 0.30
        elif host.endswith(".org"):
            score += 0.10
        if title:
            score += 0.05
        if url.startswith("https://"):
            score += 0.05
        return round(min(score, 0.99), 2)

    @staticmethod
    def _source_id(url: str) -> str:
        return "src_" + uuid.uuid5(uuid.NAMESPACE_URL, url).hex[:12]

    @staticmethod
    def _structured_projection(parsed: object, text: str) -> dict[str, object]:
        return {
            "title": getattr(parsed, "title", ""),
            "text": text,
            "links": list(getattr(parsed, "links", []) or []),
            "tables": [table[:20] for table in (getattr(parsed, "tables", []) or [])[:5]],
            "entities": list((getattr(parsed, "entities", []) or [])[:30]),
            "data": getattr(parsed, "data", None),
        }

    @staticmethod
    def _span(component: str, operation: str, started: float, status: str, input_summary: str, output_summary: str) -> Span:
        return Span(
            component=component,
            operation=operation,
            start_time=started,
            end_time=time.time(),
            status=status,
            input_summary=redact_text(input_summary),
            output_summary=redact_text(output_summary),
        )

    @staticmethod
    def _reuse_window(task: str) -> int:
        lowered = task.lower()
        if any(term in lowered for term in ("price", "cost", "stock", "availability", "available", "sale")):
            return 3_600
        if any(term in lowered for term in ("latest", "today", "current", "breaking")):
            return 900
        if any(term in lowered for term in ("history", "historical", "background")):
            return 7 * 86_400
        return 86_400

    def _source_from_snapshot(self, snapshot: dict[str, str]) -> Source | None:
        content = snapshot.get("content", "")
        surface = self.trust_engine.should_surface(content)
        if not surface.allowed:
            return None
        return Source(
            id=self._source_id(snapshot["target"]),
            url=snapshot["target"],
            title="",
            snippet=content[:240],
            trust_score=self._trust_score(snapshot["target"]),
            content_type="text/plain",
            extraction_confidence=0.70,
        )

    def _source_from_url(self, url: str, org_id: str = "development") -> Source | None:
        decision = self.trust_engine.should_fetch(url)
        if not decision.allowed:
            return None
        result = fetch_url(url, trust_engine=self.trust_engine)
        if result.error and not result.body:
            return None
        parsed = parse(result.body.encode("utf-8"), result.content_type)
        title = parsed.title
        if not title:
            title, _ = extract_metadata(result.body)
        text = parsed.text or html_to_text(result.body)
        surface = self.trust_engine.should_surface(text)
        if not surface.allowed:
            return None
        self.memory.snapshot(url, text, utc_now(), org_id)
        structured_data = {
            "tables": [table[:20] for table in parsed.tables[:5]],
            "entities": parsed.entities[:30],
        }
        if not structured_data["tables"] and not structured_data["entities"]:
            structured_data = None
        return Source(
            id=self._source_id(result.url),
            url=result.url,
            title=title,
            snippet=text[:240],
            trust_score=self._trust_score(result.url, title),
            content_type=result.content_type,
            extraction_confidence=round(0.85 if text else 0.20, 2),
            structured_data=structured_data,
        )

    def browser_open(self, url: str, actions: list[dict] | None = None, org_id: str = "development", credential_id: str | None = None, session_state_id: str | None = None):
        """Render a page through the isolated browser adapter and persist a trace."""
        started = time.time()
        execution_id = "exec_" + uuid.uuid4().hex[:16]
        try:
            credential = None
            if credential_id:
                credential = self.credentials.resolve(org_id, credential_id)
                if credential is None:
                    raise ValueError("browser credential not found")
            storage_state = None
            if session_state_id:
                storage_state = self.session_states.resolve(org_id, session_state_id, url)
                if storage_state is None:
                    raise ValueError("browser session state not found")
            session = self.browser.open(url, actions, credential, storage_state)
            self.traces.save(
                execution_id,
                [self._span("browser", "open", started, session.status, redact_url(url), f"{len(session.actions)} action(s)")],
                                    status=session.status,
                    org_id=org_id,
                )

            return session
        except Exception as error:
            self.traces.save(
                execution_id,
                [self._span("browser", "open", started, "failed", redact_url(url), redact_text(str(error)))],
                                    status="failed",
                    org_id=org_id,
                )

            raise

    def extract(self, url: str, requested_schema: dict | None = None) -> dict:
        validate_url(url)
        decision = self.trust_engine.should_fetch(url)
        if not decision.allowed:
            raise RuntimeError(decision.reason or "URL rejected by trust engine")
        result = fetch_url(url, trust_engine=self.trust_engine)
        if result.error:
            raise RuntimeError(f"could not fetch URL: {redact_text(result.error)}")
        parsed = parse(result.body.encode("utf-8"), result.content_type)
        title = parsed.title
        description = extract_metadata(result.body)[1]
        text = parsed.text or html_to_text(result.body)
        base_confidence = 0.85 if text else 0.20
        confidence_reasons = ["main text extracted" if text else "main text is empty"]
        if parsed.parse_warnings:
            base_confidence = max(0.20, base_confidence - 0.20 * len(parsed.parse_warnings))
            confidence_reasons.append(f"{len(parsed.parse_warnings)} parse warning(s)")
        field_confidence = {
            "title": 0.95 if title else 0.20,
            "description": 0.85 if description else 0.20,
            "text": round(base_confidence, 2),
            "links": 0.85 if parsed.links else 0.20,
        }
        source_spans = []
        if title:
            source_spans.append({"field": "title", "source": "title", "span": [0, len(title)], "value": title})
        if text:
            source_spans.append({"field": "text", "source": "text", "span": [0, min(len(text), 200)], "value": text[:200]})
        data = {
            "url": result.url,
            "status": result.status,
            "title": title,
            "description": description,
            "text": text,
            "links": parsed.links,
            "tables": parsed.tables,
            "entities": parsed.entities,
            "source_spans": source_spans,
            "parse_warnings": parsed.parse_warnings,
            "field_confidence": field_confidence,
            "confidence": round(sum(field_confidence.values()) / len(field_confidence), 2),
            "confidence_reasons": confidence_reasons,
            "trust_score": self._trust_score(result.url, title),
        }
        if requested_schema:
            structured: dict[str, dict] = {}
            for field, expected_type in requested_schema.items():
                candidate = title if field.lower() == "title" else text[:200]
                normalized_field = normalize(candidate, str(expected_type))
                structured[field] = {
                    **normalized_field.__dict__,
                    "source_span": {"source": "title" if field.lower() == "title" else "text", "span": [0, len(candidate)], "value": candidate},
                }
            data["data"] = structured
            data["field_confidence"].update({field: value["confidence"] for field, value in structured.items()})
            data["confidence"] = round(sum(data["field_confidence"].values()) / len(data["field_confidence"]), 2)
        return data

    def solve(self, task: str, mode: str = "focus", org_id: str = "development", output_format: str = "text") -> SolveResponse:
        task = task.strip()
        if not task or len(task) > 2000:
            raise ValueError("task must contain between 1 and 2000 characters")
        if mode not in {"flash", "focus", "dive"}:
            raise ValueError("mode must be one of: flash, focus, dive")

        execution_id = self.traces.start()
        spans: list[Span] = []
        started = time.time()
        requested_urls = list(dict.fromkeys(URL_RE.findall(task)))
        spans.append(self._span("planner", "classify", started, "complete", "task received", "direct URLs or search"))
        source_candidates: list[Source] = []
        reuse_hits = 0
        for url in requested_urls[:5 if mode == "dive" else 3]:
            fetch_started = time.time()
            cached = self.memory.reusable_snapshot(url, org_id, self._reuse_window(task))
            reuse_hits += int(cached is not None)
            source = self._source_from_snapshot(cached) if cached else self._source_from_url(url, org_id)
            spans.append(
                self._span(
                    "extractor",
                    "reuse_snapshot" if cached else "fetch_and_parse",
                    fetch_started,
                    "reused" if cached and source else "complete" if source else "degraded",
                    url,
                    "fresh snapshot reused" if cached and source else "source accepted" if source else "source unavailable or blocked",
                )
            )
            if source:
                source_candidates.append(source)

        if not source_candidates:
            search_started = time.time()
            search_results = search(task, limit=5 if mode in {"focus", "dive"} else 3, provider=self.search_provider)
            spans.append(self._span("search", "search", search_started, "complete", task, f"{len(search_results)} result(s)"))
            for item in search_results:
                source_candidates.append(
                    Source(
                        id=self._source_id(item["url"]),
                        url=item["url"],
                        title=item.get("title", ""),
                        snippet=item.get("snippet", ""),
                        trust_score=self._trust_score(item["url"], item.get("title", "")),
                        published_at=item.get("published_at"),
                        content_type=item.get("content_type"),
                    )
                )

        ranked = rank(source_candidates, task)
        spans.append(self._span("ranking", "rank_sources", time.time(), "complete", f"{len(source_candidates)} candidates", f"{len(ranked)} ranked"))
        limit = 1 if mode == "flash" else 3 if mode == "focus" else 5
        synthesis_result = synthesize([item for item in ranked if item.include][:limit], task, output_format)
        spans.append(
            self._span(
                "synthesis",
                "synthesize",
                time.time(),
                "complete",
                task,
                f"{len(synthesis_result.citations)} citation(s); evidence={synthesis_result.evidence_score:.2f}",
            )
        )
        self.traces.save(execution_id, spans, org_id=org_id)
        self.memory.record_usage(org_id, mode)
        self.metrics.gauge("memory_reuse_rate", reuse_hits / max(1, len(requested_urls)), {"org_id": org_id})
        self.metrics.observe("cost_per_run", {"flash": 0.01, "focus": 0.05, "dive": 0.20}[mode], {"mode": mode, "org_id": org_id})
        return SolveResponse(
            execution_id=execution_id,
            mode=mode,
            answer=synthesis_result.answer,
            sources=synthesis_result.sources,
            citations=synthesis_result.citations,
            insufficient_evidence=synthesis_result.insufficient_evidence,
            output_format=synthesis_result.output_format,
            evidence_score=synthesis_result.evidence_score,
            conflicts=synthesis_result.conflicts or [],
            structured_output=synthesis_result.structured_output or {},
        )

    def run_retention(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("retention payload must be an object")
        target_org = payload.get("org_id")
        if target_org is not None:
            target_org = str(target_org).strip() or None
        options = {
            "snapshot_retention_days": int(payload.get("snapshot_retention_days", 90)),
            "crawl_retention_days": int(payload.get("crawl_retention_days", 90)),
            "trace_retention_days": int(payload.get("trace_retention_days", 30)),
            "metric_retention_days": int(payload.get("metric_retention_days", 30)),
            "audit_retention_days": int(payload.get("audit_retention_days", 730)),
        }
        if any(value < 0 for value in options.values()):
            raise ValueError("retention days cannot be negative")
        return purge_retention(self.memory, self.traces, **options, org_id=target_org, metrics=self.metrics, audit_store=self.audit_store)

    def schedule_retention(
        self,
        target_org: str | None = None,
        *,
        snapshot_retention_days: int = 90,
        crawl_retention_days: int = 90,
        trace_retention_days: int = 30,
        metric_retention_days: int = 30,
        audit_retention_days: int = 730,
        run_at: float | None = None,
    ) -> str:
        options = {
            "snapshot_retention_days": int(snapshot_retention_days),
            "crawl_retention_days": int(crawl_retention_days),
            "trace_retention_days": int(trace_retention_days),
            "metric_retention_days": int(metric_retention_days),
            "audit_retention_days": int(audit_retention_days),
        }
        if any(value < 0 for value in options.values()):
            raise ValueError("retention days cannot be negative")
        payload = {"org_id": target_org, **options}
        job_id = self.memory.enqueue_retention_job(target_org, **options, run_at=run_at)
        if self.queue_coordinator is not None:
            self.queue_coordinator.enqueue_retention_job(job_id, target_org or "system", payload, run_at=run_at)
        return job_id

    def create_monitor(self, task: str, frequency: str = "hourly", webhook_url: str | None = None, org_id: str = "development", change_policy: dict | None = None) -> Monitor:
        task = task.strip()
        if not task or len(task) > 2000:
            raise ValueError("task must contain between 1 and 2000 characters")
        if frequency not in {"minutely", "hourly", "daily"}:
            raise ValueError("frequency must be one of: minutely, hourly, daily")
        target_url = next(iter(URL_RE.findall(task)), None)
        normalized_policy = self._validate_change_policy(change_policy)
        if webhook_url:
            validate_url(webhook_url)
            webhook_decision = self.trust_engine.should_fetch(webhook_url)
            if not webhook_decision.allowed:
                raise ValueError(webhook_decision.reason or "webhook URL rejected by trust engine")
        monitor = Monitor(
            id="mon_" + uuid.uuid4().hex[:16],
            task=task,
            frequency=frequency,
            target_url=target_url,
            webhook_url=webhook_url,
            change_policy=normalized_policy,
            org_id=org_id,
        )
        local_job_id = self.memory.create_monitor(monitor)
        if self.queue_coordinator is not None:
            try:
                self.queue_coordinator.sync_monitor(monitor)
                self.queue_coordinator.enqueue_monitor_job(local_job_id, org_id, monitor.id, frequency)
            except Exception:
                self.memory.delete_monitor(monitor.id, org_id)
                raise
        self.traces.save(monitor.id, [self._span("monitor", "create", time.time(), "complete", task, monitor.id)], org_id=org_id)
        return monitor

    def _deliver_webhook(self, delivery: dict) -> object:
        destination = delivery["url"]
        decision = self.trust_engine.should_fetch(destination)
        if not decision.allowed:
            return DeliveryResult(False, 0, error=decision.reason or "webhook URL rejected by trust engine")
        secret = self.secret_provider.get("WEBHOOK_SIGNING_KEY", required=False) or self.secret_provider.get("AGENTWEB_WEBHOOK_SIGNING_KEY", required=False) or ""
        return send_webhook(destination, delivery["payload"], secret, max_attempts=1)

    @staticmethod
    def _validate_change_policy(policy: dict | None) -> dict | None:
        if policy is None:
            return None
        if not isinstance(policy, dict):
            raise ValueError("change_policy must be an object")
        allowed = {
            "kind", "absolute_delta", "relative_delta_percent", "required_state", "ignore_whitespace",
            "field_path", "expected_type",
        }
        unknown = set(policy) - allowed
        if unknown:
            raise ValueError(f"unsupported change_policy field: {sorted(unknown)[0]}")
        normalized = dict(policy)
        kind = normalized.get("kind")
        if kind is not None and kind not in {"full_content", "price", "availability", "structured_field"}:
            raise ValueError("change_policy.kind must be full_content, price, availability, or structured_field")
        for name in ("absolute_delta", "relative_delta_percent"):
            if name in normalized:
                value = normalized[name]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                    raise ValueError(f"change_policy.{name} must be a non-negative number")
                normalized[name] = float(value)
        if normalized.get("relative_delta_percent", 0) > 10000:
            raise ValueError("change_policy.relative_delta_percent is too large")
        if "required_state" in normalized:
            state = str(normalized["required_state"]).strip().lower()
            if state not in {"in stock", "out of stock", "available", "unavailable", "sold out"}:
                raise ValueError("change_policy.required_state is not supported")
            normalized["required_state"] = state
        if "ignore_whitespace" in normalized and not isinstance(normalized["ignore_whitespace"], bool):
            raise ValueError("change_policy.ignore_whitespace must be boolean")
        if kind == "structured_field":
            field_path = normalized.get("field_path")
            if not isinstance(field_path, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*(?:\.(?:[A-Za-z_][A-Za-z0-9_-]*|[0-9]+))*(?:\.[0-9]+)?", field_path.strip()):
                raise ValueError("change_policy.field_path must be a dotted object/list path")
            normalized["field_path"] = field_path.strip()
            expected_type = str(normalized.get("expected_type", "string")).strip().lower()
            if expected_type not in {"string", "entity", "price", "date"}:
                raise ValueError("change_policy.expected_type must be string, entity, price, or date")
            normalized["expected_type"] = expected_type
            if "required_state" in normalized:
                raise ValueError("change_policy.required_state is not supported for structured_field")
            if expected_type != "price" and ("absolute_delta" in normalized or "relative_delta_percent" in normalized):
                raise ValueError("structured_field numeric thresholds require expected_type price")
        elif "field_path" in normalized or "expected_type" in normalized:
            raise ValueError("field_path and expected_type require kind structured_field")
        return normalized or None

    @staticmethod
    def _field_value(data: object | None, field_path: str) -> object:
        current = data
        for segment in field_path.split("."):
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            elif isinstance(current, list) and segment.isdigit() and int(segment) < len(current):
                current = current[int(segment)]
            else:
                return _MISSING_FIELD
        return current

    @staticmethod
    def _structured_value(raw: object, expected_type: str, ignore_whitespace: bool) -> object:
        if raw is _MISSING_FIELD:
            return raw
        if expected_type in {"price", "date", "entity"}:
            normalized = normalize(raw, expected_type)
            value = normalized.value if normalized.normalized else raw
            return value.casefold() if expected_type == "entity" and isinstance(value, str) else value
        value = str(raw)
        return re.sub(r"\s+", " ", value).strip() if ignore_whitespace else value

    @staticmethod
    def _meaningful_change(
        task: str,
        previous: str | None,
        current: str,
        policy: dict | None = None,
        previous_structured: object | None = None,
        current_structured: object | None = None,
    ) -> tuple[bool, str]:
        if previous is None:
            return False, "initial_snapshot"
        policy = policy or {}
        lowered = task.lower()
        kind = policy.get("kind")
        if kind is None:
            kind = "price" if any(term in lowered for term in ("price", "cost", "sale")) else "availability" if any(term in lowered for term in ("availability", "available", "stock", "sold out")) else "full_content"
        if kind == "structured_field":
            path = str(policy["field_path"])
            expected_type = str(policy.get("expected_type", "string"))
            before = AgentWebEngine._structured_value(AgentWebEngine._field_value(previous_structured, path), expected_type, bool(policy.get("ignore_whitespace")))
            after = AgentWebEngine._structured_value(AgentWebEngine._field_value(current_structured, path), expected_type, bool(policy.get("ignore_whitespace")))
            if before is _MISSING_FIELD or after is _MISSING_FIELD:
                return before != after, "structured_field"
            if expected_type == "price" and isinstance(before, (int, float)) and isinstance(after, (int, float)):
                delta = abs(float(after) - float(before))
                absolute = policy.get("absolute_delta")
                relative = policy.get("relative_delta_percent")
                if absolute is not None or relative is not None:
                    absolute_hit = absolute is not None and delta > 0 and delta >= float(absolute)
                    relative_hit = relative is not None and delta > 0 and (abs(float(before)) == 0 or delta / abs(float(before)) * 100 >= float(relative))
                    return absolute_hit or relative_hit, "structured_field_threshold"
            return before != after, "structured_field"
        if kind == "price":
            pattern = r"(?:₹|\$|€|£)\s?\d[\d,]*(?:\.\d+)?"
            parse_price = lambda value: [float(item.replace(",", "").replace("₹", "").replace("$", "").replace("€", "").replace("£", "").strip()) for item in re.findall(pattern, value)]
            before, after = parse_price(previous), parse_price(current)
            if before or after:
                if len(before) != len(after):
                    return True, "price"
                differences = [abs(left - right) for left, right in zip(before, after)]
                absolute = policy.get("absolute_delta")
                relative = policy.get("relative_delta_percent")
                if absolute is not None and any(delta > 0 and delta >= absolute for delta in differences):
                    return True, "price"
                if relative is not None and any(delta > 0 and ((abs(left) == 0) or (abs(left) > 0 and delta / abs(left) * 100 >= relative)) for left, delta in zip(before, differences)):
                    return True, "price"
                if absolute is None and relative is None:
                    return before != after, "price"
                return False, "price_threshold"
        if kind == "availability":
            pattern = r"\b(?:in stock|out of stock|available|unavailable|sold out)\b"
            before = {item.lower() for item in re.findall(pattern, previous, re.IGNORECASE)}
            after = {item.lower() for item in re.findall(pattern, current, re.IGNORECASE)}
            required = policy.get("required_state")
            if required:
                return required in after and required not in before, "availability_target"
            if before or after:
                return before != after, "availability"
        if policy.get("ignore_whitespace"):
            normalize_text = lambda value: re.sub(r"\s+", " ", value).strip()
            return normalize_text(previous) != normalize_text(current), "full_content"
        return previous != current, "full_content"

    def check_monitor(self, monitor: Monitor) -> Monitor:
        if monitor.status != "active":
            return monitor
        now = utc_now()
        monitor.last_checked_at = now
        if not monitor.target_url:
            monitor.last_event = "check_failed"
            monitor.last_error = "monitor task does not include a direct URL"
            self.memory.update_monitor(monitor)
            self.traces.save(monitor.id, [self._span("monitor", "check", time.time(), monitor.last_event, monitor.task, monitor.last_error)], org_id=monitor.org_id)
            self.memory.record_usage(monitor.org_id, "monitor_checks")
            return monitor
        decision = self.trust_engine.should_fetch(monitor.target_url)
        if not decision.allowed:
            monitor.last_event = "check_failed"
            monitor.last_error = decision.reason
            self.memory.update_monitor(monitor)
            self.traces.save(monitor.id, [self._span("monitor", "check", time.time(), monitor.last_event, monitor.target_url, monitor.last_error)], org_id=monitor.org_id)
            self.memory.record_usage(monitor.org_id, "monitor_checks")
            return monitor
        result = fetch_url(monitor.target_url, trust_engine=self.trust_engine)
        if result.error:
            monitor.last_event = "check_failed"
            monitor.last_error = redact_text(result.error)
            self.memory.update_monitor(monitor)
            self.traces.save(monitor.id, [self._span("monitor", "check", time.time(), monitor.last_event, monitor.target_url, monitor.last_error)], org_id=monitor.org_id)
            self.memory.record_usage(monitor.org_id, "monitor_checks")
            return monitor
        monitor.last_error = None
        parsed = parse(result.body.encode("utf-8"), result.content_type)
        content = parsed.text or html_to_text(result.body)
        structured_data = self._structured_projection(parsed, content)
        previous = self.memory.get_latest(monitor.target_url, monitor.org_id)
        snapshot_changed = self.memory.save_snapshot(
            key=monitor.target_url,
            url=monitor.target_url,
            content=content,
            captured_at=now,
            org_id=monitor.org_id,
            structured_data=structured_data,
        )
        changed, change_policy_name = self._meaningful_change(
            monitor.task,
            previous["content"] if previous else None,
            content,
            monitor.change_policy,
            previous.get("structured_data") if previous else None,
            structured_data,
        )
        monitor.last_event = "change_detected" if changed else "no_change"
        if changed:
            monitor.last_change_at = now
            if monitor.webhook_url:
                secret = self.secret_provider.get("WEBHOOK_SIGNING_KEY", required=False) or self.secret_provider.get("AGENTWEB_WEBHOOK_SIGNING_KEY", required=False) or ""
                if not secret:
                    monitor.last_error = "webhook signing secret is not configured"
                    monitor.last_delivery_status = "blocked"
                    monitor.last_delivery_error = monitor.last_error
                else:
                    payload = {
                        "event": "monitor.change_detected",
                        "monitor_id": monitor.id,
                        "timestamp": now,
                        "diff": {
                            "target": monitor.target_url,
                            "from_hash": previous["content_hash"] if previous else None,
                            "to_hash": self.memory.get_latest(monitor.target_url, monitor.org_id)["content_hash"],
                        },
                    }
                    delivery_job_id = "job_" + uuid.uuid4().hex[:16]
                    monitor.last_delivery_id = self.memory.enqueue_webhook_delivery(
                        monitor.org_id, monitor.id, monitor.webhook_url, payload, job_id=delivery_job_id
                    )
                    if self.queue_coordinator is not None:
                        try:
                            self.queue_coordinator.enqueue_webhook_delivery(
                                delivery_job_id, monitor.org_id, monitor.id, monitor.webhook_url, payload
                            )
                        except Exception as error:
                            self.memory.cancel_job(delivery_job_id, monitor.org_id)
                            monitor.last_delivery_status = "blocked"
                            monitor.last_delivery_error = "distributed queue unavailable"
                            monitor.last_error = redact_text(str(error))
                        else:
                            monitor.last_delivery_status = "pending"
                            monitor.last_delivery_attempts = 0
                            monitor.last_delivery_error = None
                    else:
                        monitor.last_delivery_status = "pending"
                        monitor.last_delivery_attempts = 0
                        monitor.last_delivery_error = None
        self.memory.update_monitor(monitor)
        self.traces.save(monitor.id, [self._span("monitor", "check", time.time(), monitor.last_event, monitor.target_url, f"{monitor.last_event}; policy={change_policy_name}; snapshot_changed={snapshot_changed}")], org_id=monitor.org_id)
        self.memory.record_usage(monitor.org_id, "monitor_checks")
        return monitor
