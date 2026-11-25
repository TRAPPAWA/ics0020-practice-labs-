# OpenSearch log analysis

Name:
Date:
Docker / OpenSearch versions:

Record the actual query/filter and observed result. Attach screenshots or short excerpts where appropriate. All times UTC.


## 1. Start the platform and establish the evidence scope

**Q1.1.** What version is running, what is the cluster health status, and how many nodes are present? What does yellow mean in a single-node cluster?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q1.2.** What are the main index name, primary shard count, replica count and document count? Does that count match the initial data manifest?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q1.3.** Run `load-initial` a second time, then repeat `_count`. What happened and why? Explain the difference between the source JSON document's `event_id` and OpenSearch's `_id`.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q1.4.** Inspect the mapping. Give the mapped type of `@timestamp`, `status_code`, `latency_ms`, `service`, `message` and `message.raw`. Why is `latency_ms` numeric rather than a string?

Query/filter or steps:

Result/evidence:

Explanation:

---

## 2. Mapping, ingestion failures and searchability

**Q2.1.** Why was example-2 rejected? What HTTP status and error type did OpenSearch return? Why is the document's value not searchable?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q2.2.** What was the overall HTTP status of the bulk request, and what were the individual item statuses? What does `errors: true` mean?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q2.3.** How many documents were searchable before and after your repairs? Provide your two repair requests. Why was `"240"` rejected even though it resembles a number?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q2.4.** Explain why a collector that checks only HTTP 200 could silently lose logs. Propose a handling strategy for malformed records and retries. Why are the main index and the scratch index separate?

Query/filter or steps:

Result/evidence:

Explanation:

---

## 3. Discover: use the graphical analysis interface

**Q3.1.** Record the total matching events and the separate counts for `web`, `worker`, and `audit`. Verify that they sum to the total. Which event type is the correct unit for counting HTTP requests?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q3.2.** Use Discover to count all web events, then customer web events and synthetic web events. Provide the filters and counts. Explain why the two traffic categories must be distinguished.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q3.3.** Filter web 5xx events first without a traffic condition, then for customer events only. What are both counts? Why does `level: ERROR` across all event types answer a different question?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q3.4.** Find all change-audit events in the initial period. Record timestamps, services, actions and ticket IDs. Do not infer root cause from the changes alone.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q3.5.** Save a Discover search named `Customer server errors` containing only customer web 5xx events and relevant columns. Record the saved-search name and capture a screenshot that shows the query, time range and hit count. If the Save dialog offers to store the time filter, use it; otherwise record the absolute range separately.

Query/filter or steps:

Result/evidence:

Explanation:

---

## 4. Query DSL: exact fields, full text and numeric conditions

**Q4.1.** Adapt the first search to find `timeout` in `message` using `match`. Use `size: 0` and record the total. Then search for the exact full message `Upstream timeout` with `term` on `message.raw`. Compare the totals.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q4.2.** Use `match_phrase` to find `upstream timeout` in `message`. Compare that count with the exact full-message query and explain the difference. Give an example of a worker message included in the phrase search but excluded by exact matching.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q4.3.** Find customer web requests from all services with latency at least 800 ms. Record the total, then show the five slowest hits (sort descending). Give their event IDs, service, route, status and latency. Why would a text field be inappropriate for this operation?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q4.4.** Count events that do not have `latency_ms`. Which event types explain the result? Provide the query and explain why replacing these missing values with zero would distort an average.

Query/filter or steps:

Result/evidence:

Explanation:

---

## 5. Investigate customer impact using aggregations

**Q5.1.** Fill a table for all four services with all-web requests, all-web 5xx, all-web error percentage, customer requests, customer 5xx and customer error percentage. Which service has the most customer failures? Which service has the highest customer failure percentage over the full initial period? Explain the difference between volume and rate.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q5.2.** Add a nested `terms` aggregation on `status_class` to the customer-only query. Verify the 2xx, 4xx and 5xx totals for each service. Explain why a count of only `level: ERROR` does not give the same HTTP failure rate.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q5.3.** Determine which service and route have the most customer 5xx events. Produce its 15-minute timeline for the initial period. Identify the two highest error-rate windows and their request/error counts. Compare those windows with a normal window and a later recovery window.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q5.4.** In the first of those two high-rate windows, determine which tenants were affected and how many failed requests each had. Provide the aggregation and counts. Does the evidence suggest a problem isolated to one tenant?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q5.5.** Inspect customer failures for the `documents` service using the same histogram approach. Is there a window with a higher error percentage than your primary incident? Compare request volume and explain why a minimum-volume condition may matter.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q5.6.** Provide one concrete failed customer request and its associated worker record: event IDs, shared request ID, timestamps, status code if present, and diagnostic message. What does the shared identifier prove, and what does it not prove?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q5.7.** Compare the customer failure windows with the service's change-audit records. Which change was closest to onset, and which action occurred near recovery? Explain whether this proves causation. State two additional sources you would request to verify the root cause.

Query/filter or steps:

Result/evidence:

Explanation:

---

## 6. Build an operational dashboard in OpenSearch Dashboards

**Q6.1.** Provide a screenshot of the complete dashboard showing its time range, population filter and panel titles. Explain which panel gives the denominator, which exposes outcome changes, and which measures response duration.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q6.2.** Use the table to verify the customer outcome counts for one service against Task 5. Are they consistent? If not, diagnose the time range, filters, or grouping.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q6.3.** Filter the dashboard to the main affected service. Describe the visible outcome and latency changes during the incident, then remove the filter. Why would selecting only error events globally invalidate the request-volume comparison?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q6.4.** Which information from this dashboard belongs in a periodic report, and which requires timely alerting? Propose one improvement to the dashboard that would make the percentage and low-volume issue clearer.

Query/filter or steps:

Result/evidence:

Explanation:

---

## 7. Detection rule development and validation

**Q7.1.** Supply your completed targeted query, its results, and the exact alert windows. Verify the numerator and denominator of each against Task 5.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q7.2.** Change only the minimum percentage to 30 by using the command-line option. How does the result change? Why is increasing a threshold without evaluating missed incidents a poor tuning strategy?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q7.3.** Record the initial, validation and total index document counts. What evidence in the updated dashboard differs from the initial period? What does the targeted rule report in validation? Is it sufficient to conclude that the entire portal is healthy?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q7.4.** Give the generalized query for both periods. List every alert as service, route, window, requests, errors and rate. Did the generalized rule discover an event missed by the targeted rule? Do not hardcode the new service in your query.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q7.5.** What additional alert does the untuned validation query generate when probes are included? Give the counts and the reason it does not establish customer impact. Which underlying log evidence supports your explanation?

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q7.6.** Which low-volume windows become alerts when the minimum request count is one? Explain why suppressing them reduces noise but may hide important failures. Propose how to handle such services separately.

Query/filter or steps:

Result/evidence:

Explanation:

---

**Q7.7.** Investigate the newly identified customer issue in validation using Discover, the dashboard and at least one aggregation. Report the time window, request count, failed count, affected tenants, and any change context. Separate confirmed observations from hypotheses. Explain why testing a rule on another time period is necessary but not enough to estimate production false-positive and false-negative rates.

Query/filter or steps:

Result/evidence:

Explanation:
