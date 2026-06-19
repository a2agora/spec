# A2Agora — Agent Compute Market Protocol (ACMP)

**The open marketplace protocol for agent-to-agent compute trading.**

---

## The Problem

AI agents need compute. Today, every agent is locked into a single provider's pricing, availability, and API. There is no open way for agents to:

- discover who can fulfill a compute task
- negotiate price and quality autonomously
- pay atomically upon verified completion
- trade unused compute capacity

Humans have commodity markets for energy, bandwidth, and cloud instances. Agents don't — yet.

## The Vision

A2Agora defines a layered open protocol (ACMP) that enables any AI agent to buy, sell, and exchange compute as a first-class market participant — without human involvement in individual transactions.

A Hermes agent short on budget at 3am finds an idle OpenClaw instance, negotiates a price in milliseconds, gets the job done, and pays — all autonomously. No vendor lock-in. No manual API key juggling. No centralized marketplace taking 30%.

## Protocol Layers

| # | Layer | Status |
|---|---|---|
| 1 | Transport & Invocation | `draft` |
| 2 | Task Decomposition Format | `draft` |
| 3 | Proof of Execution | `discussion` |
| 4 | Escrow & Settlement | `discussion` |
| 5 | Discovery ([→ ARD](https://agenticresourcediscovery.org)) | `external` |
| 6 | Negotiation Protocol | `discussion` |
| 7 | Agent Wallet & Identity | `discussion` |

Each layer is independently specifiable and implementable. You don't need to implement all seven to participate — a registry-only implementation is as valid a contribution as a full stack.

## Status

This is a **pre-v0 specification**. Everything is open for discussion. The goal right now is not to get it right — it's to get it written down so we can argue about it properly.

Read [RFC-0001](RFC-0001-vision.md) for the full problem statement and design rationale.

## Contributing

This project is organized around **Working Groups** — one per layer. Each working group owns its layer's spec document and maintains a set of open issues for that layer.

See [CONTRIBUTING.md](CONTRIBUTING.md) to find a working group, pick up a good first issue, or propose a new layer.

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

*Initiated by the A2Agora contributors with the assistance of [Claude Code](https://claude.ai/code).*
