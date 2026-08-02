# State Machine

## Run states (`solve`)

```
queued → planning → executing → ranking → synthesizing → complete
                                                        └─▶ failed
```

## Monitor states (`observe`)

```
active ⇄ paused
active → cancelled
active → (per check) checking → active
```

| State | Meaning |
|---|---|
| `queued` | Accepted, not yet planned |
| `planning` | Planner is producing a plan |
| `executing` | Execution workers are gathering evidence |
| `ranking` | Trust/ranking scoring in progress |
| `synthesizing` | Final answer generation |
| `complete` | Result available |
| `failed` | Unrecoverable error; see [../resilience/FAILURE_RECOVERY.md](../resilience/FAILURE_RECOVERY.md) |
| `active` (monitor) | Scheduled checks running normally |
| `paused` (monitor) | Checks suspended, resumable |
| `cancelled` (monitor) | Terminated, not resumable |

See [../api/RESPONSE_SCHEMA.md](../api/RESPONSE_SCHEMA.md) for how state surfaces in API responses.
