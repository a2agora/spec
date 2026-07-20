---
title: "Layer 5 — Discovery (ARD)"
nav_order: 7
---

# Layer 5 — Discovery (ARD Binding)

| Field | Value |
|---|---|
| Layer | 5 |
| Status | `external` |
| Working Group | discovery |
| Upstream | [ARD — Agentic Resource Discovery](https://agenticresourcediscovery.org) |

## Scope

Layer 5 is **not specified by ACMP**. Capability discovery is delegated to the
[Agentic Resource Discovery (ARD)](https://agenticresourcediscovery.org)
specification, an industry-backed open standard developed by Microsoft,
Google, Nvidia, Hugging Face, Salesforce, and others.

ARD defines how agents publish, index, and discover capabilities. ACMP
consumes ARD as its discovery layer and extends it with an **ACMP binding** —
additional metadata fields needed for economic interaction.

## What ARD Provides

- Agents publish lightweight manifests describing their capabilities
- Discovery services crawl and index these manifests
- AI clients query discovery services using natural language or structured
  search
- Results include what a resource does, its provider, location, and invocation
  method

## What ACMP Adds (the Binding)

ARD answers *"what exists?"* — ACMP needs to also know *"what does it cost?"*.
The ACMP binding extends an ARD resource entry with:

```json
{
  "ard:resource": "openclaw-3.example.com",
  "ard:capabilities": ["sentiment-analysis", "code-execution", "vision"],

  "acmp:tier": "A",
  "acmp:price_cu_per_1k_tokens": 0.004,
  "acmp:latency_p99_ms": 800,
  "acmp:availability": 0.997,
  "acmp:proof_methods": ["result-hash", "tee-attestation"],
  "acmp:negotiation_endpoint": "https://openclaw-3.example.com/acmp/negotiate"
}
```

The `ard:` fields come from the ARD manifest. The `acmp:` fields are the
economic extension that enables negotiation (Layer 6), escrow (Layer 4), and
proof of execution (Layer 3).

## Why Not Build Our Own Registry?

ARD is backed by Microsoft, Google, Nvidia, and a dozen other major companies.
Building a competing discovery layer would be:

1. **Redundant** — ARD already solves the discovery problem
2. **Adoption-hostile** — agents would need to integrate two discovery
   protocols instead of one
3. **Counter to P1 (layer independence)** — by delegating discovery, ACMP
   focuses on what no one else is building: the economic layer

## Open Questions

- `[OPEN]` How is the ACMP binding published alongside an ARD manifest —
  inline extension or separate endpoint?
- `[OPEN]` How are `acmp:price` fields kept up-to-date as market conditions
  change (push vs. pull)?
- `[OPEN]` Can the ACMP binding be discovered via ARD itself (meta-discovery)?

## Related

- [Layer 6 — Negotiation Protocol](06-negotiation-protocol.md) (consumes
  discovery results)
- [Layer 3 — Proof of Execution](03-proof-of-execution.md) (proof methods
  advertised here)
- [ARD Specification](https://agenticresourcediscovery.org)
