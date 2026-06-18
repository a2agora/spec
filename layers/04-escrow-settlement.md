# Layer 4 — Escrow & Settlement

| Field | Value |
|---|---|
| Layer | 4 |
| Status | `discussion` |
| Working Group | escrow-settlement |

## Scope

Defines how CU tokens are locked before a task begins and released upon verified completion. Specifies the settlement signaling protocol — not the underlying value transfer mechanism, which is pluggable.

## Design Considerations

- CU tokens must be locked (escrowed) before a provider begins work, preventing non-payment.
- Settlement must be atomic: tokens release if and only if proof of execution is accepted.
- The protocol must support multiple backing mechanisms: fiat credit accounts, stablecoins, or other value representations.
- Settlement latency target: < 500ms for the happy path.

## Escrow Lifecycle

```
BUYER locks CU → provider executes → proof submitted → BUYER releases CU
                                                      ↘ or disputes → arbitration
```

## Open Questions

- `[OPEN]` Who holds the escrow — a central platform, a smart contract, or a mutually trusted third party?
- `[OPEN]` What is the dispute window, and how is it negotiated per task?
- `[OPEN]` How are partial completions handled (e.g. streaming tasks that fail mid-way)?
- `[OPEN]` CU tier exchange rates — who publishes them and how often do they update?

## Related

- [Layer 3 — Proof of Execution](03-proof-of-execution.md) (triggers settlement)
- [Layer 7 — Agent Wallet](07-agent-wallet.md) (holds CU balance)
