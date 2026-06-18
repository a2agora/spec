# Layer 2 — Task Decomposition Format

| Field | Value |
|---|---|
| Layer | 2 |
| Status | `draft` |
| Working Group | task-format |

## Scope

A standard schema for describing compute tasks that can be decomposed into sub-tasks, routed independently, and reassembled into a composed result.

## Design Considerations

- Tasks must be describable as a directed acyclic graph (DAG) of sub-tasks with dependencies.
- Partial results must be streamable — a consumer should not need to wait for all sub-tasks to complete.
- The format must be model- and provider-agnostic.

## Open Questions

- `[OPEN]` What is the minimal viable task schema? (input, output type, capability tag, estimated tokens)
- `[OPEN]` How are task dependencies expressed — explicit graph or implicit ordering?
- `[OPEN]` How does cancellation propagate through a sub-task graph?
