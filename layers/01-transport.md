---
title: "Layer 1 — Transport & Invocation"
nav_order: 3
---

# Layer 1 — Transport & Invocation

| Field | Value |
|---|---|
| Layer | 1 |
| Status | `draft` |
| Working Group | transport |

## Scope

Defines how agents invoke compute tasks on other agents and receive results.
This layer is the foundation all other layers build on.

ACMP is specified as an extension to the **Model Context Protocol (MCP)**. All
ACMP messages are JSON-RPC 2.0 method calls and notifications transmitted over
standard MCP connections.

### Normative Language

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**
in this document are to be interpreted as described in [RFC
2119](https://www.rfc-editor.org/rfc/rfc2119).

### Relationship to Negotiation (Layer 6)

`acmp/invoke` is the execution step. It is normally preceded by negotiation
(Layer 6), in which buyer and provider agree on a price and terms. Two usage
modes are valid:

- **Negotiated:** The buyer first runs a Layer 6 exchange, then sends
  `acmp/invoke` carrying the resulting `escrow_id`. The agreed price is
  bounded by `max_price_cu`.
- **Direct (take-it-or-leave-it):** The buyer skips negotiation and sends
  `acmp/invoke` with a `max_price_cu`. The provider either executes at a price
  ≤ `max_price_cu` or rejects with `budget_exceeded` (-33001).

In both modes, `max_price_cu` is the buyer's ceiling and the provider's
reported `cost_cu` MUST NOT exceed it.

---

## 1. MCP Extension Model

ACMP defines custom JSON-RPC 2.0 methods under the `acmp/` namespace. An
ACMP-capable MCP server (the **provider**) advertises ACMP support in its
capability object during the standard MCP `initialize` handshake:

```json
{
  "capabilities": {
    "acmp": {
      "version": "0.1.0",
      "role": "provider",
      "accepts": ["acmp/invoke", "acmp/cancel", "acmp/inputChunk"],
      "emits": ["acmp/streamChunk", "acmp/heartbeat"],
      "features": {
        "output_streaming": true,
        "input_streaming": true,
        "heartbeat_interval_ms": 5000
      }
    }
  }
}
```

- `accepts` lists the inbound methods the provider handles (buyer → provider).
  A provider lists `acmp/inputChunk` only if `input_streaming` is `true`.
- `emits` lists the outbound notifications the provider may send (provider →
  buyer). A provider lists `acmp/streamChunk` only if `output_streaming` is
  `true`, and `acmp/heartbeat` only if it sets `heartbeat_interval_ms`.
- `features` advertises optional capabilities. A buyer MUST NOT rely on a
  feature the provider did not advertise. `heartbeat_interval_ms`, when
  present, is the nominal interval (in milliseconds) at which the provider
  emits heartbeats for running tasks; the buyer uses it to compute its
  liveness window (see §3.6).

If the `acmp` capability is absent, the server is a regular MCP server with no
ACMP support.

### Why MCP

- MCP is the emerging standard for agent-to-tool and agent-to-agent
  communication (AAIF governance).
- Hermes, OpenClaw, and other major agent frameworks already speak MCP.
- JSON-RPC 2.0 provides request/response correlation, error codes, and
  notification semantics out of the box.
- ACMP adds economic semantics (pricing, proofs, escrow) — it does not
  reinvent transport.

### Transport Requirements

Several ACMP messages are **provider-initiated notifications**
(`acmp/streamChunk`, `acmp/heartbeat`). These require a transport that
supports server-to-client messages. ACMP therefore requires a **bidirectional
transport**:

- **Supported:** HTTP+SSE, Streamable HTTP, stdio (all allow server→client
  messages).
- **Not supported:** plain request/response HTTP without a server-push
  channel.

A provider that can only use a non-bidirectional transport MUST advertise
`output_streaming: false` and MUST NOT emit notifications; buyers fall back to
a single `acmp/result`.

---

## 2. Message Types

ACMP defines seven message types. Each is either a JSON-RPC **request**
(expects a response) or a **notification** (fire-and-forget). Notifications
correlate to a task via the `task_id` field in their `params`, since
notifications have no JSON-RPC `id`.

| Method | Direction | JSON-RPC Type | Purpose |
|---|---|---|---|
| `acmp/invoke` | buyer → provider | request | Start a compute task |
| `acmp/result` | provider → buyer | response | Return the task result |
| `acmp/error` | provider → buyer | error response | Signal task failure |
| `acmp/inputChunk` | buyer → provider | notification | Stream partial input into a running task |
| `acmp/streamChunk` | provider → buyer | notification | Stream a partial result |
| `acmp/heartbeat` | provider → buyer | notification | Signal that a long-running task is still alive |
| `acmp/cancel` | buyer → provider | notification | Cancel a running task |

---

## 3. Message Schemas

### 3.1 `acmp/invoke`

Request from buyer to provider. Starts a compute task.

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/invoke",
  "id": "req_8f3a1b",
  "params": {
    "task_id": "task_a7c923f1",
    "capability": "sentiment-analysis",
    "input": {
      "type": "text",
      "data": "The product quality has declined significantly over the past quarter."
    },
    "output_type": "json",
    "input_tokens_est": 500,
    "max_price_cu": 0.005,
    "preferred_tier": "B",
    "timeout_ms": 5000,
    "stream": false,
    "input_stream": false,
    "escrow_id": "esc_a3f9c2",
    "proof_method": "result-hash"
  }
}
```

**Required fields:**

| Field | Type | Description |
|---|---|---|
| `task_id` | string | Unique identifier for this task. Generated by the buyer. MUST be globally unique; doubles as an idempotency key (see §3.1.1). |
| `capability` | string | The capability being requested (matches registry/ARD capability tags). |
| `input` | object | `{type, data}` — the input payload. `type` is a MIME-like classifier (`text`, `json`, `image/png`, ...). MAY be omitted when `input_stream` is `true`. |

**Optional fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `output_type` | string | `"json"` | Expected output format. |
| `input_tokens_est` | integer | — | Buyer's estimate of input token count. Informational, not binding. |
| `max_price_cu` | number | — | Maximum price in CU the buyer will pay. Provider MUST reject with -33001 if its minimum exceeds this. |
| `preferred_tier` | string | — | Preferred quality tier (`S`, `A`, `B`). Informational. |
| `timeout_ms` | integer | 30000 | Hard deadline (wall-clock). The buyer treats the task as failed if no `acmp/result` arrives within this window. See §3.5 for early death detection. |
| `stream` | boolean | `false` | If `true`, provider SHOULD send `acmp/streamChunk` notifications for the output. Provider MUST have advertised `output_streaming: true`. |
| `input_stream` | boolean | `false` | If `true`, the buyer will send the input incrementally via `acmp/inputChunk`. Provider MUST have advertised `input_streaming: true`. |
| `escrow_id` | string | — | Reference to a Layer 4 escrow lock. Absence means direct settlement. |
| `proof_method` | string | — | Requested proof type from Layer 3 (`result-hash`, `execution-trace`, ...). |

#### 3.1.1 Idempotency & Retries

`task_id` is buyer-generated and MUST be globally unique. It serves as an
**idempotency key**: if a provider receives a second `acmp/invoke` with a
`task_id` it has already seen, it MUST NOT execute the task again. Instead it
SHOULD return the existing result (if completed) or treat the duplicate as a
no-op (if still running). This makes `acmp/invoke` safe to retry after a
network failure without risk of double execution or double billing.

### 3.2 `acmp/result`

Successful response to an `acmp/invoke` request.

To be unambiguous about what a buyer receives: **`output` is the product being
purchased** — the actual result data. `proof` is evidence *about* it (Layer
3), never a substitute. The only case where a result legitimately carries no
`output` is a streamed task (§7.1), where the data has already arrived as
chunks.

```json
{
  "jsonrpc": "2.0",
  "id": "req_8f3a1b",
  "result": {
    "task_id": "task_a7c923f1",
    "output": {
      "type": "json",
      "data": {
        "sentiment": "negative",
        "confidence": 0.92
      }
    },
    "output_streamed": false,
    "tokens_used": 487,
    "cost_cu": 0.003,
    "proof": {
      "method": "result-hash",
      "hash": "sha256:e3b0c44298fc1c149afbf4c8996fb924..."
    },
    "provider_id": "agent:openclaw-3:us-east"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `task_id` | string | yes | Echoes the task_id from the invoke request. |
| `output` | object | conditional | `{type, data}` — the result payload. MAY be omitted if `output_streamed` is `true` and the complete output was already delivered via `acmp/streamChunk`. |
| `output_streamed` | boolean | no | If `true`, the output was delivered entirely through stream chunks; `output` is omitted to avoid duplicating large payloads. Default `false`. |
| `tokens_used` | integer | yes | Actual tokens consumed. |
| `cost_cu` | number | yes | Actual cost in CU. MUST be ≤ `max_price_cu` if the buyer provided it. |
| `proof` | object | no | Proof of execution per Layer 3. Present if `proof_method` was requested. |
| `provider_id` | string | no | Self-reported provider identity. |

### 3.3 `acmp/error`

Error response to an `acmp/invoke` request. Uses standard JSON-RPC 2.0 error
format with ACMP-specific codes.

```json
{
  "jsonrpc": "2.0",
  "id": "req_8f3a1b",
  "error": {
    "code": -33001,
    "message": "Budget exceeded",
    "data": {
      "task_id": "task_a7c923f1",
      "min_price_cu": 0.008,
      "detail": "Minimum price for sentiment-analysis at tier B is 0.008 CU."
    }
  }
}
```

**ACMP Error Codes:**

| Code | Name | Description |
|---|---|---|
| -33001 | `budget_exceeded` | Provider's minimum price exceeds `max_price_cu`. |
| -33002 | `capability_not_found` | Provider does not support the requested capability. |
| -33003 | `timeout` | Task exceeded `timeout_ms`, or liveness was lost (see §3.5). |
| -33004 | `cancelled` | Task was cancelled via `acmp/cancel`. |
| -33005 | `escrow_invalid` | Referenced escrow_id is invalid, expired, or insufficient. |
| -33006 | `proof_unsupported` | Provider cannot produce the requested proof_method. |
| -33007 | `feature_unsupported` | A requested feature (e.g. input/output streaming) was not advertised. |
| -33099 | `internal` | Unspecified provider-side error. |

Error codes are in the `-33xxx` range to avoid collision with standard
JSON-RPC codes (-32xxx) and leave room for application-specific codes.

### 3.4 `acmp/inputChunk`

JSON-RPC notification (buyer → provider). Used when the buyer set
`input_stream: true` in `acmp/invoke` to deliver the input incrementally. This
is the input-side counterpart to `acmp/streamChunk` and is what makes
streaming pipelines (Layer 2 §5) possible.

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/inputChunk",
  "params": {
    "task_id": "task_a7c923f1",
    "seq": 0,
    "chunk": {
      "type": "text",
      "data": "First part of the document..."
    },
    "final": false
  }
}
```

| Field | Type | Description |
|---|---|---|
| `task_id` | string | The task this input chunk belongs to. |
| `seq` | integer | Monotonically increasing sequence number, starting at 0. |
| `chunk` | object | `{type, data}` — partial input payload. |
| `final` | boolean | If `true`, this is the last input chunk; the provider has received the complete input. |

The provider MUST process chunks in `seq` order. It MUST NOT send
`acmp/result` before receiving a chunk with `final: true` (unless it fails or
is cancelled).

### 3.5 `acmp/streamChunk`

JSON-RPC notification (provider → buyer). Sent when the buyer set `stream:
true` in `acmp/invoke`.

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/streamChunk",
  "params": {
    "task_id": "task_a7c923f1",
    "seq": 3,
    "chunk": {
      "type": "json",
      "data": {"partial_sentiment": "negative"}
    },
    "final": false
  }
}
```

| Field | Type | Description |
|---|---|---|
| `task_id` | string | The task this chunk belongs to. |
| `seq` | integer | Monotonically increasing sequence number, starting at 0. |
| `chunk` | object | `{type, data}` — partial result payload. |
| `final` | boolean | If `true`, this is the last chunk. The provider MUST still send an `acmp/result` response after the final chunk (with `output_streamed: true` and `output` omitted, per §3.2). |

### 3.6 `acmp/heartbeat`

JSON-RPC notification (provider → buyer). Signals that a long-running task is
still being processed.

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/heartbeat",
  "params": {
    "task_id": "task_a7c923f1",
    "progress": 0.45,
    "detail": "Processing batch 9 of 20"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `task_id` | string | yes | The task this heartbeat belongs to. |
| `progress` | number | no | Estimated progress as a fraction between 0.0 and 1.0. |
| `detail` | string | no | Human-readable status message. |

**Timeout vs. liveness.** `timeout_ms` is always a hard wall-clock deadline:
if no `acmp/result` arrives within it, the buyer fails the task with -33003,
regardless of heartbeats. Heartbeats do **not** extend this deadline. Their
purpose is the opposite — to let a buyer **fail fast**: if a provider
advertised a `heartbeat_interval_ms` (see §1) and the buyer stops receiving
heartbeats for longer than its liveness window (recommended: 3×
`heartbeat_interval_ms`), the buyer MAY conclude the provider has died and
fail the task early with -33003, reclaiming escrow without waiting for the
full `timeout_ms`. For legitimately long tasks, the buyer sets a generous
`timeout_ms`; heartbeats give it confidence the task is progressing rather
than hung.

### 3.7 `acmp/cancel`

JSON-RPC notification sent by the buyer to cancel a running task.

```json
{
  "jsonrpc": "2.0",
  "method": "acmp/cancel",
  "params": {
    "task_id": "task_a7c923f1",
    "reason": "Upstream task failed, results no longer needed."
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `task_id` | string | yes | The task to cancel. |
| `reason` | string | no | Human-readable cancellation reason. |

Upon receiving `acmp/cancel`, the provider SHOULD stop work as soon as
practical and respond to the original `acmp/invoke` with an `acmp/error` using
code -33004 (cancelled). Partial work MAY still be billed — the exact policy
is defined by the negotiation terms (Layer 6).

---

## 4. Endpoint Addressing

ACMP endpoints are addressed as standard MCP server URIs. The transport
binding (stdio, SSE, Streamable HTTP) is determined by the MCP connection
setup.

For network-accessible agents, the canonical form is:

```
https://<host>/<path>
```

Example: `https://compute.example.com/acmp/v1`

Discovery of ACMP endpoints is handled by Layer 5 (ARD). An ARD resource
descriptor includes the MCP endpoint URI and the advertised `acmp` capability
object.

### Endpoint Identity

Each ACMP endpoint SHOULD have a stable `provider_id` in the format:

```
agent:<name>:<region>
```

Example: `agent:openclaw-3:us-east`

This identifier is self-reported (not cryptographically verified at Layer 1).
Layer 7 (Agent Wallet & Identity) defines stronger identity mechanisms.

---

## 5. Authentication

ACMP defines two authentication mechanisms. To guarantee interoperability,
every implementation **MUST support Bearer Token** as the baseline; **mTLS is
OPTIONAL** (MAY). This ensures any two ACMP agents share at least one common
mechanism.

### 5.1 Bearer Token (baseline, MUST)

The token is passed in the MCP connection setup (HTTP `Authorization` header
for HTTP transports, environment variable for stdio).

```
Authorization: Bearer acmp_tok_7f8a9b3c...
```

Token format and issuance are out of scope for this layer. Layer 7 (Agent
Wallet) may define token issuance tied to agent identity.

### 5.2 Mutual TLS (mTLS, MAY)

For zero-trust or untrusted networks where transport-level peer authentication
is required. Both client and server present X.509 certificates during the TLS
handshake. mTLS authenticates the *connection*; it complements rather than
replaces the Bearer token, which authorizes the *agent*.

mTLS is recommended when agents operate across organizational or network
boundaries that cannot be trusted beyond standard TLS.

---

## 6. Versioning

The `acmp.version` field in the capability advertisement follows semantic
versioning (`MAJOR.MINOR.PATCH`).

- **PATCH** changes are backward-compatible bug fixes to the spec text.
- **MINOR** changes add optional fields or new methods. Existing clients
  continue to work.
- **MAJOR** changes break backward compatibility. Method names may be prefixed
  (e.g. `acmp.v2/invoke`) to allow parallel operation during migration.

A buyer SHOULD check the provider's advertised `version` and the `features`
map before relying on any optional behaviour. The current version is `0.1.0`
(pre-release, breaking changes expected).

### Relationship to other latency fields

Layer 6 negotiation uses `max_latency_ms` (a quality-of-service SLA the
provider commits to — e.g. "p99 response under 800ms"). Layer 1 `timeout_ms`
is a different concept: the buyer's hard abort deadline for a specific
invocation. A buyer typically sets `timeout_ms` comfortably above the
negotiated `max_latency_ms` to absorb network jitter.

---

## 7. Streaming Protocol

### 7.1 Output streaming

When a buyer sets `stream: true` in `acmp/invoke` (and the provider advertised
`output_streaming: true`):

1. The provider sends zero or more `acmp/streamChunk` notifications with
   increasing `seq` numbers.
2. The last chunk has `final: true`.
3. After the final chunk, the provider sends the `acmp/result` response to
   close the JSON-RPC request, with `output_streamed: true` and `output`
   omitted (the buyer has already assembled the full output from the chunks).

If the provider did not advertise output streaming, it MAY ignore the `stream`
flag and return a single `acmp/result`, or reject with -33007.

### 7.2 Input streaming

When a buyer sets `input_stream: true` (and the provider advertised
`input_streaming: true`):

1. The buyer omits `input` in `acmp/invoke` (or sends a partial prefix).
2. The buyer sends `acmp/inputChunk` notifications with increasing `seq`
   numbers.
3. The final input chunk has `final: true`.
4. The provider may begin processing as chunks arrive and produces its result
   as usual.

Input and output streaming MAY be combined (a fully streaming pipeline stage).
This is the transport mechanism that Layer 2 §5 (streaming within DAGs) relies
on.

### 7.3 Cancellation during streaming

If the buyer sends `acmp/cancel` during streaming (input or output), the
provider SHOULD stop emitting chunks, ignore further input chunks, and respond
with error code -33004.

---

## Design Decisions

| Question | Decision | Rationale |
|---|---|---|
| MCP extension or standalone? | **MCP extension (baseline)** | MCP is the emerging standard. Hermes, OpenClaw already speak it. No reason to reinvent transport. Baseline, not exclusive — see the additive [A2A binding](01-transport-a2a-binding.md). |
| Authentication baseline? | **Bearer MUST, mTLS MAY** | A mandatory baseline guarantees any two agents share a common mechanism. mTLS adds connection-level auth for untrusted networks. |
| Error code range? | **-33xxx** | Avoids collision with JSON-RPC reserved range (-32xxx). |
| Batch invocation? | **No — use DAGs** | A DAG without edges is equivalent to a batch. One mechanism for both simple and complex cases (see Layer 2). |
| Long-running tasks? | **Hard `timeout_ms` + heartbeat for early death detection** | Heartbeats detect a hung provider *faster* than the deadline; they never extend it, so a stuck provider cannot hold a buyer hostage. |
| Streaming input into a task? | **Yes — `acmp/inputChunk`** | Symmetric to output streaming; required for streaming DAG pipelines (Layer 2 §5). Optional and capability-gated. |
| Retry safety? | **`task_id` as idempotency key** | Lets buyers safely retry after network failures without double execution or double billing. |

---

## Open Questions

- `[OPEN]` **Resumable interrupts (pause/resume).** Layer 1's seven message
  types assume *fire-and-execute*: a provider completes, streams, or fails,
  but never pauses mid-task to ask the buyer for something and resume. A2A
  models exactly this with its `input-required` / `auth-required` states
  ([A2A-MAPPING.md](../A2A-MAPPING.md#state-model-comparison) flags the gap).
  A candidate remedy is two new notifications — `acmp/interrupt` (provider →
  buyer, carrying a `reason` of `input_required` / `auth_required` and a
  machine-readable schema of exactly what is needed) and `acmp/resume` (buyer
  → provider, supplying it) — plus a non-terminal `paused` task state
  (coordinated with [Layer 2 §2](02-task-format.md#2-task-states)). The
  hardest part is economic, not syntactic: a paused task holds escrow while it
  waits, so an interrupt needs an expiry after which the task is `abandoned`
  and partially settled — a question owned by [Layer
  4](04-escrow-settlement.md#open-questions), not Layer 1. Left open pending a
  cross-layer design; no wire change is made here.

---

## Related

- [Layer 1 — A2A Binding (shallow)](01-transport-a2a-binding.md) — the
  additive A2A binding for these same messages
- [RFC-0001 §6](../RFC-0001-vision.md) — Protocol Stack Overview
- [Layer 2 — Task Decomposition Format](02-task-format.md) — Task schema used
  in `acmp/invoke`
- [Layer 5 — Discovery (ARD Binding)](05-discovery.md) — How endpoints are
  discovered
- [Layer 6 — Negotiation Protocol](06-negotiation-protocol.md) — How
  price/terms are agreed before `acmp/invoke`

---

*This document is part of the A2Agora specification. Licensed under Apache
2.0.*
