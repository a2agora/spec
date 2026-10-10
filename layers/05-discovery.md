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
| Substrate | [ARD — Agentic Resource Discovery](https://agenticresourcediscovery.org/spec/) v0.91 (Proposal, 2026-08-26) |

## Scope

Layer 5 is **not specified by ACMP**. Capability discovery is delegated to the
[Agentic Resource Discovery (ARD)](https://agenticresourcediscovery.org)
specification, an industry-backed open standard developed by Microsoft,
Google, Nvidia, Hugging Face, Salesforce, and others.

ARD defines how agents publish, index, and discover capabilities. ACMP
consumes ARD as its discovery layer and extends it with an **ACMP binding** —
additional metadata fields needed for economic interaction.

This binding targets ARD **v0.91**. That revision still has *Proposal* status,
and ARD notes that the card media types it uses are not yet IANA-registered
and may change; the binding follows the pinned revision and will be re-pinned
when ARD moves.

## What ARD Provides

- Agents publish lightweight manifests describing their capabilities
- Discovery services crawl and index these manifests
- AI clients query discovery services using natural language or structured
  search
- Results include what a resource does, its provider, location, and invocation
  method

## What ACMP Adds (the Binding)

ARD answers *"what exists?"* — ACMP needs to also know *"what does it cost?"*.
The ACMP binding adds terms to an ordinary ARD entry. A provider publishes the
entry in the `entries` array of `https://{domain}/.well-known/ard.json` (ARD
§5.1):

```json
{
  "entries": [
    {
      "@context": [
        "https://agenticresourcediscovery.org/context/v1",
        {
          "acmp": "https://a2agora.org/acmp/v0.1#",
          "acmp:price_cu_indicative": { "@type": "@json" }
        }
      ],
      "identifier": "urn:air:example.com:acmp:openclaw-3",
      "displayName": "OpenClaw-3",
      "type": "application/mcp-server-card+json",
      "url": "https://openclaw-3.example.com/mcp/server-card.json",
      "capabilities": ["sentiment-analysis", "code-execution", "vision"],
      "representativeQueries": [
        "classify the sentiment of these customer reviews",
        "run this Python snippet and return the output"
      ],

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
  ]
}
```

The unprefixed terms are ARD's own (ARD §4.2): `identifier`, `displayName`,
`type`, and `url` are required, `capabilities` and `representativeQueries` are
the discovery signals a registry indexes. The `acmp:` terms are the economic
extension that enables negotiation (Layer 6), escrow (Layer 4), and proof of
execution (Layer 3).

**The entry describes the provider's transport card, not an ACMP artifact.**
`type` is the media type of the card the provider is reached through —
`application/mcp-server-card+json` for the [MCP
binding](01-transport.md), `application/a2a-agent-card+json` for the [A2A
binding](01-transport-a2a-binding.md) — and `url` points at that card. ACMP
defines no artifact type of its own: discovery finds an MCP server or A2A agent
like any other, and the `acmp:` terms say that it also trades.

**The ACMP namespace.** ARD v0.91 treats an entry as a JSON-LD node and admits
terms from any namespace the entry declares in its `@context` (ARD §4.1).
ACMP's namespace IRI is `https://a2agora.org/acmp/v0.1#` — the same URI the A2A
binding uses as its extension identifier, with `#` appended so that terms
resolve to `https://a2agora.org/acmp/v0.1#tier` and so on. Registries match
namespaced terms **by IRI, not by prefix**: a publisher that binds the
namespace to a different prefix is still found by the same filter, while a
term under an `acmp` prefix bound to any other IRI is simply not an ACMP term.

`acmp:price_cu_indicative` is declared `@json` because it is the one ACMP term
whose value is an object with free-form keys. Without that declaration, JSON-LD
expansion under ARD's base context — which maps unknown keys into the ARD
namespace — would turn each capability tag into an ARD property and lose the
map. All other ACMP terms are plain literals and need no declaration.

ACMP prices **tasks, not tokens** ([RFC-0001 §5](../RFC-0001-vision.md)), so
the advertised price is denominated per task: `acmp:price_cu_indicative` quotes
one CU figure per advertised capability — keyed by the same `capabilities`
token Layer 6 quotes against — measured on the reference task that
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

**Filtering on ACMP terms is registry-dependent.** ARD makes namespaced terms
available as filter dimensions, but support for them beyond ARD's standard
terms is registry-defined, and a registry MAY reject a filter on an
unsupported term path with `400` (ARD §5.3.1). A buyer therefore cannot rely
on server-side filtering by `acmp:tier` or price. It can always search on
ARD's standard terms and apply the `acmp:` terms client-side to the entries
returned — which is all the binding requires, since the figures only shortlist
providers for Layer 6.

## Why Not Build Our Own Registry?

ARD is backed by Microsoft, Google, Nvidia, and a dozen other major companies.
Building a competing discovery layer would be:

1. **Redundant** — ARD already solves the discovery problem
2. **Adoption-hostile** — agents would need to integrate two discovery
   protocols instead of one
3. **Counter to P1 (layer independence)** — by delegating discovery, ACMP
   focuses on what no one else is building: the economic layer

## Open Questions

- `[OPEN]` ARD v0.91 settles *where* the binding lives: inline, as namespaced
  terms in the entry. Does ACMP additionally need a separate endpoint — for
  example for figures that change faster than a crawled manifest is
  re-indexed — or is the Layer 6 quote enough for anything time-sensitive?
- `[OPEN]` Should a vocabulary or JSON-LD context document be published at
  `https://a2agora.org/acmp/v0.1#`, so that generic tooling can resolve the
  `acmp:` terms (including the `@json` declaration) without each entry
  restating them — and who maintains it?
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
- [ARD Specification v0.91](https://agenticresourcediscovery.org/spec/) and its
  [base JSON-LD context](https://agenticresourcediscovery.org/context/v1)
