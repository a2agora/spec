---
title: "Layer 7 — Wallet & Identity"
nav_order: 9
---

# Layer 7 — Agent Wallet & Identity

| Field | Value |
|---|---|
| Layer | 7 |
| Status | `draft` |
| Working Group | agent-wallet |

## Scope

Defines the two things an agent needs to act as an economic party: a
**verifiable identity** (who is this agent, cryptographically) and a
**wallet** (its CU balance, operator-set spend limits, payout configuration,
and audit trail). This layer sits closest to the agent framework and is the
primary integration surface for framework authors.

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**
are interpreted as in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 1. The Wallet

The wallet is **operator-controlled middleware**, embeddable in existing agent
frameworks (LangChain, AutoGen, CrewAI) as a plugin — not a required
architectural change (RFC-0001 **P5**). It owns three things the agent process
itself MUST NOT be able to override:

1. **Keys** — the private keys behind the agent's economic identity live in
   the wallet, never in the agent's context or prompt. The agent *requests*
   signatures; it cannot exfiltrate the key material.
2. **Spend limits** — enforced by the wallet *outside* the agent's reasoning
   loop (§6.2). This is the protocol's core safety primitive against the
   *alignment-leak* risk (RFC-0001): an agent must not be able to spend beyond
   its operator-defined budget regardless of its own reasoning, and it MUST
   have no interface to raise its own limits.
3. **The audit log** — append-only, operator-readable (§6.3).

The wallet holds **CU credits**; it does not hold private keys to external
value (fiat, stablecoin). Redemption of CU happens via the settlement layer
([Layer 4 §7](04-escrow-settlement.md)).

---

## 2. Agent Identity: W3C DIDs

An agent's economic identity is a [W3C Decentralized Identifier
(DID)](https://www.w3.org/TR/did-core/): the wallet controls the private key,
and the DID document publishes the public key(s) a counterparty needs for
verification.

### 2.1 Method policy (P4)

- An agent participating economically MUST publish at least one DID using a
  **chain-free method**: `did:web` (resolves over plain HTTPS — the natural
  choice for domain-anchored providers) or `did:key` (fully self-contained —
  the natural choice for buyers and ephemeral parties).
- Verifiers MUST be able to resolve **both** `did:web` and `did:key`. This is
  the interoperability baseline, mirroring Layer 1 §5's "Bearer is MUST" rule.
- Ledger-based methods (`did:ion`, `did:sov`, …) MAY be used *in addition* —
  never as the only identity. Per RFC-0001 **P4**, no blockchain is required.

### 2.2 Relationship to `provider_id`

Layer 1 §4's `agent:<name>:<region>` identifier is **self-reported** and stays
what it always was: a human-readable alias. The DID is authoritative:

- An agent advertises its DID in the ACMP capability object:

```json
{
  "capabilities": {
    "acmp": {
      "version": "0.1.0",
      "role": "provider",
      "did": "did:web:compute.example.com",
      "provider_id": "agent:openclaw-3:us-east"
    }
  }
}
```

- The DID document SHOULD list the alias (e.g. via `alsoKnownAs`), so the
  mapping is verifiable in both directions.
- Where both are present, verifiers MUST treat the DID as the identity and the
  alias as display metadata. Reputation attaches to the DID.

### 2.3 Custody: operator-provisioned, not self-generated

The identity used for **economic operations** (anything that can move CU) MUST
be provisioned by the operator into the wallet. Agents MAY self-generate
ephemeral `did:key` identities for non-economic interactions (browsing,
discovery), but a conforming wallet MUST NOT allow an identity the agent
process generated *itself* to be bound to spendable funds. Note the rule is
about **who provisioned the key, not the DID method**: an operator-provisioned
`did:key` spends just fine (that is the normal buyer setup from §2.1). This
resolves the operator-vs-self-generated question: *both exist, but only
operator-provisioned keys spend.*

### 2.4 Fleets

One wallet MAY serve multiple agent instances. The DID identifies the
**economic actor** (the operator's market persona), not the process instance:
sub-agents of one wallet share its identity, its limits (§6.2) apply
wallet-wide, and reputation accrues to the shared DID. Operators MAY
additionally scope limits per instance; instance-level *identity* (sub-DIDs)
is left `[OPEN]`.

---

## 3. Identity Verification: `acmp/proveIdentity`

A challenge–response that upgrades a self-reported identity to a verified one.
Either peer MAY challenge the other at any point after the MCP handshake;
buyers SHOULD challenge providers before first payment, and an Escrow Agent
SHOULD challenge a payee before first payout.

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/proveIdentity",
  "id": "req_71bb02",
  "params": {
    "nonce": "n_5f0c22d1a9be"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `nonce` | string | yes | Challenger-generated, single-use. Prevents replay. |

**Result:** a signature envelope (§4) over the object `{ "nonce": "<the
nonce>", "did": "<responder's did>" }`:

```json
{
  "envelope": {
    "did": "did:web:compute.example.com",
    "verification_method": "did:web:compute.example.com#key-1",
    "alg": "EdDSA",
    "created_ms": 1783017900000,
    "payload_hash": "sha256:9a1f3c...",
    "signature": "zXk3o2Qb..."
  }
}
```

The challenger resolves the DID document, locates `verification_method`,
recomputes the payload hash, and verifies the signature. Crucially, the
challenger MUST also check that `envelope.did` equals the DID it *expected* —
the one the peer advertised in its capability object, or the bound `payee_id`
in an escrow context. Without this check, any party with any valid DID could
answer the challenge (a classic substitution attack). Failures use the -36xxx
codes (§7).

---

## 4. Signature Envelope

A single, reusable structure for signing any ACMP JSON object:

| Field | Type | Description |
|---|---|---|
| `did` | string | The signer's DID. |
| `verification_method` | string | The DID-document key used, e.g. `did:web:...#key-1`. |
| `alg` | string | Signature algorithm. Verifiers MUST accept both `EdDSA` (Ed25519) and `ES256`; signers SHOULD use `EdDSA`. |
| `created_ms` | number | Signing time, epoch ms. |
| `payload_hash` | string | `sha256:<hex>` over the **JCS canonicalization** ([RFC 8785](https://www.rfc-editor.org/rfc/rfc8785)) of the signed object. |
| `signature` | string | base64url signature over the payload hash. |

The envelope rides in a `sig` field **added to** the object it covers; the
signed object is the object *without* its `sig` field. Verification = resolve
DID → check method → recompute JCS hash → verify signature.

### 4.1 What must be signed

Signing is graded so adoption stays incremental (**P5**) — signatures become
mandatory exactly where money makes disputes likely:

| Object | Level | Why |
|---|---|---|
| Layer 4 `escrowClaim` params (incl. proof) | **MUST** | The claim can move funds against a silent buyer; the agent and any later arbiter need non-repudiable evidence of *who* claimed *what*. |
| Layer 4 `escrowDispute` evidence | **MUST** | Same, buyer side. |
| Layer 6 offer | SHOULD | Binds the provider to its price — prevents offer spoofing and repudiation. |
| Layer 1 result (incl. proof object) | SHOULD | Binds the provider to what it delivered; feeds Layer 3. |
| Any other message | MAY | — |

The MUST rows apply **when the parties operate with DIDs** (i.e. Layer 7 is
adopted): an Escrow Agent whose escrow is DID-bound MUST reject an unsigned or
badly signed `escrowClaim` or `escrowDispute` with the appropriate -36xxx
code. A Layer-4-only deployment without DIDs remains conforming (P5,
incremental adoption) — its claims are simply weaker evidence in a dispute.

---

## 5. Verifiable Credentials

[W3C Verifiable Credentials](https://www.w3.org/TR/vc-data-model/) are the
companion standard for **third-party attestations** — claims about an agent
that the agent cannot credibly make about itself, e.g. capability
certification or CU quality tier:

```json
{
  "@context": ["https://www.w3.org/ns/credentials/v2"],
  "type": ["VerifiableCredential", "AcmpCapabilityCredential"],
  "issuer": "did:web:certifier.example.org",
  "validFrom": "2026-07-01T00:00:00Z",
  "credentialSubject": {
    "id": "did:web:compute.example.com",
    "capability": "sentiment-analysis",
    "tier": "B"
  }
}
```

*(The VC `proof` block is omitted above for brevity; on the wire it is present
and verified per the VC Data Model.)*

Providers MAY attach VCs to Layer 6 offers and to their discovery entries
(Layer 5 / ARD); buyers MAY require a tier VC before accepting an offer. **Who
is trusted as an issuer** — a certification body, a marketplace operator, a
web-of-trust — is an ecosystem question and remains `[OPEN]`.

---

## 6. Wallet Interface

The wallet interface is a **component contract, not a wire protocol** — it is
what a framework plugin implements locally. Bindings per language are an SDK
concern; the contract is:

### 6.1 Balance

`balance(tier?) → { "S": 0.0, "A": 1.25, "B": 3.40 }` — CU credits per tier.
Tier exchange is a market function (RFC-0001 §5, `[OPEN]` there).

### 6.2 Spend authorization

Every outbound economic operation (escrow lock, direct settlement) passes
through `authorize(spend)` with `{ amount_cu, tier, counterparty_did, task_id
}`. The operator MAY configure any of:

| Limit | Meaning |
|---|---|
| `total_cap_cu` | Absolute lifetime/period budget. |
| `rate_cu_per_hour` | Rolling spend rate. |
| `per_task_max_cu` | Ceiling per individual task. |

A spend is permitted only if **all configured limits pass (AND)**. This
resolves the "how are limits expressed" question: all three forms,
conjunctive. Denials MUST be visible to the operator (audit log), and the
agent MUST NOT have any interface to modify limits.

### 6.3 Audit log

Append-only. Each entry MUST record at least:

`ts_ms`, `kind` (`lock` / `bind` / `release` / `reclaim` / `claim` /
`payout-received` / `denied`), `amount_cu`, `tier`, `counterparty` (DID or
alias), `escrow_id`, `task_id`, `op_ref`, `outcome`.

### 6.4 Payout configuration

The wallet publishes where its owner wants to be paid — this is what a Layer 4
Escrow Agent consults at payout time (Layer 4 §7.1):

```json
{
  "payout": [
    { "rail": "credit-ledger", "account": "acct_7f21c0" },
    { "rail": "x402", "network": "base", "asset": "USDC", "address": "0x9a1f..." }
  ]
}
```

Order expresses preference; the payer selects the first mutually supported
rail. At least one entry MUST use a non-blockchain rail or the credit-ledger
path (**P4**).

How this configuration reaches the payer is deployment-specific in v0.1:
typically registered with the Escrow Agent out of band, or carried in the
first economic interaction. Standardizing an in-band field for it (e.g. on
`escrowBind` or `escrowClaim`) is left `[OPEN]`.

### 6.5 Crash recovery

Before sending any mutating Layer 4 message, the wallet MUST durably record
the `op_ref` and intent (write-ahead). After a crash, it re-queries
`acmp/escrowStatus` and re-sends unresolved operations **with the same
`op_ref`** — Layer 4 §3 idempotency guarantees this is safe. This resolves the
"how does a wallet recover mid-escrow" question: recovery is a replay, never a
guess.

---

## 7. Error Codes

Identity and signature verification failures use the `-36xxx` range. They are
**cross-cutting**: any ACMP endpoint that verifies identities (buyers,
providers, Escrow Agents) MAY return them.

| Code | Name | Description |
|---|---|---|
| -36001 | `identity_proof_failed` | `proveIdentity` response missing, malformed, or nonce mismatch. |
| -36002 | `did_unresolvable` | The DID document could not be resolved (method unsupported or fetch failed). |
| -36003 | `signature_invalid` | Envelope verification failed (hash mismatch, bad signature, unknown verification method). |
| -36004 | `credential_invalid` | A presented VC failed verification or is expired. |

---

## Design Decisions

| Question | Decision | Rationale |
|---|---|---|
| Identity standard | **W3C DIDs**, chain-free baseline (`did:key` + `did:web` MUST-resolve) | External standard to bind, not reinvent — same pattern as ARD (L5) and x402 (L4). P4-safe. |
| `provider_id` | **Kept as alias; DID authoritative** | Incremental adoption (P5); no breaking change to Layer 1. |
| Who signs what | **Envelope + graded duty: MUST on claim/dispute evidence, SHOULD on offers/results** | Non-repudiation exactly where funds move; machine-speed friendly (Ed25519). |
| Key custody | **Operator-provisioned in the wallet; agent requests signatures, never sees keys; ephemeral `did:key` cannot spend** | Alignment-leak containment; resolves operator-vs-self-generated. |
| Spend limits | **Cap + rate + per-task, AND-combined, enforced outside the reasoning loop** | All three [OPEN] candidates were legitimate; conjunction is strictly safest. |
| Fleets | **One wallet MAY serve many instances; identity + reputation attach to the wallet's DID** | Reputation must attach to the economic actor, not a process. |
| Crash recovery | **Write-ahead `op_ref` + idempotent replay + `escrowStatus`** | Falls out of Layer 4 §3 for free. |
| Canonicalization | **JCS (RFC 8785)** | Deterministic JSON hashing without inventing a scheme. |

---

## Open Questions

- `[OPEN]` **VC issuer trust:** who may issue capability/tier credentials, and
  how do verifiers discover trustworthy issuers (trust registry, marketplace
  policy, web of trust)?
- `[OPEN]` **Key revocation latency:** DID documents support key rotation
  natively, but how long may verifiers cache resolved documents before a
  revoked key must stop verifying?
- `[OPEN]` **Per-instance identity in fleets:** should sub-agents be
  expressible as sub-DIDs / delegated keys of the wallet DID?

---

## Related

- [RFC-0001 §5](../RFC-0001-vision.md) (CU token; tier economics stay open
  there)
- [Layer 1 — Transport & Invocation](01-transport.md) (§4 self-reported
  `provider_id`, §5 connection auth — both upgraded, not replaced, by DIDs)
- [Layer 3 — Proof of Execution](03-proof-of-execution.md) (signed
  results/proofs feed its verification models)
- [Layer 4 — Escrow & Settlement](04-escrow-settlement.md) (§7.1 payout rail
  selection reads §6.4; claim/dispute evidence signing is MUST)
- [Layer 6 — Negotiation Protocol](06-negotiation-protocol.md) (offer signing)
- [W3C DID Core](https://www.w3.org/TR/did-core/) · [W3C VC Data Model
  2.0](https://www.w3.org/TR/vc-data-model/)

---

*This document is part of the A2Agora specification. Licensed under Apache
2.0.*
