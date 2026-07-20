---
title: "Layer 1 — A2A Binding (shallow)"
nav_order: 3.5
---

# Layer 1 — A2A Binding (shallow)

| Field | Value |
|---|---|
| Layer | 1 (additive binding) |
| Status | `draft` |
| Working Group | transport |

## Scope

This document specifies an **additive** Layer 1 binding onto the [Agent2Agent
Protocol (A2A)](https://github.com/a2aproject/A2A), alongside the MCP binding
in [`01-transport.md`](01-transport.md). It does not change that document —
MCP remains the baseline, unmodified. A provider MAY advertise this binding in
addition to, or instead of, the MCP one; Layer 5 discovery and the buyer's own
transport preference decide which connection is opened. There is no
protocol-level precedence rule between the two bindings.

This is the **shallow** strategy named in
[A2A-MAPPING.md](../A2A-MAPPING.md#two-binding-strategies): ACMP's existing
JSON-RPC messages travel unchanged inside an A2A envelope. The **deep**
strategy — remodeling ACMP semantics natively onto A2A's task state machine —
remains future work; see [Open Questions](#open-questions).

### Normative Language

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**
in this document are to be interpreted as described in [RFC
2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 1. Envelope

ACMP's existing JSON-RPC 2.0 messages ([Layer 1 §2–§3](01-transport.md), byte-
identical, no schema change) travel inside the `data` Part of an A2A
`Message`:

```json
{
  "message_id": "msg_9c2f11",
  "role": "user",
  "task_id": "task_a7c923f1",
  "parts": [
    {
      "data": {
        "acmp_method": "acmp/invoke",
        "params": {
          "task_id": "task_a7c923f1",
          "capability": "sentiment-analysis",
          "input": { "type": "text", "data": "Revenue grew 12% YoY." },
          "max_price_cu": 0.005,
          "escrow_id": "esc_a3f9c2"
        }
      },
      "media_type": "application/acmp+json"
    }
  ]
}
```

- `media_type` (the A2A `Part` field carrying the MIME type) MUST be
  `application/acmp+json` on every `data` Part carrying an ACMP message.
- The `data` Part's root object MUST be `{"acmp_method": "<method>", "params":
  {...}}` for requests and notifications. Responses and errors carry
  `acmp_result`/`acmp_error` as the root key instead, with the same field
  contents as the corresponding JSON-RPC `result`/`error` object in [Layer 1
  §3](01-transport.md#3-message-schemas).
- `task_id` is carried in **both** places: the A2A `Message.task_id` field
  (for A2A-native correlation without parsing the payload) and, unchanged,
  inside the ACMP `params` (for ACMP-side processing). This redundancy is
  intentional.
- No ACMP field is hoisted into `Message.metadata`. See
  [§3.1](#31-field-placement-escrow_id-proof_method-max_price_cu).

---

## 2. Capability Negotiation via Agent Card

A2A has no equivalent to MCP's `initialize` handshake. The `acmp` capability
object from [Layer 1 §1](01-transport.md#1-mcp-extension-model) is instead
carried as the `params` of an `AgentExtension` entry in the provider's Agent
Card — declared, per the A2A specification, inside `capabilities.extensions`
(an `AgentExtension` has `uri`, `description`, `required`, and `params`):

```json
{
  "capabilities": {
    "streaming": true,
    "extensions": [
      {
        "uri": "https://a2agora.org/acmp/v0.1",
        "description": "ACMP Layer 1 shallow binding",
        "params": {
          "version": "0.1.0",
          "role": "provider",
          "accepts": ["acmp/invoke", "acmp/cancel"],
          "emits": ["acmp/streamChunk", "acmp/heartbeat"],
          "features": {
            "output_streaming": true,
            "input_streaming": false,
            "heartbeat_interval_ms": 5000
          }
        }
      }
    ]
  }
}
```

Field meanings inside `params` are identical to [Layer 1
§1](01-transport.md#1-mcp-extension-model) — this is the same object, carried
at a different location. A buyer MUST NOT rely on a feature the provider did
not advertise here, exactly as it would not over the MCP binding. The provider
MAY set the extension's `required` flag to `true` if it serves ACMP traffic
exclusively; it SHOULD leave it `false` when the same Agent Card also serves
plain A2A clients.

---

## 3. Resolved Questions

[A2A-MAPPING.md](../A2A-MAPPING.md#open-questions) left four sub-questions
open. This binding resolves three of them; the fourth is a Layer 6 question
and stays open.

### 3.1 Field placement (`escrow_id`, `proof_method`, `max_price_cu`)

These fields stay exactly where [Layer 1 §3.1](01-transport.md#31-acmpinvoke)
puts them: inside the ACMP JSON-RPC payload in the `data` Part. None are
hoisted to top-level `Message.metadata`. Promoting fields to metadata would
already be a step toward the deep strategy — the shallow strategy's entire
value is that the ACMP schema does not change.

### 3.2 Heartbeat / liveness

`acmp/heartbeat` notifications travel exactly like `acmp/streamChunk`: as
another `data`-Part message over the same A2A streaming channel
(`SendStreamingMessage` / SSE). No new A2A mechanism is introduced. As in
[Layer 1 §1](01-transport.md#1-mcp-extension-model), heartbeat remains
optional and capability-gated (`heartbeat_interval_ms`).

### 3.3 Input streaming (`acmp/inputChunk`)

**Not supported** by this binding. A provider offering this binding MUST
advertise `input_streaming: false` in its capability object
([§2](#2-capability-negotiation-via-agent-card)) — this is already an
optional, capability-gated feature in [Layer 1
§1](01-transport.md#1-mcp-extension-model), so declining it here changes
nothing structurally. This is a deliberate, documented gap rather than a
forced-fit approximation.

### 3.4 Error mapping

An ACMP error ([Layer 1 §3.3](01-transport.md#33-acmperror), codes `-33xxx`)
stays entirely inside the payload: the enclosing A2A task reaches `completed`
regardless. A2A has no knowledge of ACMP semantics and sees only a
successfully delivered `data` Part. Generic A2A tooling (task lists,
monitoring dashboards) sees an ACMP error only if it parses the payload — an
accepted trade-off of the shallow strategy, not a defect to fix here.

---

## Design Decisions

| Question | Decision | Rationale |
|---|---|---|
| Shallow or deep? | **Shallow** | Zero schema change, lowest risk, serves Principle P5 (incremental adoptability). Deep remains future work — see [Open Questions](#open-questions). |
| Field placement? | **Inside the `data` Part, not `Message.metadata`** | Consistent with zero schema change. |
| Capability transport? | **Extension `params` on the Agent Card** | A2A has no `initialize` equivalent; the Agent Card is the only static declaration point available. |
| Error mapping? | **Payload-internal; the A2A task stays `completed`** | Consistent with shallow — the binding needs no knowledge of A2A's state machine. |
| Input streaming? | **Not supported** | An honest gap rather than a forced fit; already optional and capability-gated in Layer 1. |

---

## Open Questions

- `[OPEN]` **Deep-remodel strategy.** Remodeling ACMP semantics natively onto
  A2A's `SendMessage`/`GetTask`/`CancelTask`/`SendStreamingMessage` and its
  8-state task machine — touching every Layer 1 message schema and several
  Layer 2/6 assumptions — is deliberately out of scope here. See
  [A2A-MAPPING.md](../A2A-MAPPING.md#two-binding-strategies). It would let
  ACMP inherit A2A's `input-required`/`auth-required` resumable-interrupt
  states essentially for free, closing the gap noted in [Layer 1's own Open
  Questions](01-transport.md#open-questions) — but it is a substantially
  bigger undertaking that deserves its own dedicated design work if pursued.
- `[OPEN]` **Negotiation via `input-required` (cross-layer note).** A2A's
  resumable-interrupt states could plausibly give Layer 6 (negotiation) a
  native "task paused, awaiting counter-offer" mechanism. This is a Layer 6
  question, not a Layer 1 one — noted here as a pointer, not resolved. See
  [Layer 6](06-negotiation-protocol.md).

---

## Related

- [Layer 1 — Transport & Invocation](01-transport.md) — the MCP baseline,
  unchanged
- [A2A-MAPPING.md](../A2A-MAPPING.md) — the analysis and rationale behind this
  binding
- [RFC-0001 §7](../RFC-0001-vision.md#7-open-questions)

---

*This document is part of the A2Agora specification. Licensed under Apache
2.0.*
