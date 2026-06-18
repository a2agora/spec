# Layer 6 — Negotiation Protocol

| Field | Value |
|---|---|
| Layer | 6 |
| Status | `discussion` |
| Working Group | negotiation |

## Scope

Defines the message exchange for agents to negotiate price, quality, and execution terms before a task begins. This is the most novel layer — no open standard exists for machine-speed compute negotiation.

## Message Flow

```
BUYER → registry: RFQ (capability, budget, latency SLA, proof requirement)
registry → BUYER: list of matching providers

BUYER → PROVIDER: offer request
PROVIDER → BUYER: offer { price, latency_sla, proof_method, valid_until_ms }

BUYER → PROVIDER: accept (+ escrow_id)
PROVIDER → BUYER: ack (task begins)
```

## Example RFQ

```json
{
  "type": "rfq",
  "capability": "sentiment-analysis",
  "input_tokens_est": 500,
  "max_latency_ms": 800,
  "max_price_cu": 0.005,
  "proof_method": "result-hash",
  "escrow_id": "esc_a3f9c2...",
  "offer_valid_ms": 50
}
```

## Design Considerations

- Offers must have a validity window (milliseconds) to prevent stale-price exploitation.
- The protocol must handle concurrent RFQs — a buyer may query multiple providers simultaneously.
- Negotiation must be stateless from the provider's perspective until an accept is received.

## Open Questions

- `[OPEN]` Should multi-round negotiation (counter-offers) be supported, or is single-round sufficient?
- `[OPEN]` How are SLA violations handled post-execution — protocol-level or out of band?
- `[OPEN]` Can offers be broadcast (auction model) or only point-to-point?
- `[OPEN]` How does the protocol prevent low-ball RFQ spam that wastes provider resources?
