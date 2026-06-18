# Layer 5 — Capability Registry

| Field | Value |
|---|---|
| Layer | 5 |
| Status | `discussion` |
| Working Group | capability-registry |

## Scope

Defines how agents advertise their capabilities and how buyers discover qualified providers. Analogous to DNS for services, but with pricing, SLA, and capability metadata.

## A Capability Advertisement

An agent registers an entry like:

```json
{
  "agent_id": "openclaw-3.example.com",
  "capabilities": ["sentiment-analysis", "code-execution", "vision"],
  "tier": "A",
  "price_cu_per_1k_tokens": 0.004,
  "latency_p99_ms": 800,
  "availability": 0.997,
  "proof_methods": ["result-hash", "tee-attestation"],
  "updated_at": "2026-06-18T14:00:00Z"
}
```

## Design Considerations

- Discovery must work without a single centralized registry (federated or P2P approaches preferred).
- Entries must be verifiable — a provider cannot falsely claim capabilities or SLAs without consequence.
- The registry must support semantic search (e.g. "find agents capable of vision tasks under 0.005 CU").

## Open Questions

- `[OPEN]` Federated registry (like ActivityPub) vs. gossip protocol vs. centralized with open API?
- `[OPEN]` How are capability claims verified before an agent is listed?
- `[OPEN]` How are stale or offline entries expired?
- `[OPEN]` Should capability taxonomy be standardized, or free-form tags?
