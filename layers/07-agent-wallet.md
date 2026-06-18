# Layer 7 — Agent Wallet & Identity

| Field | Value |
|---|---|
| Layer | 7 |
| Status | `discussion` |
| Working Group | agent-wallet |

## Scope

Defines the interface for an agent's CU token balance, cryptographic identity, and spend authorization. This layer sits closest to the agent framework and is the primary integration surface for framework authors.

## Responsibilities

- **Identity:** each agent has a verifiable keypair used to sign RFQs, offers, and settlement messages.
- **Balance:** the wallet holds CU tokens across tiers and exposes a standard balance query interface.
- **Authorization:** the wallet enforces spend limits set by the agent's operator (e.g. max 10 CU/hour).
- **Audit log:** all transactions are logged locally for operator visibility.

## Design Considerations

- The wallet interface must be embeddable in existing agent frameworks (LangChain, AutoGen, CrewAI) as a plugin or middleware — not a required architectural change.
- Spend limits are a safety primitive against alignment-leak: an agent must not be able to spend beyond its operator-defined budget regardless of its own reasoning.
- The wallet does not hold private keys to external value (fiat, stablecoin) — it holds CU credits, which are redeemable via the settlement layer.

## Open Questions

- `[OPEN]` Should agent identity be tied to a keypair the operator controls, or can agents self-generate identity?
- `[OPEN]` How are spend limits expressed — absolute CU cap, rate limit (CU/hour), or per-task maximum?
- `[OPEN]` How does a wallet recover from a crash mid-escrow?
- `[OPEN]` Multi-agent systems: can one wallet serve a fleet of sub-agents, or is identity 1:1 with agent instance?
