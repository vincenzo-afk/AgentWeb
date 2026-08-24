from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from .skills import Skill, SkillRegistry, built_in_skill_registry

_URL_RE = re.compile(r"https?://[^\s)\]>]+")


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
    def _generic_steps(task: str, mode: str) -> tuple[PlanStep, ...]:
        urls = list(dict.fromkeys(_URL_RE.findall(task)))
        max_sources = 5 if mode == "dive" else 3
        steps: list[PlanStep] = []
        if urls:
            steps.append(PlanStep("extract", {"urls": urls[:max_sources], "max_sources": max_sources}))
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
            steps = tuple(PlanStep(item["type"], dict(item.get("params", {}))) for item in raw_steps)
        else:
            steps = self._generic_steps(task, estimated_mode)
        return Plan(
            id="plan_" + uuid.uuid4().hex[:16],
            steps=steps,
            estimated_mode=estimated_mode,
            intent=intent,
            skill=selected.name if selected else None,
        )
