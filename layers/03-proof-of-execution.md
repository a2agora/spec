---
title: "Layer 3 — Proof of Execution"
nav_order: 5
---

# Layer 3 — Proof of Execution

| Field | Value |
|---|---|
| Layer | 3 |
| Status | `draft` |
| Working Group | proof-of-execution |

## Scope

Defines how a buyer gains confidence that a task was actually executed as
agreed, without trusting the provider and without requiring blockchain
infrastructure (RFC-0001 **P4**). This draft specifies the **mechanics** —
a pluggable proof envelope, a registry of proof methods with honest
guarantee levels, and the audit procedures that consume them. It
deliberately does **not** claim to solve verifiable AI inference: the
hardest verification questions are stated precisely (§5) and left open for
community input.

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are
interpreted as in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

Two concepts are kept strictly apart in this layer:

- **Proof artifacts** (§3) — what a *provider attaches* to a result: a
  claim about the execution, with a defined strength.
- **Audit procedures** (§4) — what the *market does* to check such claims:
  dispute-triggered re-execution, or random spot-checks.

---

## 1. The Verification Problem

In a P2P compute market, a provider could return a cached, fabricated, or
cheaper-model result without doing the agreed work. Blockchain networks
solve this with on-chain verification tied to consensus; ACMP must offer a
path without that machinery (P4).

The uncomfortable truth this layer is built around: **for AI workloads,
no cheap artifact can prove correct execution by itself** (§5 explains
why). What a protocol *can* do is (a) make providers **commit** to their
results non-repudiably, (b) make those commitments **auditable** at a
price, and (c) let the market **price the residual risk** via tiers and
reputation. That is exactly the division of labor between this layer,
[Layer 4](04-escrow-settlement.md)'s challenge machinery, and
[Layer 7](07-agent-wallet.md)'s identity and reputation.

---

## 2. Proof Envelope

A proof is a JSON object attached wherever results travel: in the Layer 1
`result.proof` field and in a Layer 4 `escrowClaim.proof`.

```json
{
  "method": "result-hash",
  "hash": "sha256:e3b0c44298fc1c149afbf4c8996fb924..."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `method` | string | yes | A registered proof method (§3). All other fields are method-specific. |

Rules:

- The method is **negotiated up front**: the buyer requests it via the
  Layer 6 `proof_method` term; a provider that cannot deliver it MUST
  reject at quote time and at invoke with -33006 (`proof_unsupported`).
- Proofs SHOULD be signed with the provider's [Layer 7 §4](07-agent-wallet.md)
  envelope; where the parties are DID-bound and the proof backs a Layer 4
  claim or dispute, signing is **MUST** (Layer 7 §4.1). An unsigned proof
  commits nobody to anything.
- Verifiers MUST reject proofs whose `method` differs from the negotiated
  one.

---

## 3. Proof Artifacts (method registry)

Each method carries an honest **guarantee level** — what it actually
establishes, not what one wishes it did:

| Method | Guarantee level | Establishes | Does NOT establish |
|---|---|---|---|
| `result-hash` | **commitment** | The provider is bound to exactly this output (non-repudiable when signed). | That any computation was performed to produce it. |
| `tee-attestation` | **execution integrity** | The declared code ran unmodified inside genuine attested hardware on the given input. | That the code's *semantics* match the offer (attestation covers identity of code, not its quality). |

The registry is **open**: new methods are added by defining their
method-specific fields and guarantee level. Implementations MUST ignore
unknown methods they did not negotiate rather than fail on them.

### 3.1 `result-hash`

`hash` = `sha256:<hex>` over the [JCS (RFC 8785)](https://www.rfc-editor.org/rfc/rfc8785)
canonicalization of the result's `output` object (`{type, data}`) — the
same canonicalization Layer 7 uses for signature payloads. This is the
floor method: cheap, universal, implemented by the
[reference SDK](https://github.com/a2agora/sdk-reference), and honest about
being *only* a commitment. Its value is downstream: a signed result-hash is
exactly the evidence a Layer 4 dispute or an audit (§4) needs.

### 3.2 `tee-attestation` (informative sketch)

For providers running inside trusted execution environments (e.g. AMD
SEV-SNP, Intel TDX):

```json
{
  "method": "tee-attestation",
  "runtime": "sev-snp",
  "measurement": "sha384:71a3...",
  "report": "base64url...",
  "result_hash": "sha256:e3b0c442..."
}
```

The `report` chains the `result_hash` into the hardware attestation, so the
buyer verifies (against the vendor's attestation service) that *the
measured code* produced *this result*. Strong — but it binds trust to
hardware vendors, requires special fleets, and attests code identity, not
output quality. TEE remains **optional**: per P4 and the pluggable
registry, it is one binding, never a requirement. A full normative binding
(report formats, verification flow, measurement policies) is `[OPEN]`.

---

## 4. Audit Procedures

Artifacts are checked by procedures. Two are defined; both consume the
signed commitments from §3.

### 4.1 Re-execution audit (dispute-triggered)

The settlement-side twin of this procedure already exists: Layer 4's
**claim → challenge window → dispute** machinery. Layer 3 supplies what
happens *inside* a dispute:

1. The disputing party's evidence is the signed offer (Layer 6) and the
   signed result + proof (Layer 1/3).
2. An **Audit Executor** — a neutral party in the same spirit as Layer 4's
   Escrow Agent role — re-executes the task from the recorded input under
   the offer's terms.
3. Its verdict (match / no-match / not-comparable) goes to the Escrow
   Agent, whose dispute resolution disburses accordingly (Layer 4 §4.6).

The Audit Executor is a **role, not an implementation**: the escrow agent
itself, a third-party service, or a panel. Neutrality guarantees and audit
economics (who pays for re-execution — loser-pays? deposits?) are `[OPEN]`.
The hard scientific limit of this procedure — when is a re-executed AI
result "the same"? — is §5.

### 4.2 Statistical spot-checking (random)

A marketplace or buyer coalition MAY re-execute a random sample of
completed tasks as audits, feeding results into provider **reputation**
attached to the Layer 7 DID. No per-task proof burden beyond `result-hash`;
protection is probabilistic and prices dishonesty rather than preventing
it. Audit-rate economics and how reputation scores are computed and shared
are `[OPEN]` — but note this procedure is what makes the cheap floor method
meaningful at market scale.

---

## 5. The Determinism Problem (why this layer stays partly open)

Re-execution audits assume a re-run can be compared to the original. For
AI inference this is genuinely hard:

- **Sampling:** generation is stochastic by design; two honest runs differ.
- **Even at temperature 0**, floating-point non-associativity, batching,
  and kernel scheduling produce hardware- and load-dependent divergence.
- **Stack opacity:** providers do not generally disclose weights, runtime,
  and hardware precisely enough to pin a bitwise-reproducible environment.

Consequently, **bitwise comparison of re-executed outputs is not a sound
audit criterion for AI tasks.** Candidate comparison regimes, each with
open trade-offs:

| Regime | Idea | Open problem |
|---|---|---|
| Pinned decoding | temp 0, fixed seed, declared stack | Narrows but does not eliminate divergence; stack disclosure is commercially sensitive. |
| Semantic equivalence | An evaluator judges "same answer?" | Who judges the judge — the recursion reintroduces the trust problem, plus cost. |
| Statistical batch verification | Compare output *distributions* over many tasks | Only detects systematic fraud, not single-task cheating. |
| Domain verifiers | Code → run the tests; math → check the result | Excellent where checking is cheaper than generating; doesn't generalize to open-ended generation. |

Which regime (or mix) becomes normative for `re-execution-audit` verdicts
is **the** open question of this layer — deliberately left to community
input, with this section as the docking point.

---

## Design Decisions

| Question | Decision | Rationale |
|---|---|---|
| TEE hard requirement or pluggable interface? | **Pluggable envelope + open method registry; TEE is one optional binding** | P4 forbids mandating special infrastructure; the registry lets guarantees strengthen over time without breaking the floor. |
| How are proof requirements expressed? | **Resolved by Layer 6:** the `proof_method` term, gated by -33006 at quote and invoke | The stub's question predated the Layer 6 draft. |
| Who arbitrates the optimistic model? | **Audit Executor role inside Layer 4's existing dispute machinery** | Reuses the challenge-window mechanics that already exist; neutrality and economics stay `[OPEN]`. |
| What does `result-hash` prove? | **Honestly: commitment only** | Overclaiming would be worse than a weak floor; its power comes from Layer 7 signatures + auditability. |
| Artifacts vs. procedures | **Separated (§3 vs §4)** | The stub mixed provider-attached proofs with market-side checking; the split makes guarantee levels statable. |
| Determinism | **Stated precisely, not resolved** | Pretending bitwise re-execution works for AI would make the layer wrong; a precise problem statement invites the right contributors. |

---

## Open Questions

- `[OPEN]` **Comparison regime** for re-execution audits (§5) — pinned
  decoding, semantic judging, statistical, domain verifiers, or a
  tier-dependent mix?
- `[OPEN]` **Audit Executor neutrality and economics:** who may act as
  one, and who pays for re-execution (loser-pays, deposits, insurance)?
- `[OPEN]` **Full TEE binding:** normative report formats and verification
  flows per runtime (SEV-SNP, TDX).
- `[OPEN]` **Spot-check economics:** audit rates, reputation computation,
  and cross-marketplace reputation portability (Layer 7 DIDs make it
  *attachable*; making it *comparable* is unsolved).

---

## Related

- [RFC-0001 §7.1](../RFC-0001-vision.md) — "Proof of Execution without blockchain", the founding open question
- [Layer 1 — Transport & Invocation](01-transport.md) — `result.proof`, `proof_method`, -33006
- [Layer 4 — Escrow & Settlement](04-escrow-settlement.md) — claim/challenge/dispute machinery that audits plug into
- [Layer 6 — Negotiation Protocol](06-negotiation-protocol.md) — `proof_method` as a negotiated term
- [Layer 7 — Wallet & Identity](07-agent-wallet.md) — signature envelope (proofs as evidence), DID-anchored reputation

---

*This document is part of the A2Agora specification. Licensed under Apache 2.0.*
