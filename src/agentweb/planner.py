from __future__ import annotations

import re
import time
import uuid
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from threading import RLock
from typing import Any

from .skills import Skill, SkillRegistry, built_in_skill_registry

_URL_RE = re.compile(r"https?://[^\s)\]>]+")
_BROWSER_INTENT_RE = re.compile(r"\b(?:javascript|js-rendered|render|rendered|click|login|log\s+in|form|pagination|interact|browser)\b")


@dataclass(frozen=True)
class PlanStep:
    type: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Plan:
    id: str
    steps: tuple[PlanStep, ...]
    estimated_mode: str
    intent: str
    skill: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["steps"] = [step.to_dict() for step in self.steps]
        return payload


@dataclass(frozen=True)
class StoredPlan:
    plan: Plan
    task: str
    inputs: dict[str, Any]
    created_at: float
    expires_at: float


class PlanStore:
    """Bounded tenant-namespaced plan storage; plan inputs never reach disk."""

    def __init__(self, ttl_seconds: int = 900, max_plans: int = 256, clock=time.time) -> None:
        if int(ttl_seconds) < 1:
            raise ValueError("ttl_seconds must be positive")
        if int(max_plans) < 1:
            raise ValueError("max_plans must be positive")
        self.ttl_seconds = int(ttl_seconds)
        self.max_plans = int(max_plans)
        self._clock = clock
        self._plans: dict[tuple[str, str], StoredPlan] = {}
        self._lock = RLock()

    def _purge_expired(self, now: float) -> None:
        expired = [key for key, record in self._plans.items() if record.expires_at <= now]
        for key in expired:
            self._plans.pop(key, None)

    def put(self, org_id: str, plan: Plan, task: str, inputs: dict[str, Any]) -> StoredPlan:
        now = float(self._clock())
        record = StoredPlan(plan, task, deepcopy(inputs), now, now + self.ttl_seconds)
        key = (str(org_id), plan.id)
        with self._lock:
            self._purge_expired(now)
            self._plans[key] = record
            if len(self._plans) > self.max_plans:
                oldest = min(self._plans.items(), key=lambda item: item[1].created_at)[0]
                self._plans.pop(oldest, None)
        return record

    def get(self, org_id: str, plan_id: str) -> StoredPlan | None:
        now = float(self._clock())
        key = (str(org_id), str(plan_id))
        with self._lock:
            self._purge_expired(now)
            return self._plans.get(key)

    def delete(self, org_id: str, plan_id: str) -> bool:
        with self._lock:
            return self._plans.pop((str(org_id), str(plan_id)), None) is not None

    def size(self) -> int:
        now = float(self._clock())
        with self._lock:
            self._purge_expired(now)
            return len(self._plans)


class Planner:
    """Deterministic local planner; no task content is persisted."""

    def __init__(self, skills: SkillRegistry | None = None) -> None:
        self.skills = skills or built_in_skill_registry()

    @staticmethod
    def _intent(task: str) -> str:
        lowered = task.lower()
        if any(term in lowered for term in ("compare", "comparison", " versus ", " vs ", "options", "alternatives")):
            return "comparison"
        if any(term in lowered for term in ("monitor", "watch", "alert", "notify when")):
            return "monitoring"
        if any(term in lowered for term in ("over time", "historical", "history", "trend", "timeline")):
            return "longitudinal"
        if any(term in lowered for term in ("find", "lookup", "what is", "who is", "when is", "where is")):
            return "lookup"
        return "lookup"

    @staticmethod
    def _mode(intent: str, task: str) -> str:
        lowered = task.lower()
        if intent in {"comparison", "longitudinal"} or any(term in lowered for term in ("latest", "current", "breaking")):
            return "dive"
        if intent == "lookup" and len(task) < 120:
            return "focus"
        return "focus"

    @staticmethod
    def _requires_browser(task: str) -> bool:
        return _BROWSER_INTENT_RE.search(task.lower()) is not None

    @staticmethod
    def _generic_steps(task: str, mode: str, inputs: dict[str, Any]) -> tuple[PlanStep, ...]:
        urls = list(dict.fromkeys(_URL_RE.findall(task)))
        max_sources = 5 if mode == "dive" else 3
        steps: list[PlanStep] = []
        if urls:
            step_type = "browser" if Planner._requires_browser(task) else "extract"
            steps.append(PlanStep(step_type, {"urls": urls[:max_sources], "max_sources": max_sources, "inputs": dict(inputs)}))
        steps.extend(
            [
                PlanStep("search", {"limit": 5 if mode in {"focus", "dive"} else 3}),
                PlanStep("rank", {}),
                PlanStep("synthesize", {}),
            ]
        )
        return tuple(steps)

    def plan(
        self,
        task: str,
        mode: str | None = None,
        skill: str | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> Plan:
        if not isinstance(task, str) or not task.strip() or len(task.strip()) > 2000:
            raise ValueError("task must contain between 1 and 2000 characters")
        task = task.strip()
        if mode is not None and mode not in {"flash", "focus", "dive"}:
            raise ValueError("mode must be one of: flash, focus, dive")
        if inputs is not None and not isinstance(inputs, dict):
            raise ValueError("inputs must be an object")
        inputs = inputs or {}
        selected: Skill | None = None
        if skill is not None:
            if not isinstance(skill, str) or not skill.strip():
                raise ValueError("skill must be a non-empty string")
            selected = self.skills.get(skill.strip())
            if selected is None:
                raise ValueError(f"unknown skill: {skill.strip()}")
        else:
            selected = self.skills.match(task)
        intent = self._intent(task)
        estimated_mode = mode or (selected.default_mode if selected else self._mode(intent, task))
        if selected:
            raw_steps = selected.build_steps(task, inputs)
            task_urls = list(dict.fromkeys(_URL_RE.findall(task)))[:5 if estimated_mode == "dive" else 3]
            for item in raw_steps:
                if item["type"] == "extract" and task_urls:
                    item.setdefault("params", {})["urls"] = task_urls
                    if Planner._requires_browser(task):
                        item["type"] = "browser"
            steps = tuple(PlanStep(item["type"], dict(item.get("params", {}))) for item in raw_steps)
        else:
            steps = self._generic_steps(task, estimated_mode, inputs)
        return Plan(
            id="plan_" + uuid.uuid4().hex[:16],
            steps=steps,
            estimated_mode=estimated_mode,
            intent=intent,
            skill=selected.name if selected else None,
        )
