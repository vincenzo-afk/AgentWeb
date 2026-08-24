from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from typing import Any

from .vector_store import VectorStore


@dataclass(frozen=True)
class Skill:
    """A privacy-safe reusable planning template.

    Skills contain only generic metadata and bounded plan steps. Task content is
    supplied at planning time and is never written to the registry.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    plan_template: tuple[dict[str, Any], ...]
    keywords: tuple[str, ...] = ()
    success_rate: float = 0.0
    default_mode: str = "focus"

    def build_steps(self, task: str, inputs: dict[str, Any]) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        for template in self.plan_template:
            step = deepcopy(template)
            params = step.setdefault("params", {})
            params.setdefault("task", task)
            params.setdefault("inputs", deepcopy(inputs))
            steps.append(step)
        return steps


class SkillRegistry:
    """Thread-safe registry with deterministic similarity matching."""

    def __init__(self, skills: list[Skill] | None = None, vector_store: VectorStore | None = None) -> None:
        self._skills: dict[str, Skill] = {}
        self._lock = RLock()
        self.vectors = vector_store or VectorStore()
        for skill in skills or []:
            self.register(skill)

    def register(self, skill: Skill) -> None:
        if not isinstance(skill, Skill):
            raise TypeError("skill must be a Skill")
        name = skill.name.strip()
        if not name or len(name) > 100:
            raise ValueError("skill name must contain between 1 and 100 characters")
        if not skill.description.strip():
            raise ValueError("skill description must not be empty")
        if skill.default_mode not in {"flash", "focus", "dive"}:
            raise ValueError("skill default_mode must be flash, focus, or dive")
        if not 0.0 <= float(skill.success_rate) <= 1.0:
            raise ValueError("skill success_rate must be between 0 and 1")
        with self._lock:
            self._skills[name] = skill
            self.vectors.upsert("skills", name, f"{name} {skill.description}", {"name": name, "success_rate": float(skill.success_rate)})

    def get(self, name: str) -> Skill | None:
        with self._lock:
            return self._skills.get(name)

    def names(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._skills))

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {token for token in value.lower().replace("/", " ").split() if token}

    def match(self, task: str) -> Skill | None:
        task_tokens = self._tokens(task)
        with self._lock:
            candidates: list[tuple[float, float, str, Skill]] = []
            for name, skill in self._skills.items():
                keyword_tokens = self._tokens(" ".join(skill.keywords))
                description_tokens = self._tokens(skill.description)
                overlap = len(task_tokens & keyword_tokens)
                description_overlap = len(task_tokens & description_tokens)
                if overlap == 0 and description_overlap == 0:
                    continue
                score = overlap * 2.0 + description_overlap * 0.25
                candidates.append((score, float(skill.success_rate), name, skill))
            if not candidates:
                vector_matches = self.vectors.nearest(self.vectors.embed(task), k=1, namespace="skills")
                if vector_matches and vector_matches[0].score >= 0.50:
                    return self._skills.get(vector_matches[0].metadata.get("name", vector_matches[0].item_id))
                return None
            candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
            best = candidates[0]
            if best[0] >= 2.0:
                return best[3]
            vector_matches = self.vectors.nearest(self.vectors.embed(task), k=1, namespace="skills")
            if vector_matches and vector_matches[0].score >= 0.50:
                return self._skills.get(vector_matches[0].metadata.get("name", vector_matches[0].item_id))
            return None


def built_in_skill_registry() -> SkillRegistry:
    return SkillRegistry(
        [
            Skill(
                name="comparison",
                description="Compare products, services, tools, or options using multiple sources and explicit trade-offs.",
                keywords=("compare", "comparison", "versus", "vs", "options", "cheapest"),
                input_schema={"type": "object", "additionalProperties": True},
                default_mode="dive",
                plan_template=(
                    {"type": "search", "params": {"limit": 5}},
                    {"type": "extract", "params": {"max_sources": 5}},
                    {"type": "rank", "params": {}},
                    {"type": "synthesize", "params": {"output_format": "comparison"}},
                ),
            ),
            Skill(
                name="price_lookup",
                description="Find current prices, availability, or purchasing options and compare trustworthy evidence.",
                keywords=("price", "cost", "availability", "available", "sale", "buy"),
                input_schema={"type": "object", "additionalProperties": True},
                default_mode="focus",
                plan_template=(
                    {"type": "search", "params": {"limit": 5, "freshness": "day"}},
                    {"type": "extract", "params": {"max_sources": 3, "fields": ["price", "availability"]}},
                    {"type": "rank", "params": {}},
                    {"type": "synthesize", "params": {"output_format": "comparison"}},
                ),
            ),
            Skill(
                name="source_summary",
                description="Summarize a source or topic with concise, cited evidence and no unsupported claims.",
                keywords=("summarize", "summary", "brief", "explain", "overview"),
                input_schema={"type": "object", "additionalProperties": True},
                default_mode="focus",
                plan_template=(
                    {"type": "extract", "params": {"max_sources": 3}},
                    {"type": "search", "params": {"limit": 3}},
                    {"type": "rank", "params": {}},
                    {"type": "synthesize", "params": {"output_format": "text"}},
                ),
            ),
        ]
    )


_DEFAULT_REGISTRY = built_in_skill_registry()


def register_skill(skill: Skill) -> None:
    _DEFAULT_REGISTRY.register(skill)


def match_skill(task: str) -> Skill | None:
    return _DEFAULT_REGISTRY.match(task)
