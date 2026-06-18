# Contributing to A2Agora

Welcome. A2Agora is a community-driven protocol spec. There is no company behind it — only contributors.

## How the project is organized

The spec is divided into **7 layers**. Each layer has its own document in `layers/` and its own working group. You can contribute to one layer without understanding the full stack.

| Layer | Document | Working Group Label |
|---|---|---|
| 1 — Transport | [layers/01-transport.md](layers/01-transport.md) | `wg-transport` |
| 2 — Task Format | [layers/02-task-format.md](layers/02-task-format.md) | `wg-task-format` |
| 3 — Proof of Execution | [layers/03-proof-of-execution.md](layers/03-proof-of-execution.md) | `wg-proof-of-execution` |
| 4 — Escrow & Settlement | [layers/04-escrow-settlement.md](layers/04-escrow-settlement.md) | `wg-escrow` |
| 5 — Capability Registry | [layers/05-capability-registry.md](layers/05-capability-registry.md) | `wg-registry` |
| 6 — Negotiation Protocol | [layers/06-negotiation-protocol.md](layers/06-negotiation-protocol.md) | `wg-negotiation` |
| 7 — Agent Wallet | [layers/07-agent-wallet.md](layers/07-agent-wallet.md) | `wg-wallet` |

## Good first contributions

- **Challenge an open question.** Every layer document lists `[OPEN]` questions. Open an issue with your analysis, even if you don't have a definitive answer.
- **Write a comparison.** How does an existing system (Akash, Vast.ai, MCP, Stripe) address a problem in one of the layers? A well-researched comparison issue is extremely valuable.
- **Draft a schema.** Pick a `[OPEN]` question about a message format or data structure, propose a concrete schema, and open a PR to the relevant layer document.
- **Review RFC-0001.** The vision document is intentionally incomplete. If something is wrong, missing, or unclear — open an issue with label `rfc-0001`.

## What we're especially looking for

- **Protocol engineers** — for Layers 1, 2, 6
- **Security researchers** — for Layer 3 (Proof of Execution)
- **Fintech / payments engineers** — for Layer 4 (Escrow)
- **Distributed systems engineers** — for Layer 5 (Registry)
- **AI framework authors** — for Layer 7 (Wallet integration)
- **Economists / mechanism designers** — for Layer 6 (Negotiation) and CU tier definitions
- **Regulatory / legal experts** — for the open question on CU token classification

## Making changes to the spec

1. Open an issue first for any non-trivial change.
2. Fork the repo and create a branch: `layer-N/short-description`.
3. Edit the relevant layer document or RFC.
4. Mark unresolved points as `[OPEN]` with a brief explanation.
5. Open a PR referencing the issue.

Spec PRs don't need to be complete — a well-reasoned partial answer to an `[OPEN]` question is mergeable.

## Conventions

- All spec documents are in English.
- Use present tense for normative statements ("The provider MUST...").
- Use RFC 2119 keywords (MUST, SHOULD, MAY) for requirements once a layer moves from `discussion` to `draft`.
- Keep `[OPEN]` markers for anything unresolved — don't paper over uncertainty.

## License

By contributing, you agree that your contributions are licensed under Apache 2.0.
