# Planner

The planner is the first stage after intent input: it determines what kind of internet work a task requires — search-only, search plus browsing, multi-source comparison, structured extraction, ongoing monitoring, or some combination.

## Inputs

- The task description (natural language or structured `skill` + `inputs`)
- Optional `mode` hint (Flash/Focus/Dive/Monitor)
- Available Internet Skills matching the task pattern (see [concepts/internet-skills.md](../concepts/internet-skills.md))

## Outputs

A **plan**: an ordered set of serializable `PlanStep` objects to hand to the [Router](router.md), along with an estimated retrieval mode if none was specified. The local planner emits a bounded plan identifier, intent classification, optional matched skill name, and concrete step parameters without persisting task content.

## Responsibilities

- Classify task intent (lookup, comparison, monitoring, longitudinal tracking, etc.)
- Decide depth (how many sources, how much browsing vs. static search)
- Decide whether a matching Internet Skill template applies
- Produce a plan inspectable through the Python `Planner.plan()` contract and used internally by `/solve`; the public `/plan` and `/execute` endpoints remain deferred (see [api/reference/agents.md](../api/reference/agents.md))

## Current local implementation

The local MVP provides deterministic `Planner`, `Plan`, and `PlanStep` objects. Built-in matching currently covers comparison, current price/availability lookup, and source-summary tasks. An explicitly named unknown skill fails closed with a validation error; an unmatched task falls back to a conservative focus-style search, extraction, ranking, and synthesis plan. When a task includes an absolute URL and explicitly requests rendering or interaction, the planner changes the bounded URL step to `browser`; ordinary tasks continue to prefer static extraction.

## Learning loop

Over time, plans that produced high-quality, well-cited, low-cost results for a given task class can be stored and reused, improving planner accuracy and reducing cost for recurring task shapes. See [research/economic-model.md](../research/economic-model.md).
