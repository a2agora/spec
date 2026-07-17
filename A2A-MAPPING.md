---
title: "A2A Mapping"
nav_order: 10
---

# A2A Mapping: Layer 1 Transport Compared to the Agent2Agent Protocol

| Field | Value |
|---|---|
| Type | Informative note (not a layer, not normative) |
| Status | `draft` |
| Relates to | [Layer 1 — Transport & Invocation](layers/01-transport.md), [RFC-0001 §7](RFC-0001-vision.md) |

> **This document is informative, not normative.** It introduces no new
> RFC 2119 requirements and does not change Layer 1. It exists to answer
> [RFC-0001 §7, open question 5](RFC-0001-vision.md#7-open-questions) with a
> grounded comparison rather than a bare link — the question itself
> **remains open** by design; see [Conclusion](#conclusion).

## Why this document exists

Layer 1 is specified as an MCP extension. MCP is *vertical* — an agent
calling tools. ACMP's buyer and provider are both autonomous, negotiating
peer agents: the *horizontal* shape that the [Agent2Agent Protocol
(A2A)](https://github.com/a2aproject/A2A) — originated by Google, now its
own [Linux Foundation](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year)
project — targets directly. RFC-0001 has flagged this as an open question
since the MCP-vs-A2A ecosystem positioning was researched; this document is
the systematic mapping that question called for, done once instead of
re-litigated informally.

## A2A in brief

Facts below are drawn from the [A2A specification](https://a2a-protocol.org/latest/specification/)
and the canonical [`a2a.proto`](https://github.com/a2aproject/A2A) definition.

- **Transport:** JSON-RPC 2.0 (baseline), gRPC, and REST — three bindings,
  functionally equivalent wire semantics. Core RPCs: `SendMessage`,
  `SendStreamingMessage` (SSE), `GetTask`, `ListTasks`, `CancelTask`,
  `SubscribeToTask`.
- **Task state machine:** eight explicit states — `submitted`, `working`,
  `completed`, `failed`, `canceled`, `rejected`, `input-required`,
  `auth-required`.[^1] The first six are the "normal" lifecycle (four of
  them terminal); the last two are *resumable interrupts* — the task pauses
  and waits for another message before continuing.
- **Message/Part model:** a `Message` carries `message_id`, `role`
  (`user`/`agent`), one or more `parts`, and optional `context_id`/`task_id`/
  `metadata`/`extensions`. A `Part` is one of `text`, `raw` (bytes), `url`,
  or `data` (structured JSON) — each with optional `mime_type`.
- **Agent Card:** published at `/.well-known/agent-card.json`. Declares
  `name`, `description`, `version`, `supported_interfaces` (one entry per
  transport binding), `capabilities` (streaming/push/extensions feature
  flags), `security_schemes`, `default_input_modes`/`default_output_modes`,
  and `skills` (the capabilities the agent offers, each with `id`,
  `description`, `input_modes`, `output_modes`).
- **Push notifications:** `TaskPushNotificationConfig` registers a webhook
  URL per task; the agent then POSTs `TaskStatusUpdateEvent`/
  `TaskArtifactUpdateEvent` on change, instead of the client polling.
- **Extensibility:** an Agent Card can declare `extensions` — URIs
  identifying protocol extensions the agent supports. **[Agent Payments
  Protocol (AP2)](https://github.com/google-agentic-commerce/ap2)** is a
  real, shipped example: it extends A2A's task lifecycle with
  payment-negotiation and settlement steps, declared as an extension URI —
  see [AP2 precedent](#the-ap2-precedent) below.
- **Identity:** A2A has **no protocol-level caller-identity field**.
  `role` on a `Message` is a direction marker (`user` vs. `agent`), not
  authentication. Callers are authenticated entirely at the transport layer
  via the `security_schemes` an Agent Card declares (API key, HTTP auth,
  OAuth2, OIDC, mTLS); v1.0 adds *Signed* Agent Cards for card-authenticity
  verification.

## Message mapping

| ACMP (Layer 1) | Direction | A2A equivalent | Note |
|---|---|---|---|
| `acmp/invoke` | buyer → provider | `SendMessage` (implicitly creates a Task) | ACMP starts execution in one call; A2A separates sending a message from later querying task state. |
| `acmp/result` | provider → buyer | Task reaches `completed`, fetched via `GetTask` or embedded in the `SendMessage` response | — |
| `acmp/error` | provider → buyer | Task reaches `failed` (runtime error) or `rejected` (declined before starting) | ACMP's single error channel maps onto two distinct A2A terminal states. |
| `acmp/streamChunk` | provider → buyer | `SendStreamingMessage` SSE stream / `TaskArtifactUpdateEvent` | — |
| `acmp/heartbeat` | provider → buyer | **No clean equivalent** | A2A has no documented pure liveness-ping; see [Open Questions](#open-questions). |
| `acmp/cancel` | buyer → provider | `CancelTask` | Direct, clean match. |
| `acmp/inputChunk` | buyer → provider | **No direct equivalent** | Closest A2A pattern is a follow-up `Message` on the same `task_id` after `input-required` — a discrete request/response exchange, not continuous chunk streaming. |

## State model comparison

ACMP has no explicit state field at Layer 1 — state is implicit in which
message was last exchanged (`invoke` sent → running; `result`/`error`
received → done). A2A makes state explicit and richer:

| A2A state | Terminal? | ACMP Layer 1 equivalent |
|---|---|---|
| `submitted` | No | Implicit: between `acmp/invoke` sent and any response |
| `working` | No | Implicit: same window; `acmp/heartbeat` may arrive here |
| `completed` | Yes | `acmp/result` received |
| `failed` | Yes | `acmp/error` received (runtime failure) |
| `canceled` | Yes | `acmp/error` with `-33004` after `acmp/cancel` |
| `rejected` | Yes | `acmp/error` (e.g. `-33002` capability_not_found), sent before work starts |
| `input-required` | No (resumable) | **No equivalent** |
| `auth-required` | No (resumable) | **No equivalent** |

The two resumable-interrupt states are the interesting gap: ACMP's Layer 1
and Layer 2 (task DAGs) assume fire-and-execute — a provider either
completes, streams, or fails, but never pauses mid-task to ask the buyer a
question and resume later. Layer 6 (negotiation) *does* have a
request/offer/accept round trip, but that happens entirely before
`acmp/invoke`, not as a pause within an in-flight task.

## The AP2 precedent

A2A's own ecosystem has already solved a structurally similar problem: **AP2
(Agent Payments Protocol)** adds payment negotiation and settlement to A2A's
task lifecycle, declared as an extension URI in the Agent Card rather than
forking or replacing A2A itself. This is not a blueprint ACMP could adopt
verbatim — AP2 and ACMP make different design choices (AP2 is scoped to
payment authorization; ACMP additionally covers compute-specific
negotiation, escrow, and proof of execution) — but it is a concrete
existence proof: **A2A's own community treats "layer an economic protocol
on top of A2A as a declared extension" as an already-solved, shipping
pattern**, not a hypothetical. That materially lowers the perceived risk of
a hypothetical ACMP-on-A2A binding — the extension mechanism this would
need already has a production precedent.

## Two binding strategies

If Layer 1 were ever to gain an A2A binding (alongside, not instead of, the
MCP one — see [Conclusion](#conclusion)), two strategies look structurally
different enough to name separately:

| | **Shallow: DataPart envelope** | **Deep: native remodel** |
|---|---|---|
| **Approach** | Carry ACMP's existing JSON messages unchanged inside an A2A `data` Part; A2A is purely the enclosing session/transport. | Remodel ACMP semantics natively onto `SendMessage`/`GetTask`/`CancelTask`/`SendStreamingMessage` and the 8-state machine. |
| **Wire-format stability** | ACMP's existing schemas (§3 of Layer 1) stay byte-identical. | ACMP's schemas would need to be re-expressed as A2A Messages/Parts/states — a real redesign. |
| **Uses A2A-native features** | Minimal — A2A's task persistence, push notifications, and state machine go unused. | Full — gets A2A's push notifications, task history, and resumable-interrupt states essentially for free. |
| **Migration cost** | Low — an additional transport binding, MCP untouched. | High — touches every Layer 1 message schema and several Layer 2/6 assumptions. |

Both are legitimate designs, not a forced choice — Principle P1 (layer
independence) already means Layer 1 could support multiple bindings
simultaneously. Our own assessment, offered as engineering judgment rather
than a decision: the shallow strategy looks like the lower-risk entry
point, precisely because it is the strategy that best serves P5
(incremental adoptability) — it adds a binding without touching anything
that already works. The deep strategy is the more *interesting* one
long-term (it would let ACMP inherit A2A's `input-required` pause/resume
for free, closing the gap noted above), but it is a substantially bigger
undertaking that deserves its own dedicated design work if pursued.

**Illustrative example — the shallow strategy, concretely.** The existing
`acmp/invoke` request (Layer 1 §3.1):

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/invoke",
  "id": "req_8f3a1b",
  "params": {
    "task_id": "task_a7c923f1",
    "capability": "sentiment-analysis",
    "input": { "type": "text", "data": "Revenue grew 12% YoY." },
    "max_price_cu": 0.005,
    "escrow_id": "esc_a3f9c2"
  }
}
```

carried unchanged inside an A2A `SendMessage` call:

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
      "mime_type": "application/acmp+json"
    }
  ]
}
```

The provider would declare this binding the same way AP2 declares itself —
an `acmp` extension URI in its Agent Card, analogous to Layer 1's existing
`acmp` capability object in the MCP `initialize` handshake:

```json
{
  "extensions": ["https://a2agora.org/acmp/v0.1"],
  "capabilities": { "supports_streaming": true, "supports_extensions": true }
}
```

## Identity: a near-match, not a gap

At first glance, A2A having *no* protocol-level identity field looks like a
gap next to ACMP's `provider_id` (Layer 1 §4). Looking closer, it is closer
to a near-match: ACMP's `provider_id` is explicitly **self-reported, not
cryptographically verified at Layer 1** — real identity assurance is
deferred to [Layer 7](layers/07-agent-wallet.md) (DIDs, signature
envelopes). A2A takes the same posture one step further: it doesn't even
carry a self-reported identity field at the protocol level, relying
entirely on transport-layer auth (`security_schemes`) plus, from v1.0,
cryptographically Signed Agent Cards. Both protocols agree that Layer
1-equivalent identity claims are not where real trust should live — they
just draw the line in slightly different places.

## Discovery comparison

| | A2A Agent Card | ACMP |
|---|---|---|
| Capability list | `skills[]` (`id`, `description`, `input_modes`, `output_modes`) | Layer 1 `acmp` capability object (`accepts`, `emits`, `features`) + [Layer 5](layers/05-discovery.md) (ARD binding, `external` status) |
| Feature flags | `capabilities` (streaming/push/extensions booleans) | Layer 1 `features` map (`output_streaming`, `input_streaming`, `heartbeat_interval_ms`) |
| Endpoint location | `supported_interfaces[]` (one per transport binding) | Layer 5 ARD resource descriptor (MCP endpoint URI) |
| Fetch location | `/.well-known/agent-card.json` | No fixed well-known path — delegated entirely to Layer 5/ARD |

Structurally close: both separate *what an agent can do* (skills / ACMP
capability tags) from *where to reach it* (interfaces / ARD descriptor).
ACMP currently has no single well-known-URL convention the way A2A does —
that's a Layer 5 question, out of this document's scope.

## Open Questions

- `[OPEN]` **`escrow_id`/`proof_method`/`max_price_cu` mapping:** if the
  shallow binding were pursued, would these travel inside the `data` Part
  (as sketched above) or as top-level `Message.metadata`? Metadata is
  visible without parsing the ACMP payload, which may matter for A2A-native
  routing/observability tooling, but duplicates data.
- `[OPEN]` **Heartbeat/liveness equivalent:** A2A has no documented
  pure liveness-ping. `TaskStatusUpdateEvent` repeated at `working` could
  approximate it, but that requires the push-notification webhook
  machinery to be configured, unlike ACMP's heartbeat which is a plain
  notification on the existing connection.
- `[OPEN]` **`acmp/inputChunk` equivalent:** does a genuinely streaming
  input pipeline (Layer 2 §5) have *any* clean A2A expression, or is
  chunked input streaming simply a capability ACMP has that A2A's
  discrete-message model doesn't offer today?
- `[OPEN]` **Negotiation via `input-required` (cross-layer note):** A2A's
  resumable-interrupt states could plausibly give Layer 6 (negotiation) a
  native "task paused, awaiting counter-offer" mechanism it doesn't have
  today. This is a Layer 6 question, not a Layer 1 one — noted here as a
  pointer, not resolved.

## Conclusion

RFC-0001 §7's question — *"Is A2A the more natural substrate, or should
Layer 1 bind to both? Or is a standalone transport warranted?"* — **remains
open.** What this document adds is not an answer but a grounded starting
point: a concrete message mapping, a named precedent (AP2) that makes an
A2A binding look architecturally plausible rather than speculative, two
named strategies with different risk profiles, and four specific unresolved
sub-questions a future working group would need to close. Per Principle P1
(layer independence), nothing here requires choosing MCP *or* A2A — a dual
binding remains structurally available whenever the community is ready to
pursue it.

[^1]: Verified against the `a2a.proto` `TaskState` enum
    (`TASK_STATE_SUBMITTED`, `TASK_STATE_WORKING`, ...). The lowercase
    hyphenated forms used throughout this document are this document's own
    readable rendering for comparison purposes, not independently confirmed
    as the literal JSON-RPC/REST wire string values — check `a2a.proto` or
    the JSON-RPC binding directly before treating them as normative.

## Related

- [RFC-0001 §7](RFC-0001-vision.md) — the open question this document addresses
- [Layer 1 — Transport & Invocation](layers/01-transport.md) — the MCP binding this compares against
- [Layer 6 — Negotiation Protocol](layers/06-negotiation-protocol.md) — the cross-layer note on `input-required`
- [A2A Protocol](https://github.com/a2aproject/A2A) ([spec](https://a2a-protocol.org/latest/specification/))
- [Agent Payments Protocol (AP2)](https://github.com/google-agentic-commerce/ap2) — the extension precedent

---

*This document is part of the A2Agora specification. Licensed under Apache 2.0.*
