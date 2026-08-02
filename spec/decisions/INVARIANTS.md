# Invariants

Properties that must always hold, across every code path:

1. Every claim in a `Synthesis` output maps to at least one `Citation` with a valid `source_id`. No uncited claims are ever returned.
2. Every `Snapshot` is immutable once written; updates always create a new snapshot with a new hash, never mutate an existing one.
3. Every `Run` and `Monitor` produces or updates an `ExecutionTrace` — there is no code path that completes work without a trace record.
4. A `Monitor` check that fails to reach its target records a `check_failed` event, never a false "no change" diff.
5. No API key scope check is bypassed for internal/admin convenience — even internal tooling calls through the same authorization path as external clients.
6. No secret value (API key, webhook signing secret, stored credential) is ever written to logs or execution traces.

Violating any of these should be treated as a severity-1 bug regardless of how minor the triggering change seems.
