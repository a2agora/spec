# Layer 1 — Transport & Invocation

| Field | Value |
|---|---|
| Layer | 1 |
| Status | `draft` |
| Working Group | transport |

## Scope

Defines how agents discover each other's endpoints and invoke compute tasks. This layer is the foundation all other layers build on.

## Design Considerations

- MCP (Model Context Protocol) is the natural candidate for the base transport. An ACMP extension to MCP may be sufficient for Layer 1.
- Must support both request/response and streaming result patterns.
- Agent endpoints must be addressable without a centralized broker (though brokers are allowed).

## Open Questions

- `[OPEN]` Should Layer 1 be specified as an MCP extension, or as a standalone transport?
- `[OPEN]` How are agent endpoints authenticated at the transport level?

## Related

- [RFC-0001 §6](../RFC-0001-vision.md)
- [Layer 5 — Discovery (ARD Binding)](05-discovery.md)
