# Deployment Guide

## Pre-deployment checklist
- All [Phase 0 modules](../build-plan/PHASES.md) pass [acceptance criteria](../testing/ACCEPTANCE_CRITERIA.md)
- Required [environment variables](../config/ENVIRONMENT_VARIABLES.md) configured, secrets sourced from a secrets manager
- [Quality gates](../testing/QUALITY_GATES.md) pass in CI
- [Deployment architecture](../architecture/DEPLOYMENT_ARCHITECTURE.md) provisioned (API tier, orchestration tier, execution workers, stores, job scheduler)

## Deployment sequence
1. Deploy/migrate data stores first ([../data/STORAGE_SPEC.md](../data/STORAGE_SPEC.md)) — schema changes should be backward-compatible with the currently running version.
2. Deploy orchestration + execution tiers.
3. Deploy API tier last, behind a health check gate.
4. Run a smoke-test subset of [E2E tests](../testing/E2E_TESTS.md) against the newly deployed environment before routing production traffic.

## Rollback
Any deploy that fails smoke tests rolls back the API tier first (stops new traffic from hitting the bad version), then orchestration/execution tiers, then reverts data store migrations only if they're not backward-compatible with the prior version.

See [../../docs/operations/disaster-recovery.md](../../docs/operations/disaster-recovery.md) for recovery beyond a failed deploy.
