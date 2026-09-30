# Week 4 - Log Analysis with CLI Tools

## Learning Outcomes

By the end of this lab, you will be able to:

- Use `grep` / `grep -E` (`egrep`) to search for specific patterns in log files
- Utilize `awk` to extract and manipulate specific fields from log data
- Employ `sed` to perform basic text transformations on log entries
- Chain command-line tools together to perform more complex log analysis tasks
- Identify suspicious activity in web server logs
- Distinguish between a search that returns no evidence and a search that returns suspicious evidence
- Record commands and outputs as proof of completed analysis

## Objective

Practice essential Linux command-line tools (`grep`, `grep -E`, `awk`, `sed`, `cut`, `sort`, `uniq`) by parsing and analyzing existing web server log files.

## Scenario

You are a junior SOC analyst investigating web server activity. You have been provided with two web access logs:

- `access.log` - a real-world style Apache access log containing mostly normal web traffic.
- `attack_access.log` - a training dataset containing normal traffic mixed with scanning and web-attack indicators.

You will first learn and practise the basic log-analysis workflow on `access.log`. You will then use regular expressions and command-line filtering against **both files**.

> **Important:** A search returning zero results is not automatically a mistake. One dataset may contain no evidence of a particular attack while the other does. This is intentional. Your task is to search, compare, and report what the logs actually contain.

## Prerequisites

- School Ubuntu workstation
- Basic Linux command-line skills
- Basic regular-expression knowledge
- Text editor such as nano, vim, or VS Code

---

## Part 1: Understanding Apache Log Format

### Step 1: Apache Combined Log Format

Apache logs commonly use the Combined Log Format:

```text
LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined
```

**Example log entry:**

```text
192.168.1.100 - - [10/Jan/2024:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
```

**Field breakdown when using normal whitespace-separated `awk` fields:**

| Field | Position | Description | Example |
|---|---:|---|---|
| IP Address | `$1` | Client IP address | `192.168.1.100` |
| Identity | `$2` | RFC 1413 identity, usually `-` | `-` |
| Username | `$3` | HTTP auth username, usually `-` | `-` |
| Timestamp start | `$4` | Date/time beginning | `[10/Jan/2024:13:55:36` |
| Timezone | `$5` | Timezone and closing bracket | `+0000]` |
| Method | `$6` | HTTP method with opening quote | `"GET` |
| Path | `$7` | Requested URL/path | `/index.html` |
| Protocol | `$8` | HTTP protocol with closing quote | `HTTP/1.1"` |
| Status Code | `$9` | HTTP response code | `200` |
| Size | `$10` | Response size in bytes | `2326` |
| Referer | quoted field | Referring URL | `"-"` |
| User-Agent | quoted field | Browser/tool | `"Mozilla/5.0..."` |

> **Note:** Quoted fields such as the Referer and User-Agent may contain spaces, so their simple `awk` field numbers are not fixed in the same way as `$1`, `$7`, `$9`, and `$10`.

### Step 2: Download the Log Files

1. **Create a working directory:**

```bash
mkdir -p ~/logging-monitoring/week4
cd ~/logging-monitoring/week4
```

2. **Download the normal Apache log and save it as `access.log`:**

```bash
wget 'https://raw.githubusercontent.com/elastic/examples/master/Common%20Data%20Formats/apache_logs/apache_logs' -O access.log
```

3. **Download the attack-focused training log and save it as `attack_access.log`:**

```bash
wget 'https://raw.githubusercontent.com/SreejithReji/soc-sample-logs/main/web_access.log' -O attack_access.log
```

4. **Verify the files:**

```bash
ls -lh access.log attack_access.log
wc -l access.log attack_access.log
head -5 access.log
head -5 attack_access.log
```

The first file contains 10,000 records. The second contains 500 records.

---

## Part 2: Basic Log Analysis Commands

For this section, work with **`access.log` only**. Commands are provided because this section is intended to establish the basic analysis workflow you will reuse later.

### Exercise 1: Count Total Requests

**Question:** How many total requests are in the log file?

**Command:**

```bash
wc -l access.log
```

**Explanation:**

- `wc` = word count command
- `-l` = count lines
- Each line = one request

**Expected output:**

```text
10000 access.log
```

**Document this:** Record the total number of requests in your report.

---

### Exercise 2: Extract IP Addresses

**Question:** How many unique IP addresses made requests?

**Step-by-step approach:**

1. **Extract just the IP addresses (first field):**

```bash
awk '{print $1}' access.log | head -10
```

**Explanation:**

- `awk '{print $1}'` = print first field (IP address)
- `| head -10` = show first 10 results

2. **Sort the IP addresses:**

```bash
awk '{print $1}' access.log | sort | head -10
```

**Explanation:**

- `sort` = arrange the values in order
- This groups duplicate IPs together

3. **Remove duplicates:**

```bash
awk '{print $1}' access.log | sort | uniq | head -10
```

**Explanation:**

- `uniq` = remove adjacent duplicate lines
- It is normally used after `sort`

4. **Count unique IPs:**

```bash
awk '{print $1}' access.log | sort | uniq | wc -l
```

**Alternative (more efficient):**

```bash
awk '{print $1}' access.log | sort -u | wc -l
```

**Explanation:**

- `sort -u` = sort and remove duplicates in one step

**Document this:** Record the command you used and the number of unique IP addresses.

---

### Exercise 3: Find Top Talkers

**Question:** What are the top 10 most frequent IP addresses?

**Command:**

```bash
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -10
```

**Step-by-step breakdown:**

1. `awk '{print $1}'` - Extract IP addresses
2. `sort` - Sort them
3. `uniq -c` - Count occurrences of each unique IP
4. `sort -rn` - Sort by count, reverse numerical order
5. `head -10` - Show top 10

**Analysis:** IPs with high request counts can represent many things, including:

- Legitimate heavy users
- Search engines and web crawlers
- Web scrapers or automated tools
- Potential denial-of-service activity
- Compromised systems

A high request count alone does **not** prove malicious activity.

**Document this:** Record the command and the top 10 results.

---

### Exercise 4: Analyze HTTP Status Codes

**Question:** How many `404 Not Found` responses occurred?

**Command:**

```bash
grep " 404 " access.log | wc -l
```

**Explanation:**

- `grep " 404 "` = search for lines containing `404` surrounded by spaces
- `wc -l` = count matching lines

**Better approach using `awk`:**

```bash
awk '$9 == 404' access.log | wc -l
```

**Explanation:**

- `$9 == 404` = match lines where the ninth field (HTTP status code) equals `404`

**Analyze all status codes:**

```bash
awk '{print $9}' access.log | sort | uniq -c | sort -rn
```

**Document this:** Record the number of 404 responses and the complete status-code distribution.

---

### Exercise 5: Identify Frequently Requested Missing URLs

**Question:** What are the top 5 requested URLs that resulted in a `404` response?

**Command:**

```bash
awk '$9 == 404 {print $7}' access.log | sort | uniq -c | sort -rn | head -5
```

**Step-by-step:**

1. `$9 == 404` - Filter for 404 responses
2. `{print $7}` - Extract the requested path
3. `sort | uniq -c` - Group and count identical paths
4. `sort -rn` - Sort by frequency
5. `head -5` - Keep the top five

**Analysis:** Repeated 404 responses may be caused by ordinary broken links, old URLs, bots, vulnerability scanners, or reconnaissance. Do not label a path as malicious purely because it returned 404.

**Document this:** Record the command and top five paths.

---

## Part 3: Advanced Pattern Matching with grep / egrep

For this section, run your searches against **both `access.log` and `attack_access.log`** and compare the results.

Modern GNU `grep` uses `grep -E` for Extended Regular Expressions. The older `egrep` command is effectively equivalent, but `grep -E` is preferred on modern systems.

The exact regular expressions and command pipelines are **not provided** in this section. Use your regex knowledge and the basic command patterns from Part 2.

### Exercise 6: Detect Scanning Activity

**Question:** Are there requests made by the user agent `Nikto`? How many? Which source IP addresses used it?

**Background:** Nikto is a web vulnerability scanner. Its appearance in a User-Agent field indicates automated scanning, although the scan may be authorized or malicious depending on context.

**Search indicators:**

- The word `Nikto`
- The User-Agent field appears near the end of a combined access-log entry
- Searches should normally be case-insensitive when looking for tool names

**Tasks:**

1. Search `access.log` for Nikto activity and count matches.
2. Search `attack_access.log` for Nikto activity and count matches.
3. Extract the unique source IP addresses associated with Nikto requests.
4. Display several matching full log entries.

**Document this:** Record your commands and outputs for both files.

---

### Exercise 7: Detect SQL Injection Attempts

**Question:** Find potential SQL injection attempts in the logs.

**Common indicators to consider:**

- SQL keywords such as `UNION`, `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `DROP`, or `EXEC`
- Boolean conditions such as `' OR '1'='1`
- URL-encoded quote characters such as `%27`
- Scanner names associated with SQL injection testing, such as `sqlmap`

> These are **indicators**, not a ready-made regex. Construct an Extended Regular Expression that searches for several indicators at once.

**Tasks:**

1. Search both log files for possible SQL injection indicators.
2. Count matching records in each file.
3. Display several suspicious requests.
4. Extract the source IP addresses associated with the suspicious entries.
5. Determine which source IP appears most frequently in your matches.

**Document this:** Record the regex/command you constructed and its output.

---

### Exercise 8: Detect Cross-Site Scripting (XSS) Attempts

**Question:** Find potential XSS attempts.

**Indicators to consider:**

- HTML `<script>` tags
- `javascript:`
- Event handlers such as `onerror=` or `onload=`
- URL-encoded `<script>` sequences
- JavaScript calls such as `alert(...)`

**Tasks:**

1. Search both logs for possible XSS indicators using Extended Regular Expressions.
2. Count matches in each file.
3. Display several matching requests.
4. Extract the source IP addresses that generated the suspicious requests.

**Document this:** Record the commands and outputs.

---

### Exercise 9: Detect Directory Traversal

**Question:** Find potential directory traversal attempts.

**Indicators to consider:**

- Parent-directory traversal sequences such as two dots followed by `/`
- Repeated parent-directory traversal
- URL-encoded slash characters
- References to sensitive Unix files such as `/etc/passwd` or `/etc/shadow`

**Tasks:**

1. Search `access.log` for traversal-related indicators.
2. Search `attack_access.log` for the same indicators.
3. Count the results.
4. Display several matching requests and identify the source IP addresses.
5. Check the **field/context** in which a match occurs before deciding it represents an attack.

**Important:** Encoded characters can appear in legitimate referer URLs. A matching string is evidence to inspect, not automatic proof of exploitation.

**Document this:** Record the commands and outputs.

---

## Part 4: Advanced Analysis with awk

For this section, work primarily with `access.log`. Construct the commands yourself using the field information and basic pipelines from Part 2.

### Exercise 10: Analyze Traffic by Time

**Question:** What hours had the most traffic?

**Hints:**

- The beginning of the timestamp is field `$4`.
- The hour appears after the first `:` in that field.
- `cut` can split text using a delimiter.
- `sort`, `uniq -c`, and numerical reverse sorting can rank the result.

**Document this:** Record the command and resulting hourly distribution.

---

### Exercise 11: Analyze Request Methods

**Question:** What HTTP methods are being used and how often?

**Hints:**

- The method is stored in field `$6` and includes an opening double quote.
- `tr -d` can delete a character from a stream.
- Count and rank the methods.

**Security note:** Less common methods are not automatically malicious, but methods such as `PUT`, `DELETE`, or `TRACE` may deserve investigation depending on the application.

**Document this:** Record the command and method distribution.

---

### Exercise 12: Extract POST Requests

**Question:** Which IP addresses made POST requests?

**Tasks:**

1. Filter for records where the HTTP method is POST.
2. Extract the source IP addresses.
3. Produce a unique list.
4. Display several POST requests showing IP, path, and status code.

**Document this:** Record the commands and output.

---

### Exercise 13: Calculate Bandwidth Usage

**Question:** Approximately how much response data is represented in the log?

**Hints:**

- Response size is field `$10`.
- Some access logs may contain `-` where a byte count is unavailable.
- `awk` can maintain a running total and print a result in its `END` block.
- Divide bytes by `1024` twice to obtain MiB.

**Additional task:** Determine the top 10 source IP addresses by total response bytes.

**Document this:** Record the commands and output.

---

## Part 5: Text Transformation with sed
### Exercise 14: Extract and Format IPs

**Question:** Create a clean list of unique IP addresses, one per line, with no duplicates.

Save the result as:

```text
unique_ips.txt
```

Verify the number of lines and display the beginning of the file.

**Document this:** Record the commands and verification output.

---

### Exercise 15: Anonymize IP Addresses

**Question:** Use `sed` to replace the last octet of IPv4 addresses with `XXX` for privacy.

For example:

```text
192.168.1.25
```

should become something similar to:

```text
192.168.1.XXX
```

**Hints:**

- Match the dot before the final octet.
- Match one or more digits in the final octet.
- Preserve the first three octets.
- Test your transformation with only a few lines before applying it more broadly.

**Document this:** Record the command and several transformed lines.

---

### Exercise 16: Extract URLs Only

**Question:** Create a file containing only unique requested URLs/paths.

Save the result as:

```text
urls.txt
```

**Additional task:** Use an Extended Regular Expression to display only URLs ending in selected server-side file extensions such as `.php`, `.asp`, or `.jsp`.

**Document this:** Record the commands and output.

---

## Deliverables

Submit:

1. Your completed `Week-4-Log-Analysis-Report.md`
2. `unique_ips.txt`
3. `urls.txt`

Your report only needs to show evidence that each exercise was completed: category, exercise, command used, and output.
