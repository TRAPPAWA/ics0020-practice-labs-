# Week 11 — Wireshark Network Investigation and Flow Correlation

**Primary tool:** Wireshark Desktop  
**Flow analysis:** SQLite inside the supplied Docker analyzer  
**Evidence:** CTU-13 Scenario 6 / CTU-Malware-Capture-Botnet-47

This lab investigates a public malware-traffic research dataset entirely offline. It uses three complementary forms of evidence from CTU-13 Scenario 6:

- original packet evidence in `donbot-scenario6.pcap`;
- a derived NetFlow v9 export capture in `donbot-scenario6-netflow-v9.pcap`;
- bidirectional flow evidence in `donbot-scenario6-flows-unlabeled.csv` and `donbot-scenario6-flows.binetflow`.

The workstation of interest is:

```text
147.32.84.165
```

The investigated host is provided so you can focus on its behavior, the strength of the available evidence, and the questions best answered by packet-level versus flow-level analysis.

Record your findings in `WORKSHEET.md`. For each important conclusion, include the display filter or SQL query and the corresponding result so that another analyst can reproduce it.

## Safety

Analyze the supplied evidence only.

Do not:

- replay the PCAP;
- contact any IP address or domain found in the evidence;
- export or execute payloads;
- disable endpoint protection to inspect anything extracted from the capture.

No malware executable is included in the lab package. The Docker analyzer has `network_mode: none`.

---

## Part A — How to query packet evidence

### 1. Wireshark display filters are the query language

Open:

```text
evidence/donbot-scenario6.pcap
```

in Wireshark Desktop.

A **display filter** hides packets that do not match. It does not modify the capture.

A few examples:

```text
ip.addr == 147.32.84.165
```

Shows packets where the investigated host is either source or destination.

```text
ip.src == 147.32.84.165
```

Shows packets sent by the host.

```text
tcp.dstport == 25
```

Shows TCP packets whose destination port is 25.

```text
tcp.flags.syn == 1 && tcp.flags.ack == 0
```

Shows initial TCP SYN packets. This is often useful when the question is about **connection attempts** rather than every packet in an established connection.

```text
ip.src == 147.32.84.165 && tcp.dstport == 25 && tcp.flags.syn == 1 && tcp.flags.ack == 0
```

Combines all three ideas.

```text
dns.qry.name contains "spamcop.net"
```

Searches decoded DNS query names.

```text
tcp contains "mstshash"
```

Searches TCP protocol data for the string `mstshash`.

```text
tcp.stream eq 0
```

Shows one TCP stream. The stream number is assigned by Wireshark and identifies one TCP conversation in the capture.

#### Build filters from packet fields

You do not have to type every field name from memory.

Select a packet, expand a protocol in the **Packet Details** pane, right-click a field such as `Source Address`, and use:

```text
Apply as Filter -> Selected
```

You can also right-click a field and choose **Apply as Column**. Useful fields to add as temporary columns include:

```text
tcp.stream
tcp.dstport
tcp.srcport
dns.qry.name
```

---

### 2. Wireshark analysis views

Use Wireshark's analysis views to summarize the capture before inspecting individual packets.

#### Capture properties

```text
Statistics -> Capture File Properties
```

Use this for packet count, capture duration, first/last packet and file information.

#### Protocol hierarchy

```text
Statistics -> Protocol Hierarchy
```

Use this view to compare transport protocols, decoded application protocols, and the proportions of ARP and IPv4 traffic.

#### Endpoints

```text
Statistics -> Endpoints
```

Use the IPv4 tab to identify addresses present in the capture.

#### Conversations

```text
Statistics -> Conversations
```

Use the IPv4 and TCP tabs to identify communicating endpoint pairs. Sorting by **Bytes**, **Packets**, or endpoint address can reveal different traffic patterns.

If you already have a display filter applied, enable **Limit to display filter** when you want the statistics window to describe only the filtered packets.

#### I/O Graphs

```text
Statistics -> I/O Graphs
```

Graphs are useful for activity over time. You can give different graph lines different display filters, for example one line for SMTP SYN packets and another for a repeated control connection.

#### Follow TCP Stream

Select a packet from an interesting TCP conversation, then use:

```text
Analyze -> Follow -> TCP Stream
```

or the equivalent right-click menu.

This reconstructs application bytes in sequence. Some streams are binary. Do not save or execute payloads from this capture.

#### Find text in packet data

```text
Edit -> Find Packet
```

You can search packet bytes for strings such as:

```text
RBL:
Max-Threads
mstshash
```

---

### 3. Time display matters

PCAP timestamps are stored as absolute timestamps, but Wireshark normally displays them using the analyst computer's local timezone. That means two students in different timezones can see different clock times for the same packet.

For comparisons inside the PCAP, one convenient choice is:

```text
View -> Time Display Format -> Seconds Since First Captured Packet
```

For measuring gaps after applying a filter, this is useful:

```text
View -> Time Display Format -> Seconds Since Previous Displayed Packet
```

The CTU flow text uses local CEST timestamps (`UTC+02:00`) for this scenario. The importer later normalizes those timestamps to UTC. Do not join evidence from two sources until you know what their timestamps mean.

---

### 4. Packet count is not connection count

A TCP connection can contain many packets. A failed SYN can also be retransmitted several times.

This capture additionally contains many near-identical outgoing packets recorded very close together. You may therefore see what looks like immediate duplication or retransmission.

To estimate connection attempts, use evidence such as:

- TCP Conversations;
- distinct `tcp.stream` values;
- distinct source-port/destination pairs;
- flow records.

The total TCP packet count is not a valid estimate of the number of connections.

---

## Part B — Packet investigation in Wireshark

### Task 1 — Establish the scope of the capture

Start by establishing the scope and integrity of the capture.

#### 1.1 Verify the evidence

From the lab directory:

```bash
./scripts/verify-evidence.sh
```

Record whether all four supplied evidence files pass their SHA-256 checks.

#### 1.2 Capture properties

Open **Statistics -> Capture File Properties**.

Record:

```text
packet count:
capture duration:
first packet:
last packet:
encapsulation / link type:
```

Questions:

1. What time range does the capture cover, and how long is the observation window?
2. Why does capture duration matter when assessing periodic behavior?
3. Why should an analyst record the evidence hash before starting analysis?

#### 1.3 Protocol hierarchy

Open **Statistics -> Protocol Hierarchy**.

Record the counts for:

```text
ARP:
IPv4:
TCP:
UDP:
ICMP:
```

Questions:

1. Which transport protocol dominates?
2. Which application protocols does Wireshark decode automatically?
3. Why can an application protocol remain shown only as `TCP`?
4. Why is "TCP" not an application-level conclusion?

#### 1.4 Endpoints and conversations

Open:

```text
Statistics -> Endpoints -> IPv4
Statistics -> Conversations -> IPv4
Statistics -> Conversations -> TCP
```

Sort by **Packets** and then by **Bytes**.

Record:

- the most prominent IPv4 endpoint;
- the top three IPv4 conversations by byte volume;
- at least two destination ports that appear frequently in TCP conversations.

Questions:

1. What does the prominence of `147.32.84.165` suggest about the capture's observation point?
2. Are the top-ranked conversations by packets and by bytes the same? Explain any difference.
3. What limits does this observation point impose on claims about traffic between other hosts?
4. What is one reason this capture cannot represent all traffic on the university network?

#### 1.5 Optional capture-quality challenge

Apply:

```text
ip.src == 147.32.84.165 && tcp
```

Look at several adjacent packets with the same sequence number, flags, endpoints and length.

Questions:

1. Do you see near-identical packets recorded only fractions of a second apart?
2. Why could this inflate naive packet counts?
3. Explain why duplicated packet records need not create separate flow records.

---

### Task 2 — Prove or reject SMTP scanning

TCP port 25 is commonly used for SMTP, but the port number alone does not establish scanning or message delivery. Examine the connection pattern before drawing a conclusion.

#### 2.1 Build the connection-attempt filter

Use:

```text
ip.src == 147.32.84.165 &&
tcp.dstport == 25 &&
tcp.flags.syn == 1 &&
tcp.flags.ack == 0
```

Look at the **Displayed** packet count in the Wireshark status bar.

Then open:

```text
Statistics -> Endpoints -> IPv4
```

with **Limit to display filter** enabled.

Record:

```text
initial SYN packets displayed:
number of different destination addresses visible:
```

Questions:

1. Is the host contacting one mail server or a large set of addresses?
2. Does the activity continue across much of the capture or occur only once?
3. What is the difference between a SYN packet and a successful SMTP transaction?

#### 2.2 Measure connection breadth with Conversations

Keep the same display filter and open:

```text
Statistics -> Conversations -> TCP
```

Enable **Limit to display filter**.

Questions:

1. Approximately how many TCP conversations/attempts are represented?
2. How does this count compare with the raw SYN packet count, and what explains any difference?
3. What role do SYN retransmissions or capture duplication play?
4. Which metric better represents "how many targets were probed": packet count, conversation count, or distinct destination count?

#### 2.3 Look for responses

Now construct the reverse-direction filter for SMTP responses:

```text
ip.dst == 147.32.84.165 && tcp.srcport == 25
```

Then narrow it to SYN-ACK packets:

```text
ip.dst == 147.32.84.165 &&
tcp.srcport == 25 &&
tcp.flags.syn == 1 &&
tcp.flags.ack == 1
```

Record what you find.

Questions:

1. Do the targeted SMTP servers visibly answer in this public PCAP?
2. What evidence, if any, shows that a TCP connection and SMTP session were established?
3. What evidence, if any, shows that an email message was transmitted?
4. Which conclusion is supported: "sent spam", "attempted SMTP connections", or "scanned SMTP targets"?

#### 2.4 Visualize the scan

Open **Statistics -> I/O Graphs**.

Create a graph line with this display filter:

```text
ip.src == 147.32.84.165 && tcp.dstport == 25 && tcp.flags.syn == 1 && tcp.flags.ack == 0
```

Use an interval that makes activity across the capture readable, for example 10 or 60 seconds.

Questions:

1. Is the activity concentrated in a short interval or sustained over time?
2. Does its rate remain constant?
3. Which periods appear most active?
4. What information about scan timing would the total count alone conceal?

#### 2.5 Write a defensible conclusion

In the worksheet, write one observation and one interpretation separately.

Example structure:

```text
Observation: ...
Interpretation: ...
Limitation: ...
```

Do not claim successful spam delivery unless you have application-layer evidence that proves it.

---

### Task 3 — Discover the main control/data conversation

Do not begin this task with a known command-and-control IP. Find the candidate from the capture.

#### 3.1 Find dominant conversations

Clear the display filter.

Open:

```text
Statistics -> Conversations -> TCP
```

Sort by **Bytes**.

Find a high-volume conversation involving `147.32.84.165` that is separate from the broad TCP/25 scan and traffic on TCP/3389.

Record:

```text
remote IP:
remote TCP port:
packets A -> B:
packets B -> A:
bytes A -> B:
bytes B -> A:
```

Questions:

1. Which direction carries most of the bytes?
2. Is this a one-way probe or bidirectional application traffic?
3. Why does sorting by bytes reveal something different from sorting by number of conversations?

#### 3.2 Follow the first stream

Select the earliest packets from that pair and use:

```text
Analyze -> Follow -> TCP Stream
```

Do not save the stream.

Record at least five readable strings or fields that appear in the conversation.

Look specifically for clues such as:

```text
HALLO
Hash:
ID:
RBL:
Max-Threads:
Session:
```

Questions:

1. Is the application content readable, or does it appear encrypted? Cite the visible evidence.
2. Which side sends the initial greeting?
3. What identifier does the workstation report?
4. What DNS blacklist domain is named in the configuration?
5. What thread-related value is supplied?
6. What does the remote side send back besides a small acknowledgement?
7. Which features suggest interactive human activity or automated software control?
8. How does decoded application content strengthen an inference based only on a port number?

#### 3.3 Measure repetition

Create a filter for **initial SYN packets** from the workstation to the remote IP/port you discovered.

Change:

```text
View -> Time Display Format -> Seconds Since Previous Displayed Packet
```

Look down the Time column.

Questions:

1. Do many connection starts have similar gaps?
2. What approximate intervals recur often?
3. Are there also outliers or very short gaps?
4. Why is a range or distribution of intervals more informative than one fixed interval?
5. Name two legitimate systems that can also produce periodic network traffic.

#### 3.4 Graph the control traffic

Open **Statistics -> I/O Graphs**.

Create one graph for the control pair and one graph for SMTP SYN packets.

Questions:

1. Does the control relationship persist while the SMTP scan runs?
2. Which activity is high fan-out and which is low fan-out/repetitive?
3. What hypothesis does their temporal overlap suggest?
4. What additional evidence would you need to claim causality rather than correlation?

---

### Task 4 — Correlate DNS, control traffic and SMTP behavior

Correlate DNS activity, control-channel data, and TCP/25 connection attempts to establish their timing and context.

#### 4.1 Inspect DNS queries

Apply:

```text
ip.src == 147.32.84.165 && dns.flags.response == 0
```

Add `dns.qry.name` as a column if useful.

Find repeated queries containing:

```text
spamcop.net
```

You can filter them directly with:

```text
dns.qry.name contains "spamcop.net"
```

Record the full query name.

Questions:

1. Which DNS server receives the queries?
2. What do the four numeric labels at the beginning of the query name represent?
3. Compare them with `147.32.84.165`. What transformation has been applied?
4. Why are IP addresses reversed in many DNS blacklist lookup names?
5. Do the repeated queries receive positive answers or NXDOMAIN responses? Inspect the DNS response code.

#### 4.2 Link the DNS query to the control stream

Return to the TCP stream from Task 3.

Find the `RBL:` configuration line.

Questions:

1. Does the domain named in the control stream match the domain queried by DNS?
2. What does this relationship suggest the software is checking?
3. Why does this support the SMTP-scan interpretation?
4. Why is a DNS blacklist lookup supporting evidence rather than conclusive proof of malware?

#### 4.3 Reconstruct the first seconds of the capture

Set time display to **Seconds Since First Captured Packet** and use filters to inspect the first 10 seconds.

Suggested filters to alternate between:

```text
tcp.port == 5678
```

```text
dns
```

```text
tcp.dstport == 25 && tcp.flags.syn == 1 && tcp.flags.ack == 0
```

Build a short timeline containing:

```text
control connection begins
DNS blacklist lookup
SMTP scanning begins
```

Questions:

1. In what order do these events occur?
2. Which event is direct control-channel evidence?
3. Which event is supporting/contextual evidence?
4. Which event is the actual large-scale behavior?
5. Why is the sequence stronger than any one event alone?

---

### Task 5 — Avoid attributing every packet to the malware

An infected machine still receives unrelated traffic and performs normal operating-system activity. This task is designed to catch over-attribution.

#### 5.1 Determine RDP connection direction

Start with:

```text
tcp.port == 3389 && ip.addr == 147.32.84.165
```

Then determine **who initiates** the connections by filtering initial SYN packets.

Do not assume the infected machine is the client.

Record:

```text
initiating IP:
server IP:
server port:
approximate number of connection attempts:
```

Questions:

1. Is `147.32.84.165` initiating or receiving the RDP connections?
2. How many different remote source IPs are involved?
3. Do you see SYN-ACK replies from the infected host?
4. What additional evidence would establish a successful RDP login beyond TCP connectivity?

#### 5.2 Inspect RDP negotiation data

Try:

```text
tcp contains "mstshash"
```

Select one result and inspect the packet bytes / decoded TPKT or RDP data.

Record the readable value associated with `mstshash`.

Questions:

1. What username-like string is visible?
2. What credential information, if any, is visible beyond the username-like string?
3. What evidence of successful authentication, if any, is visible?
4. Why can protocol metadata be useful even when authentication results are not visible?

#### 5.3 Find another inbound background pattern

Use Wireshark filters and/or the flow data later to find traffic **to** `147.32.84.165` on TCP/21.

Questions:

1. Which source sends it?
2. Does the infected host respond?
3. What additional evidence would be needed to attribute the inbound sender to the botnet?

#### 5.4 Inspect a normal-looking HTTP request

Apply:

```text
http.request && ip.src == 147.32.84.165
```

Inspect the request fields.

Record:

```text
HTTP host:
request URI:
User-Agent:
response status if visible:
```

Questions:

1. What operating-system component does the User-Agent suggest?
2. Which request fields, if any, suggest malicious behavior?
3. Why might a `From-Botnet` label describe the source host rather than the cause of every flow?
4. Why should an analyst distinguish "from an infected host" from "generated by malware"?

---

## Part C — Flow and NetFlow analysis

### Task 6 — Inspect NetFlow v9 and build the flow-analysis dataset

This task uses **two different flow representations**. They describe the same underlying CTU Scenario 6 activity, but they are not the same file format.

The CTU bidirectional flow source file is:

```text
evidence/donbot-scenario6-flows.binetflow
```

It is a **bidirectional Argus flow-text file**. Each row can contain counters for both directions of one conversation. It is not an `nfcapd` binary file and should not be opened with `nfdump`.

The lab also includes:

```text
evidence/donbot-scenario6-netflow-v9.pcap
```

The **NetFlow v9 export capture** was generated from the supplied CTU flow rows for this lab. It allows you to inspect the NetFlow v9 wire format in Wireshark; it was not recorded from a CTU router or exporter. Conversion splits each bidirectional CTU row into one or two unidirectional NetFlow records, depending on whether packets were observed in one or both directions.

For analysis before viewing labels, use:

```text
evidence/donbot-scenario6-flows-unlabeled.csv
```

Keep the CTU reference labels out of the analysis until Task 8.4.

#### 6.1 Inspect the NetFlow v9 export in Wireshark

Open:

```text
evidence/donbot-scenario6-netflow-v9.pcap
```

Wireshark should decode UDP/2055 as **Cisco NetFlow/IPFIX**. The protocol display-filter name is:

```text
cflow
```

Start with:

```text
cflow.version == 9
```

Open **Statistics -> Protocol Hierarchy** and confirm that the capture contains NetFlow export records transported over UDP, not the host-to-host application packets.

Select the first packet and expand the NetFlow section in the **Packet Details** pane.

Record:

```text
exporter IPv4 address:
collector IPv4 address:
UDP source port:
UDP destination port:
NetFlow version:
sequence number:
source / observation-domain ID:
record count in the export packet:
```

Questions:

1. Why are the exporter and collector addresses `192.0.2.x` rather than addresses from the CTU malware capture?
2. What does the NetFlow packet contain: original TCP payload, packet copies, or flow metadata?
3. Why can many flow records be carried inside one UDP export packet?
4. Why must you avoid treating the number of NetFlow **export packets** as the number of network flows?

#### 6.2 Find and understand the NetFlow template

NetFlow v9 is template based. The collector needs a description of each record before it can interpret the record bytes.

Filter for packets containing a template:

```text
cflow.template_id == 256
```

In the first such packet, expand:

```text
Cisco NetFlow/IPFIX
  -> Template FlowSet
     -> Template
```

Record:

```text
Template ID:
Field count:
```

Then list the fields in order. You should be able to identify fields for:

```text
source IPv4 address
destination IPv4 address
source transport port
destination transport port
IP protocol
IP ToS
packet counter
byte counter
flow start time
flow end time
```

Questions:

1. Why is the template not repeated before every individual data record?
2. Why are templates retransmitted periodically in this derived export capture?
3. What problem would a collector have if it received a Data FlowSet for Template ID 256 but had never received Template 256?
4. What is gained by a template-based protocol compared with a fixed record layout?
5. Which information from the packet capture is **not** represented by this template?

#### 6.3 Inspect NetFlow data records

Clear the template filter and use:

```text
cflow.srcaddr == 147.32.84.165 && cflow.dstport == 25
```

Select a matching export packet and expand its **Data FlowSet** records.

Record one SMTP-oriented NetFlow record:

```text
source IP:
source port:
destination IP:
destination port:
protocol:
packets:
bytes:
first switched:
last switched:
```

Now inspect the control/data relationship with:

```text
cflow.srcaddr == 147.32.84.165 &&
cflow.dstaddr == 91.212.135.158 &&
cflow.dstport == 5678
```

And the reverse direction with:

```text
cflow.srcaddr == 91.212.135.158 &&
cflow.dstaddr == 147.32.84.165 &&
cflow.srcport == 5678
```

Questions:

1. Why does the control relationship appear as separate forward and reverse NetFlow records while the CTU `.binetflow` row stores both directions together?
2. Which control-stream details, such as `HALLO`, `RBL:` and `Max-Threads: 60`, are unavailable in NetFlow records?
3. Which endpoint, port, timing, packet-count, and byte-count details remain available?
4. Why does the NetFlow export capture contain about 5,028 data records although the CTU bidirectional file contains 4,714 rows?
5. Inspect one matching UDP export packet. Which embedded records satisfy the filter, and why is the displayed packet count not a count of matching flow records?

#### 6.4 Compare the three evidence representations

Complete this table in the worksheet before moving on:

| Capability | Packet capture | NetFlow v9 export PCAP | CTU bidirectional flow file |
|---|---|---|---|
| Full packet/application payload |  |  |  |
| Source/destination addresses |  |  |  |
| Ports/protocol |  |  |  |
| Byte/packet counters |  |  |  |
| One row/record contains both directions |  |  |  |
| Requires a template to decode records |  |  |  |
| Efficient for large-scale aggregation |  |  |  |

Questions:

1. Which representation is best for discovering the plaintext command syntax?
2. Which is best for rapidly ranking thousands of conversations?
3. Which file most closely represents what a router would export to a NetFlow collector?
4. What analytical advantages does the CTU `.binetflow` file offer despite using a different format from NetFlow v9?

#### 6.5 Start the offline analyzer

The rest of the flow analysis uses the CTU bidirectional rows because they retain convenient source/destination counters in one record.

```bash
docker compose build
docker compose up -d
```

Check:

```bash
docker compose ps
```

The analyzer runs with `network_mode: none`; the exercise is offline.

#### 6.6 Import the unlabeled flow data

CTU Scenario 6 uses CEST (`UTC+02:00`) text timestamps. Normalize them during import:

```bash
docker compose exec analyzer \
  python3 /opt/lab/tools/import_flows.py \
  /evidence/donbot-scenario6-flows-unlabeled.csv \
  /work/flows.db \
  --utc-offset +02:00
```

Open SQLite:

```bash
docker compose exec analyzer sqlite3 /work/flows.db
```

Then:

```sql
.headers on
.mode column
.schema flows
SELECT COUNT(*) AS flow_records FROM flows;
SELECT * FROM flows LIMIT 3;
```

##### Example query 1 — protocol counts

```sql
SELECT proto, COUNT(*) AS flows
FROM flows
GROUP BY proto
ORDER BY flows DESC;
```

##### Example query 2 — traffic direction relative to the investigated host

```sql
SELECT
  CASE
    WHEN src_addr='147.32.84.165' THEN 'outbound'
    WHEN dst_addr='147.32.84.165' THEN 'inbound'
    ELSE 'other'
  END AS direction,
  COUNT(*) AS flows
FROM flows
GROUP BY direction;
```

##### Example query 3 — top outbound destination ports by flow count

```sql
SELECT dst_port,
       COUNT(*) AS flows,
       COUNT(DISTINCT dst_addr) AS distinct_destinations,
       SUM(bytes) AS total_bytes
FROM flows
WHERE src_addr='147.32.84.165'
  AND proto='tcp'
GROUP BY dst_port
ORDER BY flows DESC;
```

##### Example query 4 — top outbound destination ports by bytes

Modify only the final ordering:

```sql
ORDER BY total_bytes DESC;
```

Questions:

1. Which port ranks first by **flow count**?
2. Which port ranks first by **total bytes**?
3. Why are the answers different?
4. Which metric is more useful for scanning?
5. Which metric is more useful for bulk/control-channel data movement?
6. Compare the SQL ranking with what you saw in the NetFlow v9 records. Do both representations preserve the same broad behavior?

#### 6.7 Examine source and destination counters separately

The normalized table contains:

```text
src_packets
dst_packets
src_bytes
dst_bytes
packets
bytes
```

For one destination pair:

```sql
SELECT dst_addr, dst_port,
       COUNT(*) AS flows,
       SUM(src_packets) AS packets_out,
       SUM(dst_packets) AS packets_back,
       SUM(src_bytes) AS bytes_out,
       SUM(dst_bytes) AS bytes_back
FROM flows
WHERE src_addr='147.32.84.165'
GROUP BY dst_addr, dst_port
ORDER BY SUM(bytes) DESC
LIMIT 10;
```

Questions:

1. Among the returned pairs, which has the highest byte count from the remote side?
2. Which pair has many flows but effectively no reply packets?
3. How does that distinction help separate scanning from established bidirectional communication?
4. Which grouping keys would let you compare the forward and reverse directions of unidirectional NetFlow records?

---

### Task 7 — Reproduce the packet findings from flows

Now answer the major packet questions again without looking at the PCAP.

#### 7.1 SMTP fan-out

Write a query returning:

```text
flow count
number of distinct destinations
sum of source packets
sum of destination packets
sum of bytes
```

for outbound TCP/25.

Questions:

1. How many flow records are present?
2. How many distinct destination addresses?
3. Do those flows show return packets?
4. Which flow state dominates?
5. How does this support or weaken the Wireshark conclusion?

#### 7.2 C&C-like repeated pair

Find the outbound destination pair with the most bytes.

Then query it in detail:

```sql
SELECT state,
       COUNT(*) AS flows,
       SUM(src_bytes) AS bytes_out,
       SUM(dst_bytes) AS bytes_back
FROM flows
WHERE src_addr='147.32.84.165'
  AND dst_addr='<candidate-ip>'
  AND dst_port='<candidate-port>'
GROUP BY state;
```

Questions:

1. How many flows are present?
2. Which states occur?
3. Which direction carries most of the bytes?
4. Is that consistent with what Follow TCP Stream showed?
5. Which features distinguish repeated bidirectional communication from numerous unanswered TCP/25 attempts?

#### 7.3 Periodicity from flow timestamps

A starter query using `LAG()`:

```sql
WITH ordered AS (
  SELECT dst_addr,
         dst_port,
         start_epoch,
         LAG(start_epoch) OVER (
           PARTITION BY dst_addr, dst_port
           ORDER BY start_epoch
         ) AS previous_start
  FROM flows
  WHERE src_addr='147.32.84.165'
), gaps AS (
  SELECT dst_addr,
         dst_port,
         start_epoch - previous_start AS gap_seconds
  FROM ordered
  WHERE previous_start IS NOT NULL
)
SELECT dst_addr,
       dst_port,
       COUNT(*) AS gaps,
       ROUND(AVG(gap_seconds),2) AS avg_gap,
       ROUND(MIN(gap_seconds),2) AS min_gap,
       ROUND(MAX(gap_seconds),2) AS max_gap
FROM gaps
GROUP BY dst_addr, dst_port
HAVING COUNT(*) >= 8
ORDER BY gaps DESC;
```

Questions:

1. Which repeated pair stands out?
2. Why can minimum/maximum gap be misleading when some connections are retries or paired events?
3. Compare the SQL result with the Wireshark "Seconds Since Previous Displayed Packet" view.
4. Which source is easier for computing timing statistics: packets or flows?

#### 7.4 Inbound RDP attribution from flows

Write a query for TCP flows where:

```text
dst_addr = 147.32.84.165
dst_port = 3389
```

Record:

```text
remote source IP:
flow count:
bytes from remote source:
bytes from infected host back to remote source:
```

Run the corresponding query in the other direction and record whether it returns any rows:

```text
src_addr = 147.32.84.165
dst_port = 3389
```

Questions:

1. What direction is the RDP activity?
2. Does the flow evidence support a claim of outbound RDP scanning? Explain using the connection direction.
3. Which evidence source made the direction easiest to summarize?

#### 7.5 Explain PCAP/flow count differences

The PCAP and flow subset do not cover exactly the same start time, and a flow is not a packet.

Give at least four reasons why counts can differ between them. Consider:

- flow aggregation;
- retransmissions;
- duplicated packet capture records;
- bidirectional flow aggregation;
- flow timeout/reporting behavior;
- slightly different evidence time windows.

---

### Task 8 — Correlation and detection challenge

Develop behavioral detections without hardcoding the control-channel address or the SMTP port found in earlier tasks.

#### 8.1 Detect broad fan-out without an IOC

Write a query that returns source-address / destination-port combinations with:

```text
at least 100 distinct destination IPs
at least 100 flow records
```

Return at least:

```text
src_addr
dst_port
flow_count
distinct_destinations
dst_packets_total
bytes_total
```

Questions:

1. Which behavior is detected?
2. Why is `dst_packets_total` important?
3. How could a legitimate service trigger a similar rule?
4. What additional condition would reduce false positives?

#### 8.2 Detect repeated low-fan-out communication

Write a second query that groups flows by source IP, destination IP, and destination port, then finds pairs with:

```text
at least 20 flow records
substantial traffic in both directions
```

Compare the distinct-destination count for each source/destination-port combination with the broad-scan behavior from Task 8.1. Then add timing statistics using `LAG()`.

Do not hardcode the known candidate IP or port.

Questions:

1. Which pair rises to the top?
2. What combination of count, byte direction and timing makes it interesting?
3. Why would a simple "many destinations" scan rule miss this behavior?

#### 8.3 Cross-validate one SQL result in Wireshark

Choose one result from either behavioral query.

Construct a Wireshark display filter using the returned fields.

Record:

```text
SQL behavior detected:
SQL query:
SQL result:
Wireshark filter:
packet-level observation:
interpretation:
limitation:
```

#### 8.4 Validate against the CTU reference labels

Only now import the labeled flow file:

```bash
docker compose exec analyzer \
  python3 /opt/lab/tools/import_flows.py \
  /evidence/donbot-scenario6-flows.binetflow \
  /work/flows_labeled.db \
  --utc-offset +02:00
```

Inspect the label distribution:

```bash
docker compose exec analyzer \
  sqlite3 -header -column /work/flows_labeled.db \
  "SELECT label, COUNT(*) AS n FROM flows GROUP BY label ORDER BY n DESC;"
```

Then inspect the labels for:

- outbound TCP/25;
- the repeated control pair;
- inbound TCP/3389;
- the HTTP request from Task 5.

Questions:

1. Which labels agree with your analysis?
2. Which activity is labeled `Background` even though it involves the infected host?
3. What does a `From-Botnet` label establish, and what does it leave unproven about the traffic?
4. What do the flow labels establish about malware execution time, and what timing evidence is missing?
5. Why should labels be used for validation rather than replacing analysis?

---

### Task 9 — Final incident reconstruction

Use the evidence from the previous tasks to build a concise timeline and analyst conclusion.

Your timeline should include at least:

```text
control connection
DNS blacklist lookup
SMTP fan-out activity
repeated control connections
RDP background activity
normal-looking HTTP/OS activity
```

For each item record:

```text
time or time range
data source
filter/query
direct observation
interpretation
confidence
```

Then answer:

1. What behavior can you prove the workstation performed?
2. What evidence most strongly supports an automated spam-related bot workflow?
3. Which observation is the strongest evidence for C&C-like control traffic?
4. Which evidence is merely contextual/supporting?
5. Which traffic cannot be attributed to malware on the available evidence?
6. Which conclusions were easiest with Wireshark?
7. Which conclusions were easiest with the flow dataset?
8. What did flow records hide that packet data exposed?
9. What did flow aggregation make easier than packet inspection?
10. If this were a live corporate endpoint, what additional evidence would you request next?

A strong conclusion distinguishes facts from inference. For example:

```text
Observation: the host initiated TCP connection attempts to a large number of
remote addresses on destination port 25 and the supplied flow records contain
no reply packets for those flows.

Interpretation: the behavior is consistent with automated SMTP scanning.

Limitation: this evidence does not prove successful SMTP authentication or
message delivery.
```

---

## Additional question pool

Use these if you finish the core tasks early or if your lecturer assigns them.

### Wireshark / packet questions

1. Which remote address is second only to the infected host by packet count?
2. Which pair is largest by byte volume?
3. Which pair is largest by connection count?
4. How many DNS query packets are duplicates or near-duplicates?
5. Which DNS server is used by the workstation?
6. What DNS response, if any, resolves `crl.microsoft.com`, and to which address?
7. What HTTP response status is returned for the certificate-revocation-list request?
8. Which HTTP User-Agent appears?
9. Find one TCP reset. Which endpoint sent it?
10. Compare a long-lived flow with a short scan attempt in the packet list.
11. Use **Analyze -> Expert Information**. Which TCP warnings dominate?
12. How does the capture's duplicated outgoing traffic affect Expert Information?
13. Use a display filter to show only ARP. What local-neighbor activity is visible?
14. Use a display filter to show only ICMP. Is ICMP a major part of the incident?
15. Find the first packet after the control stream contains `Max-Threads: 60` that belongs to TCP/25 scanning.

### Flow questions

16. What percentage of all supplied flow records are outbound TCP/25 attempts?
17. Which destination IP receives the most TCP/25 flow records?
18. Which destination pair has the highest total byte count?
19. Which pair has the highest destination-to-source byte ratio?
20. How many C&C candidate flows end with `FIN` and how many with `RST`?
21. Which inbound source produces repeated TCP/21 attempts?
22. How many inbound RDP flows are recorded?
23. Which flow type contains the largest single `TotBytes` value?
24. Find the largest single flow and compare it with the typical repeated control flow.
25. Which protocols besides TCP appear in the flow file?
26. How many DNS flow records exist?
27. Compare `SrcPkts + DstPkts` with `TotPkts` for several records.
28. Find flows where `dst_packets = 0`. Which behavior dominates that set?
29. Find flows with `src_bytes < dst_bytes * 0.1`. Which communication pattern appears?
30. Which activity is high-count/low-byte and which is low-count/high-byte?

### Correlation questions

31. Which `From-Botnet` flows contain activity unrelated to the SMTP fan-out or repeated control relationship?
32. Why might those records still carry `From-Botnet` labels without proving that the traffic itself was malicious?
33. Which packet evidence links the RBL configuration to the DNS blacklist lookup?
34. Which packet evidence links the same period to SMTP fan-out?
35. Evaluate the claim that C&C activity caused the SMTP scan. What additional evidence would establish causality?
36. What would TLS encryption remove from this investigation, and which flow-level clues would remain?
37. If the packet payload had been truncated to 54 bytes, which conclusions would survive?
38. If only flow data were retained for 90 days, which questions in this lab would become impossible?
39. If only PCAP were retained, which large-scale summaries would become expensive to calculate?
40. Design one new behavioral rule that uses two independent features rather than one port number.

### NetFlow v9 wire-format questions

41. How many UDP NetFlow export packets are in the derived NetFlow-v9 PCAP?
42. How many of those packets refresh Template ID 256?
43. What is Template ID 256's field count, and why does field order matter?
44. What sequence-number range is visible, and what does the sequence number count in this artifact?
45. What Source/Observation Domain ID is used?
46. Why are there 5,028 derived unidirectional NetFlow records but only 4,714 CTU bidirectional rows?
47. Which RFC 3954 field types represent source/destination IPv4 addresses and source/destination transport ports?
48. Which field types carry packet and byte counters?
49. Explain the difference between the number of matching UDP export packets and the number of embedded SMTP flow records.
50. List five conclusions from the packet capture that the NetFlow v9 export cannot reproduce because the template contains metadata only.

---

## Appendix A — Wireshark filter quick reference

```text
# Host in either direction
ip.addr == 147.32.84.165

# Host as source / destination
ip.src == 147.32.84.165
ip.dst == 147.32.84.165

# Initial TCP connection attempts
tcp.flags.syn == 1 && tcp.flags.ack == 0

# SYN-ACK responses
tcp.flags.syn == 1 && tcp.flags.ack == 1

# SMTP target port
tcp.dstport == 25

# RDP in either direction
tcp.port == 3389

# DNS queries
dns.flags.response == 0

# DNS blacklist names
dns.qry.name contains "spamcop.net"

# HTTP requests
http.request

# Search TCP payload for a string
tcp contains "mstshash"

# One TCP stream
tcp.stream eq N

# Wireshark TCP analysis flags
tcp.analysis.retransmission
tcp.analysis.spurious_retransmission

# NetFlow/IPFIX export packets (use with the derived NetFlow-v9 PCAP)
cflow
cflow.version == 9
cflow.template_id == 256
cflow.srcaddr == 147.32.84.165 && cflow.dstport == 25
```

---

## Appendix B — Optional TShark verification

The practical is designed for Wireshark Desktop. TShark is included only for reproducible command-line checks.

Example:

```bash
docker compose exec analyzer \
  tshark -r /evidence/donbot-scenario6.pcap \
  -Y 'ip.src==147.32.84.165 && tcp.dstport==25 && tcp.flags.syn==1 && tcp.flags.ack==0' \
  -T fields -e frame.number -e frame.time_relative -e ip.dst -e tcp.stream
```

Do not replace the Wireshark investigation with blindly copying TShark commands. The point is to learn how to form and validate the same questions interactively.

---

## Cleanup

```bash
docker compose down
```

The evidence files are mounted read-only. SQLite databases and your query work remain under `work/`.
