# Layer 3 — Proof of Execution

| Field | Value |
|---|---|
| Layer | 3 |
| Status | `discussion` |
| Working Group | proof-of-execution |

## Scope

Defines how a compute consumer can verify that a task was actually executed by the claimed provider, without requiring trust in the provider and without blockchain infrastructure.

## Why This Is Hard

In a P2P compute market, a provider could return a cached or fabricated result without doing the actual work. The buyer needs a way to detect this. Blockchain-based systems solve this with on-chain verification (e.g. Bittensor's proof-of-useful-work), but ACMP must support a non-blockchain path.

## Candidate Approaches

### A — Trusted Execution Environment (TEE)
The compute job runs inside an Intel SGX or AMD SEV enclave. The enclave produces a cryptographic attestation report that proves the specific code ran on the specific hardware. The buyer verifies the attestation without trusting the provider.

**Pros:** Strong cryptographic guarantee, no trusted third party needed.  
**Cons:** Requires TEE-capable hardware, significant operational complexity.

### B — Optimistic Execution + Challenge Period
The provider posts a result hash. The buyer accepts optimistically. If the buyer suspects fraud, it triggers a challenge within a time window. A neutral re-executor (the platform or a third-party auditor) re-runs the task and arbitrates.

**Pros:** Simple, low overhead for honest providers.  
**Cons:** Introduces a centralized arbiter, challenge period adds latency to dispute resolution.

### C — Statistical Spot-Checking
A random subset of tasks are re-executed by the platform as audits. Providers with high fraud rates are penalized via reputation score. No per-task proof required.

**Pros:** Very low per-task overhead.  
**Cons:** Probabilistic only — determined attackers can game the audit rate.

## Open Questions

- `[OPEN]` Is TEE a hard requirement, or should the spec define a pluggable proof interface?
- `[OPEN]` Who acts as arbiter in the Optimistic model, and how is arbiter neutrality guaranteed?
- `[OPEN]` How are proof requirements expressed in a task RFQ?
