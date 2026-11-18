# Student Worksheet - Statistical Analysis and Reporting

Name: __________________________  Date: __________________

Use this file to record results, queries, observations and interpretations while following `STUDENT.md`.

---

# Task 1 - Evidence and context

Baseline start: __________________________

Baseline end: __________________________

Evaluation date: __________________________

Business hours: __________________________

Known schedules:

```text
1.
2.
3.
```

Pipeline limits:

```text
max ingestion lag:
max unparsed %:
max clock skew:
```

Answers:

1. One row in `auth` represents:

2. One row in `network` represents:

3. One row in `pipeline` represents:

4. Benefit of hourly aggregation:

5. Information lost by aggregation:

6. Why keep baseline/evaluation separate:

7. Context that can prevent a false positive:

---

# Task 2 - Top-N reports

## Authentication

| Rank | System | Failures | Successes |
|---:|---|---:|---:|
| 1 | | | |
| 2 | | | |
| 3 | | | |

## Network

| Rank | Host | Total outbound GiB | Peak hour GiB | Max unique destinations |
|---:|---|---:|---:|---:|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |

Questions:

1. Authentication system with most failures:

2. Host with most outbound data:

3. Host with widest destination breadth:

4. Why bytes and destinations differ:

5. Why time window belongs in the report:

6. Weakness of Top-N:

---

# Task 3 - Global baseline

```text
vpn-gw global baseline
mu:
sigma:
mu + 2*sigma:
p95:
p99:
03:00 evaluation value:
z-score:
```

Flagged by global two-sigma rule? __________________

Interpretation:

---

# Task 4 - Comparable windows

## Historical 03:00 baseline

```text
n:
mu:
sigma:
mu + 2*sigma:
p95:
evaluation value:
z-score:
```

| Measure | Global | 03:00 only |
|---|---:|---:|
| Mean | | |
| Sigma | | |
| Upper 2-sigma | | |
| Value | | |
| Z-score | | |
| Flagged? | | |

Why did the conclusion change?

Why is the 03:00 baseline better?

Trade-off of narrower windows:

## ssh-bastion Sunday 01:00

```text
n:
mean failures:
sigma:
p95:
```

Why is schedule context necessary?

---

# Task 5 - Network statistics

## app-01 03:00

```text
historical mean:
historical sigma:
upper 2-sigma:
p99:
observed value:
z-score:
unique destinations:
```

Additional evidence needed before calling this exfiltration:

## backup-01 02:00

All-days baseline:

```text
n:
mean:
sigma:
upper 2-sigma:
p95:
```

Sunday-only baseline:

```text
n:
mean:
sigma:
p95:
```

Why can the all-days baseline create a false positive?

Limitation of Sunday-only baseline:

Why rarity != risk:

---

# Task 6 - Pipeline health

| Time | Source | Finding | Evidence | Operational impact |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |

Questions:

1. Silent source:

2. Duration:

3. Excessive lag:

4. Excessive unparsed data:

5. Excessive clock skew:

6. Why silence is dangerous:

7. Effect of ingestion lag:

8. Effect of clock skew:

9. Why pipeline health is a separate report category:

10. Conditions that deserve immediate alerts:

---

# Task 7 - Charts

Generated files:

```text
reports/auth.svg
reports/network.svg
reports/pipeline.svg
```

Most useful visual finding:

Chart-design limitation observed:

---

# Task 8 - Operational report

Executive-summary points before writing:

```text
1.
2.
3.
4.
5.
```

| Finding | Immediate alert / daily / weekly | Reason |
|---|---|---|
| | | |
| | | |
| | | |
| | | |
| | | |
| | | |

Fastest response required:

Statistically unusual but explained finding:

Finding that could break other detections:

Daily metric:

Weekly metric:

Example of useless report:

What makes a report actionable:

---

# Task 9 - Challenge

Score formula:

```text

```

Top five hours:

| Rank | Timestamp | auth z | bytes z | destinations z | pipeline violations | score |
|---:|---|---:|---:|---:|---:|---:|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |

Why first-ranked hour is significant:

Why score is not a probability:

Weight/cap justification:

Zero-sigma handling:

Missing-data handling:

Potential evasion:

Additional context that would improve scoring:
