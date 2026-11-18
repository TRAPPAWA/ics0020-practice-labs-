# Week 12 - Statistical Analysis and Reporting for Logging and Monitoring

**Prerequisite:** Docker / Docker Compose familiarity, basic SQL, basic command line

This lab focuses on statistical analysis of monitoring data and on turning measurements into reports that support decisions.

You will work with 28 days of baseline history and one evaluation day. The data covers:

- authentication activity;
- network activity;
- logging-pipeline health.

The practical work uses a single Docker container. The container has no network access while running. The datasets are read-only. Your queries, charts and report are stored in the mounted `work/` and `reports/` directories.

---

# Part A - Concepts used in the lab

## 1. From events to statistics

Individual log records are useful when you already know what to inspect. Statistical analysis answers broader questions:

- Which systems generate the most failures?
- Which host sent the most data?
- What does normal activity look like for 03:00?
- Is a current value unusual compared with its own history?
- Did a logging source become silent?
- Which findings belong in an immediate alert and which belong in a periodic report?

The basic workflow in this lab is:

```text
normalized telemetry
        |
        v
aggregate and summarize
        |
        v
build a baseline
        |
        v
compare new values
        |
        v
visualize and report
        |
        v
review and act
```

## 2. The three datasets

The files are under `data/`.

### `auth_hourly.csv`

One row represents one system for one hour.

```text
timestamp
period
system
successes
failures
unique_users
```

### `network_hourly.csv`

One row represents one host for one hour.

```text
timestamp
period
host
bytes_out
bytes_in
connections
unique_destinations
```

### `pipeline_hourly.csv`

One row represents one logging source for one hour.

```text
timestamp
period
source
events_received
ingestion_lag_s
unparsed_pct
clock_skew_s
```

### `context.json`

This contains operational context:

- baseline period;
- evaluation date;
- business hours;
- known maintenance and backup schedules;
- pipeline-health expectations.

Read it before deciding that an unusual value is an incident.

## 3. Baseline and evaluation periods

The dataset is divided into:

```text
baseline:   2026-10-01 through 2026-10-28
evaluation: 2026-10-29
```

The baseline is the historical reference. The evaluation day is the period you must assess.

Do not calculate a baseline using the evaluation value itself unless a task explicitly asks you to. Including the current anomaly in its own baseline can reduce its apparent significance.

## 4. Mean and standard deviation

For values `x1 ... xn`, the mean is:

```text
mu = sum(x) / n
```

The population standard deviation describes the spread around that mean:

```text
sigma = sqrt( sum((x - mu)^2) / n )
```

A simple normal range is often written as:

```text
mu +/- 2*sigma
```

For approximately normal data, many values should fall within that range.

Do not assume that every log-derived measure is normally distributed. Counts and transfer sizes are often skewed.

## 5. Z-score

The z-score expresses how far a value is from the mean in units of standard deviation:

```text
z = (value - mu) / sigma
```

Examples:

```text
z = 0      value is at the mean
z = 1      one standard deviation above the mean
z = 2      two standard deviations above the mean
z = -2     two standard deviations below the mean
```

A high z-score is evidence that a value is unusual relative to the chosen baseline. It is not proof of an attack.

## 6. Percentiles

The 95th percentile (`p95`) is a value at or below which approximately 95% of observations fall.

The 99th percentile (`p99`) is similar for 99%.

Percentiles are often useful for skewed monitoring data because they do not assume a symmetric distribution around a mean.

## 7. Windowing

A baseline must compare similar periods.

Examples:

```text
03:00 should often be compared with previous 03:00 values.
Sunday 02:00 may need to be compared with previous Sundays at 02:00.
Business hours may need a different baseline from night-time hours.
```

A single global average can hide these patterns.

## 8. Reporting

A report should reduce data into something that supports a decision.

Useful statistical report patterns include:

- Top-N;
- Bottom-N / rare values;
- baseline and threshold;
- count distinct;
- windowed comparison;
- trend over time;
- pipeline-health status.

Not every finding should become an alert. A high-volume weekly backup may belong in a report. A critical logging source going silent may require immediate action.

---

# Part B - Environment

## 9. Start the lab

From the lab directory:

```bash
docker compose up -d --build
```

Check the container:

```bash
docker compose ps
```

You should see one service:

```text
analyst
```

The container deliberately has no network access.

## 10. Verify the analysis tool

Run:

```bash
docker compose exec analyst \
  python3 /lab/tools/sql.py \
  "SELECT COUNT(*) AS auth_rows FROM auth;"
```

Expected:

```text
auth_rows
---------
2088
```

Check the other tables:

```bash
docker compose exec analyst \
  python3 /lab/tools/sql.py \
  "SELECT COUNT(*) AS network_rows FROM network;"
```

```bash
docker compose exec analyst \
  python3 /lab/tools/sql.py \
  "SELECT COUNT(*) AS pipeline_rows FROM pipeline;"
```

The helper loads the CSV files into an in-memory SQLite database each time it runs.

It also adds three aggregate functions that stock SQLite does not provide:

```text
STDDEV_POP(value)
MEDIAN(value)
PERCENTILE(value, p)
```

For example:

```bash
docker compose exec analyst \
  python3 /lab/tools/sql.py \
  "SELECT AVG(failures), STDDEV_POP(failures), PERCENTILE(failures,0.95) FROM auth;"
```

## 11. Running longer SQL

Use the supplied work file:

```text
work/student_queries.sql
```

Run it with:

```bash
docker compose exec analyst \
  python3 /lab/tools/sql.py \
  -f /work/student_queries.sql
```

Add your final queries to that file as you complete the tasks.

---

# Task 1 - Understand the evidence and reporting context

## 1.1 Read the operational context

Open:

```text
data/context.json
```

Record:

```text
Baseline start:
Baseline end:
Evaluation date:
Business hours:
Known scheduled jobs:
Maximum expected ingestion lag:
Maximum expected unparsed percentage:
Maximum expected clock skew:
```

## 1.2 Inspect the tables

Run:

```bash
docker compose exec analyst \
  python3 /lab/tools/sql.py \
  "SELECT * FROM auth LIMIT 5;"
```

Then inspect `network` and `pipeline` in the same way.

Questions:

1. What does one row in each table represent?
2. Why is it useful that the data is already hourly rather than one row per raw log event for this lab?
3. What information has been lost by using hourly summaries?
4. Why should the baseline period and evaluation period remain separate?
5. Give one example of operational context in `context.json` that could prevent a false positive.

---

# Task 2 - Top-N and frequency reports

The simplest report is often a ranking.

## 2.1 Authentication failures

Use this example:

```sql
SELECT system,
       SUM(failures) AS failed_logins
FROM auth
WHERE period='evaluation'
GROUP BY system
ORDER BY failed_logins DESC;
```

Run it directly:

```bash
docker compose exec analyst \
  python3 /lab/tools/sql.py \
  "SELECT system, SUM(failures) AS failed_logins FROM auth WHERE period='evaluation' GROUP BY system ORDER BY failed_logins DESC;"
```

Record the ranking.

Now modify the query to show both:

```text
failed logins
successful logins
```

## 2.2 Top outbound hosts

Write a query that ranks evaluation-day hosts by total outbound bytes.

Convert bytes to GiB:

```sql
bytes_out / 1073741824.0
```

Your output should contain:

```text
host
total_out_GiB
```

Then add:

```text
peak_hour_out_GiB
```

using `MAX(bytes_out)`.

## 2.3 Distinct destination breadth

Write a report showing, for each host on the evaluation day:

```text
maximum hourly unique_destinations
```

Rank largest first.

Questions:

1. Which authentication system has the most failed logins on the evaluation day?
2. Which network host sends the most total outbound data?
3. Is the host with the highest total outbound volume also the host with the widest destination breadth?
4. Why can total bytes and unique destinations represent different types of activity?
5. Why should a Top-N report usually include a time window in its title or query?
6. What is one weakness of using only Top-N reports for detection?

Add your final Task 2 queries to `work/student_queries.sql`.

---

# Task 3 - Build a global statistical baseline

You will first use a deliberately simple baseline for `vpn-gw` failed logins.

## 3.1 Calculate mean, standard deviation and percentiles

Use only baseline rows:

```sql
SELECT AVG(failures) AS mu,
       STDDEV_POP(failures) AS sigma,
       PERCENTILE(failures,0.95) AS p95,
       PERCENTILE(failures,0.99) AS p99
FROM auth
WHERE system='vpn-gw'
  AND period='baseline';
```

Record:

```text
mu:
sigma:
mu + 2*sigma:
p95:
p99:
```

## 3.2 Get the evaluation value

Query:

```text
vpn-gw
2026-10-29 03:00 UTC
failures
```

Then calculate its z-score in SQL:

```text
(value - mu) / sigma
```

A useful structure is:

```sql
WITH baseline AS (...),
stats AS (...),
evaluation AS (...)
SELECT ...
FROM stats, evaluation;
```

## 3.3 Interpret the result

Questions:

1. Is the 03:00 value above the global `mu + 2*sigma` threshold?
2. Is its z-score above 2?
3. Would a simple global two-sigma rule raise an alert?
4. How does the value compare with p95 and p99?
5. Does exceeding a percentile automatically mean malicious activity?
6. What assumption is hidden in treating one global baseline as appropriate for every hour of the day?

Do not change the data to make the result fit a rule. The purpose is to assess whether the rule is suitable.

---

# Task 4 - Build a comparable-window baseline

The lecture emphasizes that a value can be normal in one window and unusual in another.

## 4.1 Calculate a baseline by hour of day

SQLite can extract the hour from the timestamp:

```sql
CAST(strftime('%H', timestamp) AS INTEGER)
```

Use:

```sql
SELECT CAST(strftime('%H',timestamp) AS INTEGER) AS hour,
       AVG(failures) AS mean_failures,
       STDDEV_POP(failures) AS sigma
FROM auth
WHERE system='vpn-gw'
  AND period='baseline'
GROUP BY hour
ORDER BY hour;
```

Extend the query to calculate:

```text
upper_2sigma = mean_failures + 2*sigma
```

## 4.2 Compare only historical 03:00 values

Create a baseline using only:

```text
vpn-gw
baseline period
03:00 UTC
```

Calculate:

```text
n
mean
standard deviation
p95
mu + 2*sigma
```

Then compare the evaluation value from 03:00 on 2026-10-29.

Calculate its z-score again.

## 4.3 Compare the two methods

Fill in:

| Measure | Global baseline | Historical 03:00 baseline |
|---|---:|---:|
| Mean | | |
| Sigma | | |
| Upper 2-sigma | | |
| Evaluation value | | |
| Z-score | | |
| Flagged by 2-sigma? | | |

Questions:

1. Why does the conclusion change when the baseline is restricted to 03:00?
2. Which baseline better represents normal `vpn-gw` behaviour at 03:00?
3. What does this demonstrate about seasonality or time-of-day effects?
4. Would an even narrower window always be better? Explain the trade-off.

## 4.4 Maintenance window example

The context file states that `ssh-bastion` has approved maintenance on Sunday at 01:00 UTC.

Use:

```sql
strftime('%w',timestamp)
```

where SQLite uses:

```text
0 = Sunday
1 = Monday
...
6 = Saturday
```

Calculate the baseline for:

```text
ssh-bastion
Sunday
01:00 UTC
baseline period
```

Questions:

1. What is the mean failure count during this maintenance window?
2. Would it be sensible to compare those values with an ordinary Tuesday at 01:00?
3. Why must a detection system know about scheduled operational behaviour?

---

# Task 5 - Network statistics and skewed behaviour

## 5.1 Rank the evaluation-day hosts

Produce one table containing:

```text
host
total outbound GiB
maximum hourly outbound GiB
maximum hourly unique destinations
```

Rank by total outbound GiB.

Questions:

1. Which host is the largest outbound sender on the evaluation day?
2. At what hour does its largest transfer occur?
3. Which host has the largest unique-destination count?
4. Do the byte-volume and destination-breadth signals point to the same host?

## 5.2 Baseline `app-01` at 03:00

For `app-01`, compare the evaluation 03:00 `bytes_out` value with historical 03:00 values.

Calculate:

```text
mean
sigma
mu + 2*sigma
p99
evaluation value
z-score
```

Convert baseline values to MiB and the evaluation value to GiB if that makes the output easier to read.

Questions:

1. Is the evaluation value clearly outside the historical 03:00 range?
2. Is `mu + 2*sigma` sufficient to identify it?
3. Does the large number of unique destinations strengthen the case for investigation? Why?
4. What additional logs would you want before concluding that data exfiltration occurred?

## 5.3 A legitimate recurring backup

Now examine `backup-01` at 02:00.

First build a baseline using **all days at 02:00**.

Calculate:

```text
mean
sigma
mu + 2*sigma
p95
```

Then inspect the largest baseline values at that hour.

Use:

```sql
SELECT timestamp,
       ROUND(bytes_out/1073741824.0,3) AS out_GiB
FROM network
WHERE host='backup-01'
  AND period='baseline'
  AND CAST(strftime('%H',timestamp) AS INTEGER)=2
ORDER BY bytes_out DESC
LIMIT 8;
```

Then build a second baseline using only:

```text
Sunday 02:00
```

Questions:

1. Why is the all-days 02:00 distribution strongly skewed?
2. Can an approved Sunday backup exceed `mu + 2*sigma` calculated across all 02:00 values?
3. Does that make the backup malicious?
4. Which baseline is operationally more appropriate for this job?
5. What limitation do you see in the Sunday-only baseline sample size?
6. Why is statistical rarity not the same as security risk?

---

# Task 6 - Monitor the monitoring pipeline

A logging system can fail while the monitored systems continue operating.

The context file defines these expectations:

```text
sources should report every hour
ingestion lag <= 300 seconds
unparsed percentage <= 1%
clock skew <= 60 seconds
```

## 6.1 Find explicit health violations

Write one query for evaluation-day rows where any of these conditions is true:

```text
events_received = 0
ingestion_lag_s > 300
unparsed_pct > 1
clock_skew_s > 60
```

Your output should include:

```text
timestamp
source
events_received
ingestion_lag_s
unparsed_pct
clock_skew_s
```

Add a `CASE` expression that labels the primary finding, for example:

```sql
CASE
  WHEN events_received=0 THEN 'silent source'
  WHEN ingestion_lag_s>300 THEN 'ingestion lag'
  ...
END
```

## 6.2 Interpret the failures

Record every affected source and time.

Questions:

1. Which source becomes silent?
2. How long does the silence last?
3. Which source has excessive ingestion lag?
4. Which source has excessive unparsed data?
5. Which source has excessive clock skew?
6. Why is a silent firewall log source a security problem even if there are no error messages?
7. How could excessive ingestion lag affect an alert that depends on near-real-time data?
8. How could clock skew damage correlation between different log sources?
9. Why should pipeline-health findings be reported separately from the security events they carry?
10. Which of these conditions should probably be an immediate alert rather than only a weekly report?

---

# Task 7 - Visualize the statistics

The supplied chart helper creates SVG files. It has no external Python dependencies.

The basic workflow is:

```text
SQL query -> CSV -> plot_svg.py -> SVG
```

## 7.1 Create an authentication chart

Create:

```text
work/chart_auth.sql
```

The query should produce these columns for each hour:

```text
hour
eval_failures
baseline_mean
upper_2sigma
```

Use the baseline rows to calculate the mean and upper two-sigma value for each hour, then join them to the evaluation-day values.

Export CSV:

```bash
docker compose exec -T analyst \
  python3 /lab/tools/sql.py \
  --csv -f /work/chart_auth.sql \
  > work/chart_auth.csv
```

Create the chart:

```bash
docker compose exec analyst \
  python3 /lab/tools/plot_svg.py \
  /work/chart_auth.csv \
  /reports/auth.svg \
  --x hour \
  --y eval_failures,baseline_mean,upper_2sigma \
  --title "vpn-gw failures: evaluation vs baseline"
```

Open:

```text
reports/auth.svg
```

## 7.2 Create a network chart

Produce a similar chart for `app-01` outbound traffic.

Use MiB for the y-axis.

Suggested columns:

```text
hour
eval_out_MiB
baseline_mean_MiB
upper_2sigma_MiB
```

Save:

```text
reports/network.svg
```

## 7.3 Create a pipeline-health chart

Plot `fw-edge-01` evaluation-day `events_received` by hour.

Save:

```text
reports/pipeline.svg
```

Questions:

1. Which patterns are clearer in the charts than in a table of 24 rows?
2. Which chart is most useful for an operator who has only a few seconds to assess the day?
3. What information should not be removed merely to make a chart visually simpler?
4. Why should a chart title include the system, measure and time period?
5. What can go wrong if the y-axis scale is chosen poorly?

---

# Task 8 - Produce an operational report

Open:

```text
work/REPORT.md
```

Complete it using your findings.

Your report must contain:

1. a short executive summary;
2. authentication findings;
3. network findings;
4. logging-pipeline-health findings;
5. at least three charts;
6. a table deciding whether each major finding belongs in:
   - an immediate alert;
   - a daily report;
   - a weekly report;
7. concrete recommended actions;
8. methods and limitations.

## 8.1 Required findings

Your report must discuss at least:

```text
vpn-gw 03:00 comparison
app-01 03:00 network behaviour
backup-01 scheduled behaviour
fw-edge-01 silence
edr-collector lag
web-01-nginx parsing problem
dc-01-security clock skew
```

## 8.2 Reporting questions

Answer in the report or worksheet:

1. Which finding deserves the fastest response?
2. Which finding is statistically unusual but already explained by approved context?
3. Which finding could cause other detections to fail even if no attacker is present?
4. Which metric would you review daily?
5. Which metric would be reasonable in a weekly trend report?
6. Give one report that would be technically correct but operationally useless.
7. What makes a statistical report actionable rather than merely descriptive?

---

# Task 9 - Challenge: build a multi-signal anomaly ranking

A real monitoring system often combines several weak signals rather than relying on one threshold.

Build one SQL query that ranks all 24 evaluation-day hours using these inputs:

```text
vpn-gw failed-login z-score, using same-hour historical baseline
app-01 outbound-bytes z-score, using same-hour historical baseline
app-01 unique-destinations z-score, using same-hour historical baseline
number of pipeline-health violations during the hour
```

## 9.1 Requirements

Your query must:

1. calculate each baseline from `period='baseline'`;
2. group baselines by hour of day;
3. calculate z-scores for the evaluation day;
4. count pipeline violations for each evaluation hour;
5. join the signals by timestamp;
6. produce one final numeric score;
7. sort highest score first.

You may choose the score formula, but document it.

A simple starting idea is:

```text
positive auth z
+ positive outbound-byte z
+ positive unique-destination z
+ weighted pipeline violation count
```

You may cap individual z-scores so one extremely large measurement does not dominate the entire score.

## 9.2 Challenge questions

1. Which hour ranks first?
2. Which signals contribute to that hour?
3. Why should the score not be treated as a probability of compromise?
4. How did you choose weights or caps?
5. What would happen if a metric had zero historical standard deviation?
6. How would you handle missing data in a production implementation?
7. How could an attacker try to remain below this type of statistical detector?
8. What additional contextual data would improve the score?

---

# Robust statistics

Mean and standard deviation are sensitive to extreme values.

The SQL helper also provides:

```text
MEDIAN(value)
PERCENTILE(value,p)
```

Calculate the median absolute deviation (MAD) for one metric:

```text
MAD = median( abs(x - median(x)) )
```

Compare the result with mean and standard deviation for `backup-01` at 02:00.

Questions:

1. Is MAD less affected by the weekly large backups?
2. Would a robust statistic alone solve the false-positive problem?
3. Why is schedule-aware windowing still necessary?

---

# Final review questions

Be prepared to explain:

1. What is a statistical baseline?
2. What is the difference between a global baseline and a windowed baseline?
3. What does standard deviation measure?
4. What does a z-score mean?
5. Why are percentiles useful for skewed log or network data?
6. Why must a threshold include a time window?
7. Why can a statistically unusual event still be legitimate?
8. Why can a statistically ordinary value still be security-relevant?
9. Why is pipeline health part of monitoring?
10. What is the difference between an alert and a report?
11. Why should a report state its time period and data source?
12. What makes Top-N useful, and what can it miss?
13. Why should current observations usually be excluded from the historical baseline used to judge them?
14. Why is a 95% confidence interval for a mean not the same thing as a normal range for individual observations?
15. When should you prefer comparable time windows over one global threshold?

---

# Cleanup

Stop the container:

```bash
docker compose down
```

To reset your work files:

```bash
./scripts/reset-lab.sh
```
