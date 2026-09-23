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
| Substrate | [ARD — Agentic Resource Discovery](https://agenticresourcediscovery.org) — no published revision to pin |

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
  "acmp:price_cu_indicative": {
    "sentiment-analysis": 0.003,
    "code-execution": 0.012,
    "vision": 0.008
  },
  "acmp:price_basis": "acmp:reference-tasks/v1",
  "acmp:latency_p99_ms": 800,
  "acmp:availability": 0.997,
  "acmp:proof_methods": ["result-hash", "tee-attestation"],
  "acmp:negotiation_endpoint": "https://openclaw-3.example.com/acmp/negotiate"
}
```

The `ard:` fields come from the ARD manifest. The `acmp:` fields are the
economic extension that enables negotiation (Layer 6), escrow (Layer 4), and
proof of execution (Layer 3).

ACMP prices **tasks, not tokens** ([RFC-0001 §5](../RFC-0001-vision.md)), so
the advertised price is denominated per task: `acmp:price_cu_indicative` quotes
one CU figure per advertised capability — keyed by the same ARD capability tag
Layer 6 quotes against — measured on the reference task that
`acmp:price_basis` names. Both parts are needed: without a shared reference
task, two providers' figures describe different work and cannot be compared.
The `acmp:price_basis` value above is illustrative — what such a catalogue
contains, and who publishes it, is an open question below.

The figure is **informational only**. It exists so a buyer can shortlist
providers before negotiating, and it binds no one. The binding price is the
`price_cu` of a [Layer 6](06-negotiation-protocol.md) offer, which covers the
task actually requested rather than the reference one.

Only the price is broken out per capability here. `acmp:availability` describes
the endpoint and is provider-wide by nature; whether `acmp:tier` and
`acmp:latency_p99_ms` should vary per capability as the price does is not
settled by this binding.

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
- `[OPEN]` How are `acmp:price_cu_indicative` figures kept up-to-date as market
  conditions change (push vs. pull)?
- `[OPEN]` Who defines the reference task behind `acmp:price_basis`, and who may
  publish or version such a catalogue? Compare the CU tier-definition question
  ([RFC-0001 §7](../RFC-0001-vision.md), question 2) — its candidate **Assessor**
  role maintains benchmark definitions, and a reference task is one.
- `[OPEN]` Can the ACMP binding be discovered via ARD itself (meta-discovery)?

## Related

- [Layer 6 — Negotiation Protocol](06-negotiation-protocol.md) (consumes
  discovery results)
- [Layer 3 — Proof of Execution](03-proof-of-execution.md) (proof methods
  advertised here)
- [ARD Specification](https://agenticresourcediscovery.org)
