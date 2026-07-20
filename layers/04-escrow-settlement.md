---
title: "Layer 4 — Escrow & Settlement"
nav_order: 6
---

# Layer 4 — Escrow & Settlement

| Field | Value |
|---|---|
| Layer | 4 |
| Status | `draft` |
| Working Group | escrow-settlement |

## Scope

Defines how CU value is locked before a task begins and released upon verified
completion. This layer specifies the **escrow signaling protocol** — the
roles, states, and messages. The underlying movement of value is delegated to
pluggable **settlement rails** (§7); no specific rail is mandated.

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are interpreted
as in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 1. Roles & Trust Model

Escrow involves three parties:

| Role | Responsibility |
|---|---|
| **Buyer** | Locks CU before work starts; releases against accepted proof; reclaims unused funds. |
| **Provider** | Performs the work; may claim payment with proof if the buyer goes silent. |
| **Escrow Agent** | Neutral third party that holds locked CU and enforces the state machine below. |

The Escrow Agent is a **role, not an implementation**. It MAY be operated as a
hosted platform service, a mutually trusted third party, or a smart contract —
all are conforming as long as they implement the message interface in §4. Per
RFC-0001 principle **P4**, at least one non-blockchain implementation path
MUST always exist (see §7.2).

Buyer and provider each talk to the Escrow Agent over a standard ACMP
connection ([Layer 1](01-transport.md)): all messages below are JSON-RPC 2.0
requests in the `acmp/` namespace.

**Party authorization:** the agent binds the *buyer* role to the authenticated
connection identity (Layer 1 §5) that created the lock, and the *payee* role
to the authenticated identity matching the bound `payee_id`. Buyer-side
operations (bind, release, reclaim, dispute) MUST be rejected with -35005
unless they arrive from the buyer's identity; `escrowClaim` MUST be rejected
unless it arrives from the bound payee's identity. Note that `payee_id` itself
is self-reported at this layer — verifiable identity binding is [Layer
7](07-agent-wallet.md)'s job (e.g. W3C DIDs).

An Escrow Agent advertises the capability in its MCP `initialize` handshake:

```json
{
  "capabilities": {
    "acmp": {
      "version": "0.1.0",
      "role": "escrow-agent",
      "accepts": [
        "acmp/escrowLock", "acmp/escrowBind", "acmp/escrowRelease",
        "acmp/escrowReclaim", "acmp/escrowClaim", "acmp/escrowDispute",
        "acmp/escrowStatus"
      ]
    }
  }
}
```

---

## 2. Escrow Lifecycle

An escrow tracks a **balance** (locked CU) through four states:

```
                     ┌────────┐
         lock        │        │  release / reclaim (buyer)
BUYER ──────────────▶│  open  │────────────────────────────────▶ closed
                     │        │                                    ▲
                     └───┬────┘                                    │
                         │ claim (provider, with proof)            │
                         ▼                                         │
                     ┌─────────┐  challenge window elapses         │
                     │ claimed │───────(auto-release)──────────────┤
                     └───┬─────┘                                   │
                         │ dispute (buyer, within window)          │
                         ▼                                         │
                     ┌──────────┐  resolution (agent policy)       │
                     │ disputed │──────────────────────────────────┘
                     └──────────┘
```

| State | Meaning |
|---|---|
| `open` | Funds are locked. Partial releases and partial reclaims are possible; the escrow stays `open` while remaining balance > 0. |
| `claimed` | The provider has claimed payment with proof; a challenge window is running. Auto-release at window end unless disputed. |
| `disputed` | The buyer contested a claim. Frozen until the agent's resolution process concludes. |
| `closed` | Terminal. Balance fully disbursed (released + reclaimed = locked). |

**Happy path** (matches the RFC-0001 sequence diagram): buyer locks 0.005 CU →
task runs → buyer verifies proof and releases 0.003 CU to the provider → buyer
reclaims the unused 0.002 CU → escrow closes.

**Safety path** (silent buyer): the provider submits `acmp/escrowClaim` with
its proof. If the buyer does not dispute within the challenge window, the
agent auto-releases the claimed amount. This is the settlement-side twin of
[Layer 3](03-proof-of-execution.md)'s *Optimistic Execution + Challenge
Period* model.

**Expiry:** every lock carries a `valid_until_ms` deadline. If the escrow is
still `open` at expiry, the agent MUST auto-reclaim the remaining balance to
the buyer and close the escrow. A pending claim or dispute **suspends** expiry
until resolved — a provider who claimed in time cannot lose payment to the
clock. Buyers SHOULD size `valid_until_ms` to cover task timeout plus the
challenge window.

---

## 3. Idempotency

Every mutating message carries a caller-generated **`op_ref`** (unique string,
e.g. `op_<random>`). An agent that receives a repeated `op_ref` on the same
escrow MUST NOT execute the operation twice; it MUST return the outcome of the
first execution. This makes every operation safe to retry after a network
failure — the same rule Layer 1 §3.1.1 applies to `task_id`.

---

## 4. Message Schemas

### 4.1 `acmp/escrowLock` — buyer locks funds

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/escrowLock",
  "id": "req_5c11aa",
  "params": {
    "op_ref": "op_9f21b3c4",
    "amount_cu": 0.005,
    "tier": "B",
    "valid_until_ms": 1783017900000,
    "payee_id": null,
    "challenge_window_ms": 86400000
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `op_ref` | string | yes | Idempotency key (§3). |
| `amount_cu` | number | yes | CU amount to lock. Rejected with -35002 if the buyer's funding does not cover it. |
| `tier` | string | no | CU quality tier (`S`, `A`, `B`). |
| `valid_until_ms` | number | yes | Absolute epoch-ms expiry of the lock (§2 Expiry). |
| `payee_id` | string | no | The provider allowed to claim/receive. MAY be omitted at lock time (RFC-0001 locks *before* provider selection) and bound later via `acmp/escrowBind`. |
| `challenge_window_ms` | integer | no | Challenge window applied to claims (§4.5). Note the lock typically happens *before* Layer 6 negotiation (RFC-0001 ordering), so the buyer can only set a standing default here; the negotiated value is set at bind time (§4.2). Default: agent policy (RECOMMENDED 24 h). |

**Result:** `{ "escrow_id": "esc_a3f9c2", "state": "open", "amount_cu": 0.005,
"valid_until_ms": 1783017900000 }`

The returned `escrow_id` is what the buyer passes to the provider in the Layer
6 *accept* and in Layer 1 `acmp/invoke`.

How the lock is **funded** is rail-specific (§7) — e.g. an existing credit
balance with the agent, or an inbound rail payment.

### 4.2 `acmp/escrowBind` — buyer binds the payee

Binds an unbound escrow to one provider. Binding is **once-only**: rebinding
MUST be rejected with -35003. Typically sent between Layer 6 *accept* and
Layer 1 *invoke*.

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/escrowBind",
  "id": "req_5c11ab",
  "params": {
    "op_ref": "op_71d0e2aa",
    "escrow_id": "esc_a3f9c2",
    "payee_id": "agent:openclaw-3:us-east",
    "challenge_window_ms": 86400000
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `op_ref` | string | yes | Idempotency key. |
| `escrow_id` | string | yes | The escrow to bind. |
| `payee_id` | string | yes | Layer 1 §4 identity format. |
| `challenge_window_ms` | integer | no | The challenge window agreed in the Layer 6 terms. Since bind follows *accept*, this is where the negotiated value lands; it overrides any default set at lock time. |

**Result:** `{ "escrow_id": "esc_a3f9c2", "payee_id":
"agent:openclaw-3:us-east" }`

### 4.3 `acmp/escrowRelease` — buyer releases funds to the provider

The fast path: the buyer verified the proof itself and pays out immediately.

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/escrowRelease",
  "id": "req_5c11ac",
  "params": {
    "op_ref": "op_c44d19e0",
    "escrow_id": "esc_a3f9c2",
    "amount_cu": 0.003,
    "payee_id": "agent:openclaw-3:us-east",
    "task_id": "task_a7c923f1",
    "proof": { "method": "result-hash", "hash": "sha256:e3b0c442..." }
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `op_ref` | string | yes | Idempotency key. |
| `escrow_id` | string | yes | The escrow to release from. |
| `amount_cu` | number | yes | Amount to release. MUST be ≤ remaining balance (-35006 otherwise). Partial releases are allowed; the escrow stays `open` while balance remains. |
| `payee_id` | string | yes | MUST equal the bound payee. If the escrow is unbound, this release binds it implicitly. |
| `task_id` | string | no | The Layer 1 task this payment settles. Audit trail. |
| `proof` | object | no | The accepted Layer 3 proof. Audit trail; the agent stores it but does not verify it on this path (the buyer already did). |

**Result:** `{ "escrow_id": "esc_a3f9c2", "released_cu": 0.003,
"remaining_cu": 0.002, "state": "open" }`

A release in state `claimed` is allowed as a fast-forward confirmation of the
pending claim — but only for `amount_cu` **≥ the claimed amount** (it resolves
the claim; any surplus release is a normal partial release). A smaller release
MUST be rejected with -35003: a buyer who believes less is owed must
**dispute**, not undercut the claim.

### 4.4 `acmp/escrowReclaim` — buyer takes back unused funds

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/escrowReclaim",
  "id": "req_5c11ad",
  "params": {
    "op_ref": "op_2b8ce671",
    "escrow_id": "esc_a3f9c2",
    "amount_cu": 0.002
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `op_ref` | string | yes | Idempotency key. |
| `escrow_id` | string | yes | The escrow to reclaim from. |
| `amount_cu` | number | no | Amount to reclaim. Default: entire remaining balance. |

**Result:** `{ "escrow_id": "esc_a3f9c2", "reclaimed_cu": 0.002,
"remaining_cu": 0, "state": "closed" }`

Reclaim is only valid in state `open` (-35003 otherwise) — a pending claim
blocks it, so a provider's in-flight claim cannot be undercut.

**Bound-escrow guard:** on a *bound* escrow, reclaim MUST additionally be
rejected (-35003) until at least one release or resolved claim has occurred.
Binding signals that a deal is on; without this guard, a buyer could drain the
escrow *while the provider is still working*, winning the race against the
provider's claim and defeating the safety path entirely. The buyer's funds are
never stranded: they come back via the happy path (release, then reclaim the
remainder — the RFC-0001 flow) or via expiry auto-reclaim if the provider
never delivers. Unbound escrows can be reclaimed freely at any time.

### 4.5 `acmp/escrowClaim` — provider claims payment with proof

The safety path for a silent or unresponsive buyer. Valid only in state `open`
(-35003 otherwise); one claim may be pending at a time.

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/escrowClaim",
  "id": "req_5c11ae",
  "params": {
    "op_ref": "op_e09a3d17",
    "escrow_id": "esc_a3f9c2",
    "amount_cu": 0.003,
    "task_id": "task_a7c923f1",
    "proof": { "method": "result-hash", "hash": "sha256:e3b0c442..." }
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `op_ref` | string | yes | Idempotency key. |
| `escrow_id` | string | yes | MUST be bound, and the caller MUST be the bound payee (-35005 otherwise). |
| `amount_cu` | number | yes | Claimed amount, ≤ remaining balance. |
| `task_id` | string | yes | The task the claim settles. |
| `proof` | object | yes | The Layer 3 proof. In v0.1 the agent stores it as dispute evidence rather than verifying it cryptographically — verification maturity tracks Layer 3. |

**Result:** `{ "escrow_id": "esc_a3f9c2", "state": "claimed", "claim": {
"amount_cu": 0.003, "window_ends_ms": 1783104300000 } }`

State moves to `claimed` and the challenge window starts. If the buyer does
not dispute before `window_ends_ms`, the agent MUST auto-release the claimed
amount to the payee (any remainder returns to `open`, still reclaimable).

### 4.6 `acmp/escrowDispute` — buyer contests a claim

Valid only in state `claimed`, before the window ends.

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/escrowDispute",
  "id": "req_5c11af",
  "params": {
    "op_ref": "op_55fe0c28",
    "escrow_id": "esc_a3f9c2",
    "reason": "Returned result does not match the task input.",
    "evidence": { "task_id": "task_a7c923f1", "offer_id": "offer_6217d1" }
  }
}
```

**Result:** `{ "escrow_id": "esc_a3f9c2", "state": "disputed" }`

The escrow freezes. **Resolution is agent policy, not protocol**: the agent
arbitrates (itself, via a third party, or via a Layer 3 re-execution audit)
and disburses accordingly, closing the escrow. Parties observe the outcome via
`acmp/escrowStatus`. Standardizing arbitration is out of scope for v0.1.

### 4.7 `acmp/escrowStatus` — query

Callable by the buyer or the bound payee (-35005 for anyone else).

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/escrowStatus",
  "id": "req_5c11b0",
  "params": { "escrow_id": "esc_a3f9c2" }
}
```

**Result:**

```json
{
  "escrow_id": "esc_a3f9c2",
  "state": "open",
  "locked_cu": 0.005,
  "released_cu": 0.003,
  "reclaimed_cu": 0,
  "remaining_cu": 0.002,
  "payee_id": "agent:openclaw-3:us-east",
  "valid_until_ms": 1783017900000,
  "claim": null,
  "dispute": null
}
```

---

## 5. Error Codes

Layer 4 uses the `-35xxx` range — distinct from Layer 1's `-33xxx`; `-34xxx`
is informally in use for negotiation-level errors.

| Code | Name | Description |
|---|---|---|
| -35001 | `escrow_not_found` | Unknown `escrow_id`. |
| -35002 | `insufficient_funds` | Lock could not be funded. |
| -35003 | `invalid_state` | Operation not permitted in the current state (incl. rebinding). |
| -35004 | `escrow_expired` | The lock passed `valid_until_ms` and was auto-reclaimed. |
| -35005 | `not_authorized` | Caller is not a party to this escrow, or not the party allowed to perform this operation. |
| -35006 | `amount_exceeds_remaining` | Release/reclaim/claim amount exceeds the remaining balance. |
| -35099 | `internal` | Unspecified agent-side error. |

---

## 6. Atomicity

The core guarantee of this layer:

> Locked CU leaves the escrow **only** through (a) an explicit buyer release,
> (b) an unchallenged claim's auto-release, (c) a dispute resolution, or
> (d) expiry auto-reclaim to the buyer. A conforming agent MUST NOT move
> value on any other trigger, and MUST perform the rail payout (§7) strictly
> **after** the corresponding state transition is durably recorded.

Settlement latency target for the happy path (release → payout initiated): **<
500 ms**. On-chain rails may exceed this for *finality*; the state transition
itself must still meet the target.

---

## 7. Settlement Rails

### 7.1 Abstract rail interface (normative)

The escrow agent holds value **between** two rail interactions: funding in,
payout out. A conforming agent:

- MUST support at least one **funding mechanism** for locks (e.g. a credit
  balance held with the agent, or an inbound rail payment at lock time).
- MUST support at least one **payout mechanism** to disburse releases (to the
  payee) and reclaims (to the buyer).
- MUST perform payouts idempotently (one payout per state transition, keyed by
  `escrow_id` + transition), and only after that transition (§6).
- MUST NOT expose one party's rail credentials or funding details to the other
  party.
- MAY support multiple rails simultaneously; the payout rail is selected by
  the recipient's wallet configuration ([Layer 7](07-agent-wallet.md)).

### 7.2 Non-blockchain path (P4)

A plain **credit ledger** at the agent is a fully conforming rail: funding
debits the buyer's account balance, payout credits the payee's. No chain, no
token. This path MUST always remain implementable (RFC-0001 P4).

A more powerful chain-free rail exists in **Chaumian blind-signature e-cash**
(e.g. [GNU Taler](https://taler.net)): true bearer tokens with payer privacy
and payee-side income transparency (AML/CFT-friendly), measured costs below
USD 0.0001 per transaction, and settlement in a few hundred milliseconds —
comfortably inside this layer's latency target (§6), and priced for exactly
the micro-amounts CU trades involve. See Chaum, Grothoff & Moser, [*How to
Issue a Central Bank Digital Currency*](https://ssrn.com/abstract=3965032)
(SNB Working Paper, 2021) for the reference design. Like all rails here: a
candidate binding, not a requirement.

### 7.3 x402 binding (informative)

[x402](https://x402.org) is an HTTP-402 stablecoin rail with immediate,
single-round-trip settlement. That instant-settlement nature is **not** in
tension with escrow-on-proof once the rail is placed at the *edges* of the
escrow rather than in the middle:

- **Funding edge:** the buyer funds a lock by paying the escrow agent over
  x402 (agent responds `402 Payment Required` for the lock amount; buyer pays;
  lock opens). Instant settlement *into* escrow is unproblematic — the funds
  are now held by the neutral agent.
- **Payout edge:** after a release (or resolved claim), the agent pays the
  provider over x402 to the wallet advertised in its Layer 7 configuration.
  Instant settlement *out of* escrow is exactly what the < 500 ms target
  wants.

In short: **settle in → hold → settle out.** The escrow guarantee lives at the
agent, between two instant rail hops. No hold/capture extension to x402 is
required. This resolves the previously `[OPEN]` question on reconciling
instant-settlement rails with escrow-on-proof.

---

## Design Decisions

| Question | Decision | Rationale |
|---|---|---|
| Who holds the escrow? | **Neutral Escrow Agent role** (interface, not implementation) | Platform, trusted third party, or smart contract all conform; P4 keeps a non-chain path mandatory. |
| Who initiates the lock? | **Buyer** | Matches RFC-0001's sequence and Layer 6's `accept (+ escrow_id)`. |
| Payee binding | **Optional at lock, once-only bind afterwards** | RFC-0001 locks before provider selection; binding at accept-time closes the gap without a second lock. |
| Silent-buyer problem | **Provider claim + challenge window + auto-release** | The settlement twin of Layer 3's Optimistic Execution model; without it, providers bear unbounded non-payment risk. |
| Expiry | **Auto-reclaim at `valid_until_ms`; pending claim/dispute suspends expiry** | No stranded funds, and the clock can never expropriate a timely claim. |
| Early-reclaim race | **Bound escrows cannot be reclaimed before a first release/claim resolution** | Otherwise a buyer could drain the escrow mid-task and beat the provider's claim to the punch — the guard makes the safety path race-free. |
| Instant rails vs escrow-on-proof | **Rails at the edges (fund-in / payout-out), escrow held at the agent** | Dissolves the tension without requiring hold/capture semantics from any rail. |
| Error range | **-35xxx** | -33xxx is Layer 1; -34xxx is de-facto negotiation. |

---

## Open Questions

- `[OPEN]` Partial completions of streaming tasks (Layer 1 §7 / Layer 2 §5):
  can a partial result justify a partial claim, and how is "how much was
  delivered" measured? Deferred until Layer 3 matures.
- `[OPEN]` **Abandoned interrupts.** If Layer 1 gains resumable interrupts
  ([L1 Open Questions](01-transport.md#open-questions), [L2 Open
  Questions](02-task-format.md#open-questions)), a provider may pause a task
  awaiting buyer input while the buyer never returns. The escrow mechanics
  already exist — partial release (§4.3) and expiry auto-reclaim (§2) — so the
  open part is the *trigger semantics*, not the plumbing: does an interrupt
  carry its own `expires_in` window, does the task reach a terminal
  `abandoned` state distinct from plain expiry, and is the provider partially
  settled for compute spent up to the interrupt point (rather than the buyer
  reclaiming everything)? Coupled to how "work done so far" is measured, which
  tracks Layer 3.
- `[OPEN]` Dispute arbitration: v0.1 leaves resolution to agent policy. Should
  a future version standardize an arbitration interface (e.g. a Layer 3
  re-execution audit as neutral arbiter)?
- `[OPEN]` Should the agent push state-change notifications
  (`acmp/escrowResolved`?) instead of requiring `escrowStatus` polling?
- `[OPEN]` CU tier exchange rates — who publishes them and how often do they
  update? (Tracked at RFC-0001 §5.)

---

## Related

- [RFC-0001 — At a Glance](../RFC-0001-vision.md) (the lock → release →
  reclaim sequence this layer implements)
- [Layer 1 — Transport & Invocation](01-transport.md) (transport for all
  escrow messages; `escrow_id` in `acmp/invoke`; `escrow_invalid` -33005)
- [Layer 3 — Proof of Execution](03-proof-of-execution.md) (proof acceptance
  triggers release; the claim path mirrors its optimistic model)
- [Layer 6 — Negotiation Protocol](06-negotiation-protocol.md) (terms incl.
  challenge window; `accept (+ escrow_id)`)
- [Layer 7 — Agent Wallet](07-agent-wallet.md) (CU balance, payout rail
  configuration, verifiable identity)

---

*This document is part of the A2Agora specification. Licensed under Apache
2.0.*
