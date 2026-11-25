# Week 13 - Indexed log analysis and detection with OpenSearch

## Purpose

In previous practicals, you collected logs, examined packets and flow records, and calculated statistical baselines. This practical focuses on what happens after events reach a searchable log-management platform: defining field types, searching structured and unstructured content, building reproducible queries, visualizing operational impact, and validating a detection rule on new data.

You are the analyst for a fictional customer portal. An operations team has reported intermittent failures but has not established the affected service, time window or customer impact. You receive normalized HTTP, worker and change-audit events. Your job is to investigate the initial observation period and then test your conclusions against a second observation period.

### Learning outcomes

By the end of the lab, you should be able to explain how an index and a mapping affect search results; diagnose rejected documents; distinguish full-text searches from exact filters; create an index pattern and use Discover; write Query DSL searches and nested aggregations; build and validate a dashboard; and distinguish a detection rule from an operational conclusion.

Use `WORKSHEET.md` for answers. Include the actual query/filter, observed numerical output or screenshot, and explanation. Do not just copy a screenshot without describing what it proves. All timestamps in your answers must be UTC.

### Tools and safety

Docker Compose v2 (`docker compose`) and a browser are required. Docker Desktop users should allocate at least 4 GB RAM, preferably 6 GB. Allow approximately 8 GB free disk for image pulls and storage. No host Python, pip packages or cloud account are required. Use Linux containers on Windows. Commands are run from the extracted lab directory unless otherwise specified. Linux users who need elevated Docker access may prepend `sudo` to Docker commands.

OpenSearch 2.19.4 stores and searches documents. OpenSearch Dashboards 2.19.4 is the graphical interface. The third Compose service, `tools`, is an on-demand Python container for loading data and evaluating search results; it does not run as a daemon. This stack is local only, with security deliberately disabled and ports bound to `127.0.0.1`. Do not expose it or ingest real logs.

## 1. Start the platform and establish the evidence scope

### 1.1 Start and verify

From the directory containing `docker-compose.yml`:

```bash
docker compose config --quiet
docker compose pull search dashboards tools
docker compose up -d search dashboards
docker compose ps
docker compose run --rm tools tools/lab.py ready
```

The readiness check contacts the actual OpenSearch API, waits for at least yellow cluster health and verifies the version. A container marked `Up` is not necessarily ready to serve searches. The search service is expected to become ready before Dashboards finishes initializing.

If it fails, use `docker compose logs --tail=80 search` and `docker compose logs --tail=80 dashboards`. On Linux, OpenSearch may require `vm.max_map_count` of at least 262144. See the troubleshooting section at the end before changing system settings.

Verify and load the initial evidence:

```bash
docker compose run --rm tools tools/lab.py verify
docker compose run --rm tools tools/lab.py load-initial
```

Do not load the validation file yet. The loader verifies hashes, creates the main index with its explicit mapping if absent, and sends documents in batches using the Bulk API. It checks the result of each bulk item and refreshes the index so the events are searchable immediately. It uses `event_id` as `_id`, so retrying the same load replaces the same documents rather than adding duplicates.

Open http://127.0.0.1:15601 in your browser. If Dashboards says it is not ready yet, refresh after a short interval. Use the navigation menu (top left). If a welcome page asks about sample data, choose to explore your own data.

Find **Dev Tools** in the navigation menu (under Management in classic navigation). Dev Tools is an HTTP request console connected to OpenSearch, not a Unix shell. Enter one request at a time; put the cursor inside it and click its play/run button. In this guide, lines like `GET lab-events-v1/_count` are Dev Tools requests. Do not paste those lines into your shell.

Run:

```http
GET /
```

```http
GET _cluster/health
```

```http
GET _cat/indices/lab-events-*?v
```

```http
GET lab-events-v1/_count
```

```http
GET lab-events-v1/_mapping
```

An OpenSearch index is a logical collection of documents, divided into shards. A primary shard holds an index's data; a replica is another copy. The lab creates one primary and zero replicas so a single node can hold the entire index. This is not a high-availability production configuration.

**Q1.1.** What version is running, what is the cluster health status, and how many nodes are present? What does yellow mean in a single-node cluster?

**Q1.2.** What are the main index name, primary shard count, replica count and document count? Does that count match the initial data manifest?

**Q1.3.** Run `load-initial` a second time, then repeat `_count`. What happened and why? Explain the difference between the source JSON document's `event_id` and OpenSearch's `_id`.

**Q1.4.** Inspect the mapping. Give the mapped type of `@timestamp`, `status_code`, `latency_ms`, `service`, `message` and `message.raw`. Why is `latency_ms` numeric rather than a string?

## 2. Mapping, ingestion failures and searchability

### 2.1 Learn what a mapping controls

Read `DATA.md`. OpenSearch indexes fields according to their mapping. `keyword` fields preserve exact values and support grouping; `text` fields are analyzed into searchable terms. The `message` field has both representations. A mapping can also require a numeric type or prohibit unknown fields.

Use a scratch index so experiments do not alter the evidence. If you have already performed Task 2, delete **only** `lab-scratch` first (`DELETE lab-scratch`) and recreate it. A 404 when deleting an absent scratch index is harmless.

In Dev Tools:

```http
PUT lab-scratch
{
  "settings": {"number_of_shards": 1, "number_of_replicas": 0},
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "service": {"type": "keyword"},
      "latency_ms": {"type": "long", "coerce": false},
      "message": {"type": "text"}
    }
  }
}
```

```http
PUT lab-scratch/_doc/example-1?refresh=true
{
  "service": "example",
  "latency_ms": 120,
  "message": "Request completed"
}
```

Try the following intentional failure. Keep the response for your worksheet.

```http
PUT lab-scratch/_doc/example-2?refresh=true
{
  "service": "example",
  "latency_ms": "slow",
  "message": "Request completed"
}
```

### 2.2 Bulk request with partial failure

The Bulk API accepts newline-delimited JSON (NDJSON): action metadata followed by the corresponding document, with a final newline. The next request deliberately contains one valid and one invalid item. Paste it as a complete request into Dev Tools, including the final newline.

```http
POST lab-scratch/_bulk?refresh=true
{"index":{"_id":"example-3"}}
{"service":"example","latency_ms":240,"message":"Request completed"}
{"index":{"_id":"example-4"}}
{"service":"example","latency_ms":"240","message":"Request completed"}
```

Inspect the top-level `errors` and the status and error fields of each item. Query the scratch index using `_count` and `_search` to see what survived. Repair the invalid documents yourself using the original IDs and numeric values (use 350 for example-2 and 240 for example-4). Verify that all four are now present.

**Q2.1.** Why was example-2 rejected? What HTTP status and error type did OpenSearch return? Why is the document's value not searchable?

**Q2.2.** What was the overall HTTP status of the bulk request, and what were the individual item statuses? What does `errors: true` mean?

**Q2.3.** How many documents were searchable before and after your repairs? Provide your two repair requests. Why was `"240"` rejected even though it resembles a number?

**Q2.4.** Explain why a collector that checks only HTTP 200 could silently lose logs. Propose a handling strategy for malformed records and retries. Why are the main index and the scratch index separate?

## 3. Discover: use the graphical analysis interface

### 3.1 Create an index pattern and set time correctly

1. Open the navigation menu, select **Dashboards Management** (under Management), then **Index patterns**. Create an index pattern named `lab-events-*`.
2. Select `@timestamp` as the time field and complete creation. Do not choose a pattern matching `lab-scratch`.
3. In Dashboards Management > Advanced settings, search for the time zone setting (`dateFormat:tz`). Set it to `UTC` and save. This prevents your browser's local zone from shifting the exercise times.
4. Open **Discover**, choose the `lab-events-*` index pattern, and click the time picker in the upper right. Choose an absolute range from **24 November 2026 09:00:00** through **24 November 2026 11:59:59.999**, UTC. Apply/update the range. If the picker only supports seconds, use 11:59:59; all event timestamps are at whole seconds.
5. Clear the search bar and remove any active filter pills. Check the displayed hits against Task 1. The default last-15-minutes filter will show no data outside the exercise date.

In Discover, expand a row to see its fields and raw JSON. Add columns using the field sidebar (hover and click the add/plus control): `service`, `event_type`, `level`, `traffic`, `route`, `status_code`, `request_id`, `message`. Some rows have blanks because the fields do not apply to all event types. The histogram and hit count reflect the current time range and filters, while the table shows a limited page of matching records.

### 3.2 Learn search bar filters

Use the DQL (Dashboards Query Language) mode in the search bar. If the interface says Lucene, switch to DQL using the language selector. Field values shown here are case-sensitive for exact keyword matching. Use uppercase Boolean operators for clarity. After changing a query, press Enter or click Refresh/Update.

| Example DQL filter | Meaning |
|---|---|
| `event_type: web` | HTTP request events only. |
| `service: catalog AND event_type: web` | Requests logged by catalog. |
| `event_type: web AND traffic: customer` | Customer requests, excluding probes and non-web records. |
| `event_type: web AND status_class: "5xx"` | Server errors, including synthetic requests. |
| `event_type: audit` | Change records only. |
| `message: "upstream timeout"` | Full-text phrase search. |
| `request_id: "req-00-catalog-000"` | A specific request identifier. |

You can alternatively add filter pills using **Add filter**: select a field, choose `is`, and provide a value. DQL and filter pills are combined. Remove them when starting a different investigation. Do not interpret the first page of records as the complete result count.

**Q3.1.** Record the total matching events and the separate counts for `web`, `worker`, and `audit`. Verify that they sum to the total. Which event type is the correct unit for counting HTTP requests?

**Q3.2.** Use Discover to count all web events, then customer web events and synthetic web events. Provide the filters and counts. Explain why the two traffic categories must be distinguished.

**Q3.3.** Filter web 5xx events first without a traffic condition, then for customer events only. What are both counts? Why does `level: ERROR` across all event types answer a different question?

**Q3.4.** Find all change-audit events in the initial period. Record timestamps, services, actions and ticket IDs. Do not infer root cause from the changes alone.

**Q3.5.** Save a Discover search named `Customer server errors` containing only customer web 5xx events and relevant columns. Record the saved-search name and capture a screenshot that shows the query, time range and hit count. If the Save dialog offers to store the time filter, use it; otherwise record the absolute range separately.

## 4. Query DSL: exact fields, full text and numeric conditions

Discover is useful for exploration. A JSON Query DSL request is useful for reproducible analysis, automation, and inspection of the exact aggregation structure. Use Dev Tools for the following tasks. The time picker does **not** automatically constrain Dev Tools requests. Always include an explicit time range when analyzing a period.

A request to `_search` may return a small number of example hits; `hits.total.value` is the total when `track_total_hits` is true. `size: 0` suppresses example hits without suppressing the total or aggregations. `_source` in a hit contains the originally indexed JSON; `_id` is document metadata.

### 4.1 Search terms and phrases

Example: look for `completed` in the analyzed `message` field within the initial time range.

```http
GET lab-events-v1/_search
{
  "size": 3,
  "track_total_hits": true,
  "query": {
    "bool": {
      "filter": [
        {"range": {"@timestamp": {"gte": "2026-11-24T09:00:00Z", "lt": "2026-11-24T12:00:00Z"}}}
      ],
      "must": [{"match": {"message": "completed"}}]
    }
  }
}
```

`match` analyzes the query text. `match_phrase` requires adjacent analyzed terms in the given order. `term` matches an exact indexed term; use it for keyword fields and exact identifiers. For a multiword full message, use `message.raw` with a `term` query. `message.raw` is a multifield of `message`, so you will not find it as a separate property in `_source`.

The range is half-open: the lower endpoint is included (`gte`), the upper endpoint excluded (`lt`). Adjacent windows can therefore be combined without double-counting their boundary.

### 4.2 Structured filters and missing data

Example: catalog customer requests with duration at least 500 ms:

```http
GET lab-events-v1/_search
{
  "size": 5,
  "track_total_hits": true,
  "query": {"bool": {"filter": [
    {"range": {"@timestamp": {"gte": "2026-11-24T09:00:00Z", "lt": "2026-11-24T12:00:00Z"}}},
    {"term": {"event_type": "web"}},
    {"term": {"traffic": "customer"}},
    {"term": {"service": "catalog"}},
    {"range": {"latency_ms": {"gte": 500}}}
  ]}},
  "sort": [{"latency_ms": "desc"}, {"event_id": "asc"}]
}
```

All entries in `bool.filter` must match. `must_not` excludes matching documents. An `exists` query matches documents with an indexed field value. For example, `{ "exists": {"field": "latency_ms"} }` can be placed inside `must_not` to find events without latency. Do not treat missing latency as zero; it is not a measurement.

**Q4.1.** Adapt the first search to find `timeout` in `message` using `match`. Use `size: 0` and record the total. Then search for the exact full message `Upstream timeout` with `term` on `message.raw`. Compare the totals.

**Q4.2.** Use `match_phrase` to find `upstream timeout` in `message`. Compare that count with the exact full-message query and explain the difference. Give an example of a worker message included in the phrase search but excluded by exact matching.

**Q4.3.** Find customer web requests from all services with latency at least 800 ms. Record the total, then show the five slowest hits (sort descending). Give their event IDs, service, route, status and latency. Why would a text field be inappropriate for this operation?

**Q4.4.** Count events that do not have `latency_ms`. Which event types explain the result? Provide the query and explain why replacing these missing values with zero would distort an average.

## 5. Investigate customer impact using aggregations

The previous lab used statistical measures directly over a dataset. Here you will express those measures using OpenSearch's search and aggregation model, and pivot from aggregate results to individual evidence.

### 5.1 Group events and choose the correct denominator

An aggregation summarizes the documents selected by `query`. The `terms` aggregation creates one bucket per indexed value. `doc_count` is the number of documents in that bucket. A nested `filter` aggregation counts only matching documents inside the bucket. Use a sufficiently large `size` for this small dataset; `sum_other_doc_count` indicates documents in terms buckets omitted from the response.

Start with all web requests, including probes:

```http
GET lab-events-v1/_search
{
  "size": 0,
  "track_total_hits": true,
  "query": {"bool": {"filter": [
    {"range": {"@timestamp": {"gte": "2026-11-24T09:00:00Z", "lt": "2026-11-24T12:00:00Z"}}},
    {"term": {"event_type": "web"}}
  ]}},
  "aggs": {
    "by_service": {
      "terms": {"field": "service", "size": 20},
      "aggs": {"errors": {"filter": {"term": {"status_class": "5xx"}}}}
    }
  }
}
```

For each service calculate `100 × errors.doc_count / bucket.doc_count`. The numerator and denominator must refer to the same population. Modify the query to restrict that population to customer traffic. Do not move the 5xx filter into the top-level `query`: that would remove successful requests from the denominator. HTTP 4xx are retained in the denominator under the exercise's definition but are not server errors.

**Q5.1.** Fill a table for all four services with all-web requests, all-web 5xx, all-web error percentage, customer requests, customer 5xx and customer error percentage. Which service has the most customer failures? Which service has the highest customer failure percentage over the full initial period? Explain the difference between volume and rate.

**Q5.2.** Add a nested `terms` aggregation on `status_class` to the customer-only query. Verify the 2xx, 4xx and 5xx totals for each service. Explain why a count of only `level: ERROR` does not give the same HTTP failure rate.

### 5.2 Find the affected time window and route

A `date_histogram` groups documents by time. `fixed_interval: "15m"` forms consecutive 15-minute buckets. The bucket key represents its start, not the time when all the events occurred. `min_doc_count: 1` omits empty buckets; missing buckets do not establish health.

Example for the payments service (adapt it for your candidate):

```http
GET lab-events-v1/_search
{
  "size": 0,
  "query": {"bool": {"filter": [
    {"range": {"@timestamp": {"gte": "2026-11-24T09:00:00Z", "lt": "2026-11-24T12:00:00Z"}}},
    {"term": {"event_type": "web"}},
    {"term": {"traffic": "customer"}},
    {"term": {"service": "payments"}}
  ]}},
  "aggs": {
    "windows": {
      "date_histogram": {"field": "@timestamp", "fixed_interval": "15m", "time_zone": "UTC", "min_doc_count": 1},
      "aggs": {"errors": {"filter": {"term": {"status_class": "5xx"}}}}
    }
  }
}
```

You can group by route using a `terms` aggregation on `route`; place it above the histogram to get windows per route. To inspect affected tenants, apply the chosen service, route and time range, then filter to customer 5xx and group on `tenant`. The number of returned distinct tenant buckets is exact for this small complete result. A `cardinality` aggregation is often used for large distinct counts, but it estimates cardinality; use the small terms result here.

**Q5.3.** Determine which service and route have the most customer 5xx events. Produce its 15-minute timeline for the initial period. Identify the two highest error-rate windows and their request/error counts. Compare those windows with a normal window and a later recovery window.

**Q5.4.** In the first of those two high-rate windows, determine which tenants were affected and how many failed requests each had. Provide the aggregation and counts. Does the evidence suggest a problem isolated to one tenant?

**Q5.5.** Inspect customer failures for the `documents` service using the same histogram approach. Is there a window with a higher error percentage than your primary incident? Compare request volume and explain why a minimum-volume condition may matter.

### 5.3 Pivot to individual events and change context

Return to Discover. Use the candidate service, customer traffic, 5xx status and the affected window. Sort by timestamp ascending and select a failed request. Copy its `request_id`. Clear the traffic and event-type filters, then search for that ID alone (retain the time range). A related worker event may now appear. Expand both records; compare times, service and messages. Then search for audit events for the affected service. You may also use Dev Tools `term` filters on `request_id`, `service` and `event_type`, sorting on `@timestamp` ascending.

**Q5.6.** Provide one concrete failed customer request and its associated worker record: event IDs, shared request ID, timestamps, status code if present, and diagnostic message. What does the shared identifier prove, and what does it not prove?

**Q5.7.** Compare the customer failure windows with the service's change-audit records. Which change was closest to onset, and which action occurred near recovery? Explain whether this proves causation. State two additional sources you would request to verify the root cause.

## 6. Build an operational dashboard in OpenSearch Dashboards

The objective is not to reproduce the preceding numbers manually. You will save reusable visualizations and check that the graphical platform applies the same population and time scope as the underlying queries.

### 6.1 Create aggregation-based visualizations

In the navigation menu, open **Visualize** (sometimes labeled Visualize Library in newer navigation). Create an aggregation-based visualization; choose `lab-events-*` as the index pattern. The legacy aggregation editor in 2.19.4 uses metrics and buckets. If a visualization editor displays several different visualization types, choose the ordinary aggregation-based vertical bar, data table and line chart. Use the visualization's Apply/Update control after editing metrics/buckets.

Set the absolute initial time range again. Use the DQL filter `event_type: web AND traffic: customer` at the visualization or dashboard level, not a filter on 5xx for every chart. Save three visualizations with the following specifications:

| Name | Visualization | Metric | Buckets |
|---|---|---|---|
| Customer request outcomes | Vertical bar, stacked if available | Count | X-axis: Date Histogram, `@timestamp`, 15-minute interval (or nearest fixed setting); Split series: Terms, `status_class`, size 5. |
| Customer outcomes by service | Data table | Count | Split rows: Terms, `service`, size 10; second Split rows: Terms, `status_class`, size 5. |
| Customer latency over time | Line | Average of `latency_ms` | X-axis: Date Histogram, `@timestamp`, 15-minute interval; Split series: Terms, `service`, size 10. |

For a date histogram, choose a custom/fixed interval of `15m` if available. If your editor exposes only automatic interval or a minimum interval, use the closest option, note the effective interval, and use Task 5's Dev Tools query as the exact 15-minute reference. The latency chart uses mean duration; it is not a percentile or an error-rate chart.

Create a new dashboard using the Dashboard menu, give it the title `Customer portal operations`, and add the three saved visualizations and the saved search from Task 3. Use Add panels / Add from library / Add existing (the label depends on the navigation layout). Set the initial absolute time range. Apply `event_type: web AND traffic: customer` at dashboard level if you did not already save that population in each visualization; do not use a global 5xx filter. The saved search should retain its own 5xx filter. Save the dashboard and verify after reopening it. If the saved search's filter was not retained, edit or re-save it before adding it again.

Use the filter bar to isolate one service temporarily, then clear that filter. The dashboard should update all applicable panels. If a panel does not update, check whether the panel has a saved query, custom time range or another conflicting filter. Avoid adding an unnecessary permanent filter on the time range inside a saved visualization; we will change the dashboard range in Task 7.

**Q6.1.** Provide a screenshot of the complete dashboard showing its time range, population filter and panel titles. Explain which panel gives the denominator, which exposes outcome changes, and which measures response duration.

**Q6.2.** Use the table to verify the customer outcome counts for one service against Task 5. Are they consistent? If not, diagnose the time range, filters, or grouping.

**Q6.3.** Filter the dashboard to the main affected service. Describe the visible outcome and latency changes during the incident, then remove the filter. Why would selecting only error events globally invalidate the request-volume comparison?

**Q6.4.** Which information from this dashboard belongs in a periodic report, and which requires timely alerting? Propose one improvement to the dashboard that would make the percentage and low-volume issue clearer.

## 7. Detection rule development and validation

A dashboard is a review tool; a detection rule is an explicit decision applied to a defined population and window. This task tests a rule using fixed historical evidence. It does not send notifications or create a scheduled Alerting-plugin monitor. In production the same query and condition could run on a schedule, with an alert lifecycle and deduplication.

### 7.1 Implement a targeted rule

Operations requests the following candidate rule:

- evaluate 15-minute UTC windows;
- consider only customer web requests;
- initially restrict to the service and route you identified in Task 5;
- alert when at least 20 requests were observed and at least 10% were 5xx (both boundaries inclusive);
- report a lower-volume returned bucket as `INSUFFICIENT`, not `OK`.

Open `work/rule.json` in your host text editor. It contains a JSON search body with three `TODO` values. Replace them with the population and service/route values you found. The time range is fixed to the initial period. Read the aggregation structure carefully: `by_service` → `by_route` → `windows` → `errors`. Do not rename these keys because the supplied evaluator reads them. The top-level query filters the population; the histogram splits each service/route into windows; the nested error filter supplies the numerator.

To test the query manually, paste the JSON body into Dev Tools after the line `GET lab-events-v1/_search`. To evaluate all returned buckets with the supplied tool, run:

```bash
docker compose run --rm tools tools/rule_check.py work/rule.json --min-requests 20 --min-percent 10 --all
```

The tool sends the JSON to the real OpenSearch API and prints the window, service, route, request count, error count, percentage and state. The tool does not invent missing windows, label a zero-return search healthy or perform a second independent search. It raises an error for a truncated aggregation or an incomplete search. Use `--all` to include non-alerts; without it, only alerts and the summary are printed.

**Q7.1.** Supply your completed targeted query, its results, and the exact alert windows. Verify the numerator and denominator of each against Task 5.

**Q7.2.** Change only the minimum percentage to 30 by using the command-line option. How does the result change? Why is increasing a threshold without evaluating missed incidents a poor tuning strategy?

### 7.2 Load the validation period

Now, and only now, ingest the second batch:

```bash
docker compose run --rm tools tools/lab.py load-validation
```

In Dev Tools run `GET lab-events-v1/_count` again. The original time range should still show the same events, while the full index now includes the validation batch. In Discover and your dashboard, switch the absolute range to **24 November 2026 12:00:00 through 12:59:59.999 UTC**. Keep the customer population filter. Look for operational changes. Save a screenshot with the new range.

Copy `work/rule.json` to `work/rule-validation.json` (using your editor's Save As or a file manager). Change the `gte` to `2026-11-24T12:00:00Z` and `lt` to `2026-11-24T13:00:00Z`. Keep all other filters and aggregation keys unchanged. Run:

```bash
docker compose run --rm tools tools/rule_check.py work/rule-validation.json --min-requests 20 --min-percent 10 --all
```

**Q7.3.** Record the initial, validation and total index document counts. What evidence in the updated dashboard differs from the initial period? What does the targeted rule report in validation? Is it sufficient to conclude that the entire portal is healthy?

### 7.3 Challenge: generalize and test the rule

A rule targeting a previously affected endpoint can miss a new incident. Copy the targeted JSON into `work/rule-general.json`, remove the two exact service and route conditions from the `bool.filter` array, and keep the customer-web filters. Ensure the JSON is valid (no trailing commas). The existing nested `terms` buckets evaluate each service and route independently. Save this initial-period query as `work/rule-general.json`. Make a second copy named `work/rule-general-validation.json` and change only its time range to 12:00 inclusive through 13:00 exclusive. Run both queries:

```bash
docker compose run --rm tools tools/rule_check.py work/rule-general.json --all
```

```bash
docker compose run --rm tools tools/rule_check.py work/rule-general-validation.json --all
```

Create a third copy of the generalized validation query, `work/rule-untuned-validation.json`. Remove only the `traffic: customer` term filter. Evaluate it with the same thresholds. Finally compare a version of the customer-only rule using `--min-requests 1` to the 20-request rule. This tests the effects of population selection and denominator size separately.

```bash
docker compose run --rm tools tools/rule_check.py work/rule-untuned-validation.json --all
docker compose run --rm tools tools/rule_check.py work/rule-general.json --min-requests 1 --all
docker compose run --rm tools tools/rule_check.py work/rule-general-validation.json --min-requests 1 --all
```

**Q7.4.** Give the generalized query for both periods. List every alert as service, route, window, requests, errors and rate. Did the generalized rule discover an event missed by the targeted rule? Do not hardcode the new service in your query.

**Q7.5.** What additional alert does the untuned validation query generate when probes are included? Give the counts and the reason it does not establish customer impact. Which underlying log evidence supports your explanation?

**Q7.6.** Which low-volume windows become alerts when the minimum request count is one? Explain why suppressing them reduces noise but may hide important failures. Propose how to handle such services separately.

**Q7.7.** Investigate the newly identified customer issue in validation using Discover, the dashboard and at least one aggregation. Report the time window, request count, failed count, affected tenants, and any change context. Separate confirmed observations from hypotheses. Explain why testing a rule on another time period is necessary but not enough to estimate production false-positive and false-negative rates.

## Troubleshooting and cleanup

- `docker compose config --quiet` fails: ensure the archive is extracted, the file is unmodified and Docker Compose v2 is available. Run `docker compose version`.
- Cannot pull an image: check Internet access and Docker registry connectivity. The pinned search and dashboard versions support x86-64 and ARM64; do not force amd64 emulation on Apple Silicon. Pull images before class if the network is slow.
- Search exits: `docker compose logs --tail=100 search`. For memory problems, allocate more RAM to Docker. If logs explicitly mention `vm.max_map_count`, Linux users may temporarily run `sudo sysctl -w vm.max_map_count=262144` on their Linux host/VM and restart the service. On Docker Desktop the kernel belongs to Docker's Linux VM; changing the macOS/Windows host sysctl will not fix it. Follow the Docker Desktop-specific OpenSearch documentation in SOURCES.md or ask the lecturer; do not change unrelated host settings. Do not run with privileged mode.
- Dashboard not ready: check the search readiness command first, then `docker compose logs --tail=80 dashboards`. Both images must use the matching version and security settings supplied.
- Port already in use: stop your conflicting local lab or change only the host-side port mappings in the Compose file (the internal `9200` and `5601` remain unchanged). If you change the dashboard host port, update your browser URL. The tools service communicates internally with `search:9200`.
- Discover returns no results: verify `_count` in Dev Tools, index pattern, absolute UTC date range, and DQL/filter pills. The default relative time picker does not include fixed historical events.
- Dev Tools works but rule tool returns no windows: confirm the JSON contains the correct `gte`/`lt`, no `TODO`, correct filters and the loaded batch. No returned windows is not evidence of health.
- Bulk response HTTP 200 with `errors: true`: inspect per-item errors, not just the status line. The supplied loader exits with a failure if any item is rejected.
- `terms` buckets omit results: check `sum_other_doc_count` and increase `size` for a complete small-data answer.

When finished, stop the containers:

```bash
docker compose down
```

Your evidence files, worksheet and query files remain in the lab directory, and the named volume retains OpenSearch data. Use `docker compose down -v` only when you deliberately want to discard the lab's stored index and dashboards.
