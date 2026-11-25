# Evidence and field reference

The fictional organization operates a customer portal with four services: `catalog`, `orders`, `payments`, and `documents`. Its HTTP access logs, worker logs, and change audit logs have already been normalized upstream. This lab starts at the indexing and analysis stage; students do not need to implement a collector or a parser.

All times are UTC. The dates are fixed historical exercise dates; the dataset does not depend on your computer's clock.

| File | Purpose |
|---|---|
| `data/initial.ndjson` | One JSON document per line, 24 November 2026, 09:00 inclusive to 12:00 exclusive. |
| `data/validation.ndjson` | Second observation period, 12:00 inclusive to 13:00 exclusive. Load only in Task 7. |
| `data/mapping.json` | Explicit field types and index settings. |
| `data/manifest.json` | SHA-256 hashes and source file event counts. |

| Field | Type | Interpretation |
|---|---|---|
| `@timestamp` | date | Event time in UTC. |
| `event_id` | keyword | Unique event identifier, also used as the OpenSearch document `_id`. |
| `batch` | keyword | Initial or validation evidence partition. |
| `event_type` | keyword | `web` = one completed HTTP request; `worker` = application diagnostic; `audit` = change audit. |
| `service` | keyword | Service emitting the event. |
| `route` | keyword | HTTP request route, available on web events. |
| `traffic` | keyword | `customer` or `synthetic` for web events. Synthetic probes exercise the same endpoints but do not represent customer requests. |
| `tenant` | keyword | Synthetic customer organization identifier, present on customer web requests only. |
| `status_code` | integer | HTTP status, present on web events only. |
| `status_class` | keyword | `2xx`, `4xx`, or `5xx` for HTTP requests. |
| `latency_ms` | long | End-to-end response duration in milliseconds, on web events only. |
| `request_id` | keyword | Request identifier shared by a web event and its associated worker diagnostic, when one is available. |
| `message` | text | Analyzed natural-language message. |
| `message.raw` | keyword | Exact full message as a multifield; not a separate property in `_source`. |
| `level` | keyword | `INFO` or `ERROR`; this is an event severity, not necessarily an HTTP outcome. |
| `component` | keyword | Worker component, when present. |
| `action`, `change_id` | keyword | Change action and audit ticket reference, on audit events. |

A `web` event counts exactly one request. A `worker` record can describe the same request; adding both counts as requests double-counts activity. An audit record supplies context, not proof that the change caused an incident. A missing field is not zero. HTTP 4xx and 5xx are distinct status classes; this exercise defines a server-error rate using 5xx only. The records and ticket IDs are fictional, with deterministic values generated for this lab.

The main index is `lab-events-v1`. The index pattern `lab-events-*` selects it. A separate `lab-scratch` index is used for mapping experiments and is excluded from this pattern. No log source contains credentials or personal data.
