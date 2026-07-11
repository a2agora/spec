---
title: "Layer 6 — Negotiation"
nav_order: 8
---

# Layer 6 — Negotiation Protocol

| Field | Value |
|---|---|
| Layer | 6 |
| Status | `draft` |
| Working Group | negotiation |

## Scope

Defines the message exchange in which a buyer and a provider agree on
**price and terms** before a task is executed. Negotiation sits between
discovery ([Layer 5](05-discovery.md) tells the buyer *who* is capable) and
execution ([Layer 1](01-transport.md) `acmp/invoke` runs the task under the
agreed terms, [Layer 4](04-escrow-settlement.md) secures the payment).

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are interpreted
as in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

Negotiation in v0.1 is **single-round** and **point-to-point**: the buyer
requests an offer, the provider quotes, the buyer accepts or walks away.
Counter-offers and broadcast auctions are explicitly out of scope (see Open
Questions). Machine-speed markets (RFC-0001 **P2**) are served by concurrent
fan-out instead (§5).

---

## 1. Where Negotiation Sits

```
L4:       escrowLock (buyer locks funds — typically before negotiating)
L5/ARD:   discover candidates ──▶ [provider A, provider B, ...]
L6:       offerRequest ──▶ offer ──▶ accept ──▶ ack        (this layer)
L4:       escrowBind (buyer binds the lock to the chosen provider)
L1:       acmp/invoke (+ escrow_id) ──▶ result
```

The buyer typically locks escrow *before* negotiating (RFC-0001's sequence)
and **binds** it to the chosen provider after accepting (Layer 4 §4.2) —
which is also where the negotiated `challenge_window_ms` lands.

All Layer 6 messages are JSON-RPC 2.0 requests over a standard ACMP
connection (Layer 1).

---

## 2. Messages

### 2.1 `acmp/offerRequest` — buyer asks for a quote

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/offerRequest",
  "id": "req_90ab31",
  "params": {
    "capability": "sentiment-analysis",
    "input_tokens_est": 500,
    "max_price_cu": 0.005,
    "max_latency_ms": 800,
    "preferred_tier": "B",
    "proof_method": "result-hash",
    "challenge_window_ms": 86400000,
    "offer_valid_ms": 50
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `capability` | string | yes | The capability to quote (ARD tag, same vocabulary as Layer 1/2). |
| `input_tokens_est` | integer | no | Buyer's size estimate. Informational. |
| `max_price_cu` | number | no | Budget ceiling. Provider SHOULD reject with -33001 rather than quote above it. |
| `max_latency_ms` | integer | no | Requested latency SLA (e.g. p99). |
| `preferred_tier` | string | no | Preferred CU quality tier (`S`, `A`, `B`) — same informational field as Layer 1/2. |
| `proof_method` | string | no | Required Layer 3 proof type. Provider MUST reject with -33006 if unsupported. |
| `challenge_window_ms` | integer | no | Proposed claim challenge window (Layer 4 §4.5). The value the buyer will set at `escrowBind`. |
| `offer_valid_ms` | integer | no | Requested offer validity window. Provider MAY clamp. |

Note ACMP prices **tasks, not tokens** (RFC-0001 §5): the quote covers the
outcome; the provider's own tokenomics are its margin calculation.

**Result — the Offer:**

```json
{
  "offer_id": "offer_6217d1",
  "capability": "sentiment-analysis",
  "price_cu": 0.003,
  "valid_until_ms": 1783017900050,
  "latency_sla_ms": 600,
  "proof_method": "result-hash",
  "challenge_window_ms": 86400000,
  "sig": {
    "did": "did:web:compute.example.com",
    "verification_method": "did:web:compute.example.com#key-1",
    "alg": "EdDSA",
    "created_ms": 1783017900000,
    "payload_hash": "sha256:4c2ab0...",
    "signature": "zQm8xT..."
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `offer_id` | string | yes | Provider-generated, single-use. |
| `capability` | string | yes | Echo of the requested capability. |
| `price_cu` | number | yes | The fixed task price. MUST be ≤ `max_price_cu` if one was given. |
| `valid_until_ms` | number | yes | Absolute epoch-ms expiry. Short windows (tens of ms) prevent stale-price exploitation. |
| `latency_sla_ms` | integer | no | The latency the provider commits to. |
| `proof_method` | string | no | The proof type the provider will deliver. |
| `challenge_window_ms` | integer | no | Confirmed (or adjusted) challenge window. Absence means the provider defers to the escrow agent's default. |
| `sig` | object | no | [Layer 7 §4](07-agent-wallet.md) signature envelope over the offer. **SHOULD** be present — a signed offer binds the provider to its price (non-repudiation). |

### 2.2 `acmp/accept` — buyer takes the offer

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/accept",
  "id": "req_90ab32",
  "params": {
    "offer_id": "offer_6217d1",
    "escrow_id": "esc_a3f9c2"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `offer_id` | string | yes | The offer being accepted. MUST still be within `valid_until_ms` (-34002 otherwise) and not previously accepted (-34003). |
| `escrow_id` | string | no | The Layer 4 escrow securing payment. RECOMMENDED; its absence signals direct settlement (Layer 1, "Relationship to Negotiation"). The buyer SHOULD have bound the escrow to this provider (Layer 4 §4.2) before or promptly after accepting. |

**Result — the Ack:**

```json
{
  "offer_id": "offer_6217d1",
  "escrow_id": "esc_a3f9c2",
  "price_cu": 0.003
}
```

Acceptance is the moment terms become binding. The buyer's subsequent
`acmp/invoke` carrying the same `escrow_id` executes under these terms; the
provider matches invoke to accepted offer via that shared `escrow_id`. How to
link them in escrow-less direct mode is `[OPEN]`.

---

## 3. Statelessness & Offer Validity

Quoting MUST be **stateless** for the provider: an offer is a signed promise,
not a reservation. No resources are held, nothing is booked — state is
created only at *accept*. Combined with short validity windows, this is the
primary defense against quote-spam: flooding a provider with offer requests
costs it only quote computation, never capacity.

Providers MAY additionally rate-limit offer requests per caller identity
(Layer 1 connection auth, or a Layer 7 DID where available). Deposit-based
anti-spam economics remain `[OPEN]`.

An expired offer MUST be rejected at accept with -34002; the buyer's remedy
is simply to request a fresh quote.

---

## 4. Terms Handoff

What is agreed here is consumed elsewhere. This table is normative glue:

| Negotiated term | Where it lands after accept |
|---|---|
| `price_cu` | Layer 1 `invoke.max_price_cu` (ceiling) and Layer 4 release/claim amounts; the provider's `cost_cu` MUST NOT exceed it. |
| `latency_sla_ms` | Quality commitment. Distinct from Layer 1 `timeout_ms` (the buyer's hard abort deadline, typically set well above the SLA). |
| `proof_method` | Layer 1 `invoke.proof_method`; the result's proof feeds Layer 3 verification and Layer 4 claims. |
| `challenge_window_ms` | Layer 4 `escrowBind.challenge_window_ms` — the buyer carries the agreed value to the escrow agent. |

**SLA violations after execution** are deliberately *not* a Layer 6 concern:
a missed SLA on a delivered result is contested through the Layer 4 dispute
path (with the signed offer as evidence) and priced in over time by Layer 7
reputation. Negotiation ends at accept.

---

## 5. Concurrent Fan-Out (the quasi-auction)

A buyer MAY send `acmp/offerRequest` to any number of discovered providers
**concurrently**, compare the returned offers, accept the best one, and
simply let the others expire — no retraction message exists or is needed;
validity windows do that work. From the market's perspective this *is* a
sealed-bid auction, run buyer-side, with zero auction infrastructure. A
protocol-level broadcast/auctioneer mode is `[OPEN]`.

---

## 6. Error Codes

Layer 6 uses the `-34xxx` range. These codes formalize what reference
implementations already use de facto; the numbers below are wire-compatible
with the [reference SDK](https://github.com/a2agora/sdk-reference).

| Code | Name | Description |
|---|---|---|
| -34001 | `offer_not_found` | Unknown `offer_id`. |
| -34002 | `offer_expired` | Accept arrived after `valid_until_ms`. |
| -34003 | `already_accepted` | Offers are single-use. |

Budget and capability failures during quoting reuse the Layer 1 codes
(-33001 `budget_exceeded`, -33002 `capability_not_found`, -33006
`proof_unsupported`).

---

## Design Decisions

| Question | Decision | Rationale |
|---|---|---|
| Single- or multi-round? | **Single-round** | Machine-speed (P2), stateless until accept, and proven by the reference SDK. Counter-offers stay `[OPEN]`. |
| Point-to-point or auction? | **Point-to-point + concurrent fan-out** | Fan-out over discovered candidates is a buyer-side sealed-bid auction with no new roles or infrastructure. |
| Quote-spam defense? | **Statelessness + short validity, DID rate-limiting MAY** | An offer is a promise, not a reservation — spam costs the provider compute, never capacity. |
| Post-execution SLA violations? | **Delegated to Layer 4 dispute + Layer 7 reputation** | Negotiation ends at accept; the signed offer is the evidence a dispute needs. |
| Error codes | **-34xxx, numbers adopted from the SDK's de-facto use** | The implementation preceded the spec here; keeping the numbers avoids a needless breaking change. |
| Terms → downstream layers | **Explicit handoff table (§4)** | Closes the dangling references from Layer 4 (`challenge_window_ms`) and Layer 7 (offer `sig`). |

---

## Open Questions

- `[OPEN]` Counter-offers: is a bounded multi-round extension (e.g. one
  counter each) worth the state it introduces?
- `[OPEN]` Auction mode: a broadcast RFQ with an auctioneer role — who runs
  it, and how does it stay P4/P6-compatible?
- `[OPEN]` Deposit-based spam economics for offer requests.
- `[OPEN]` Linking an accepted offer to the subsequent invoke in
  escrow-less direct mode (an `offer_id` field on `acmp/invoke`?).

---

## Related

- [RFC-0001 §2](../RFC-0001-vision.md) — use cases this flow serves; §5 tasks-not-tokens pricing
- [Layer 1 — Transport & Invocation](01-transport.md) — negotiated vs direct mode; `max_price_cu`, `timeout_ms`
- [Layer 3 — Proof of Execution](03-proof-of-execution.md) — `proof_method` semantics
- [Layer 4 — Escrow & Settlement](04-escrow-settlement.md) — `escrow_id` at accept, `challenge_window_ms` at bind
- [Layer 7 — Wallet & Identity](07-agent-wallet.md) — the offer `sig` envelope

---

*This document is part of the A2Agora specification. Licensed under Apache 2.0.*
