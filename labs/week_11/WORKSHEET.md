# Student Worksheet — Wireshark Network Investigation and Flow Correlation

Use this file to record answers while you work through `STUDENT.md`.

For important conclusions, always record both:

```text
Evidence: the filter/query/result you actually used
Interpretation: what you think the evidence means
```

Do not write only the final conclusion.

---

# Task 1 — Capture scope

## Evidence verification

| File | Hash check | Notes |
|---|---|---|
| `donbot-scenario6.pcap` |  |  |
| `donbot-scenario6-flows-unlabeled.csv` |  |  |
| `donbot-scenario6-flows.binetflow` |  |  |

Why hash evidence?

> 

## Capture properties

| Property | Value |
|---|---|
| Packet count |  |
| Capture duration |  |
| First packet |  |
| Last packet |  |
| Link type / encapsulation |  |

Why does duration matter for periodicity analysis?

> 

## Protocol hierarchy

| Protocol | Count / observation |
|---|---:|
| ARP |  |
| IPv4 |  |
| TCP |  |
| UDP |  |
| ICMP |  |

Dominant transport protocol:

> 

Decoded application protocols you noticed:

> 

Why can some traffic remain displayed only as TCP?

> 

## Endpoints and conversations

Most prominent IPv4 endpoint:

> 

Top three IPv4/TCP conversations by bytes:

| Rank | Endpoint A | Endpoint B | Ports if relevant | Packets | Bytes |
|---:|---|---|---|---:|---:|
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |
| 3 |  |  |  |  |  |

What does the observation point let you see, and what does it not let you see?

> 

### Optional duplicate-capture observation

Evidence/filter used:

> 

What duplication/retransmission artifact did you notice?

> 

Why is packet count not the same thing as connection count?

> 

---

# Task 2 — SMTP scanning

Display filter used for initial SMTP SYN packets:

```text

```

| Measurement | Result |
|---|---:|
| Displayed SYN packets |  |
| Approx. TCP conversations / attempts |  |
| Distinct destination IPs |  |
| SMTP SYN-ACK replies |  |

Does the activity occur throughout the capture or in one short burst?

> 

What did the I/O Graph show?

> 

Why are raw SYN count, conversation count and distinct-target count different?

> 

Can you prove any SMTP session was established?

> 

Can you prove a message was delivered?

> 

Observation:

> 

Interpretation:

> 

Limitation:

> 

---

# Task 3 — Main control/data conversation

How did you locate the candidate? Record the Wireshark view/filter:

> 

| Property | Result |
|---|---|
| Remote IP |  |
| Remote port |  |
| Packets host -> remote |  |
| Packets remote -> host |  |
| Bytes host -> remote |  |
| Bytes remote -> host |  |

Which direction carries more data?

> 

## Follow TCP Stream observations

Record at least five readable strings/fields:

1. 
2. 
3. 
4. 
5. 

Greeting / command visible:

> 

Reported ID:

> 

RBL domain:

> 

Thread-related setting:

> 

Is the protocol encrypted? What evidence supports your answer?

> 

What does the remote side send back?

> 

Why is this stronger evidence than the TCP port number alone?

> 

## Periodicity

Filter used for connection starts:

```text

```

Recurring gap values you observed:

> 

Outliers / retries you observed:

> 

Why is "approximately periodic" more accurate than "exactly every N seconds"?

> 

What did the I/O Graph show when compared with the SMTP scan?

> 

---

# Task 4 — DNS/control/SMTP correlation

Full repeated SpamCop DNS name:

> 

DNS server:

> 

How does the left side of the DNS name relate to `147.32.84.165`?

> 

DNS response result / response code:

> 

Control-stream field that refers to the same DNS blacklist:

> 

## First-seconds timeline

| Relative / absolute time | Event | Wireshark filter/evidence |
|---|---|---|
|  | Control connection begins |  |
|  | DNS blacklist lookup |  |
|  | SMTP scanning begins |  |

What is the strongest direct evidence of software control?

> 

What is contextual/supporting evidence?

> 

What is the large-scale behavior?

> 

Why does the sequence strengthen the overall interpretation?

> 

---

# Task 5 — Attribution traps

## RDP

Filter used to find initial RDP SYN packets:

```text

```

| Property | Result |
|---|---|
| Initiating IP |  |
| Server IP |  |
| Server port |  |
| Approx. connection count |  |
| Number of remote source IPs |  |

Does the infected host initiate or receive RDP?

> 

Do you see SYN-ACK responses from the infected host?

> 

Visible `mstshash` value:

> 

What does that value prove?

> 

What does it *not* prove?

> 

## TCP/21 background traffic

Source IP:

> 

Direction:

> 

Does the infected host respond?

> 

Why should this not automatically be attributed to the malware?

> 

## HTTP / OS-looking activity

| Field | Value |
|---|---|
| HTTP host |  |
| URI |  |
| User-Agent |  |
| Response status |  |

Does this look obviously malicious? Explain.

> 

Why is "traffic from an infected host" not equivalent to "malicious traffic"?

> 

---

# Task 6 — NetFlow v9 and flow evidence orientation

## NetFlow v9 export capture

File opened:

```text
evidence/donbot-scenario6-netflow-v9.pcap
```

| Property | Result |
|---|---|
| Exporter IPv4 address |  |
| Collector IPv4 address |  |
| UDP source port |  |
| UDP destination port |  |
| NetFlow version |  |
| Source / Observation Domain ID |  |
| First sequence number |  |

What does one UDP NetFlow export packet contain?

> 

Why is an export-packet count not a flow count?

> 

## NetFlow template

Filter used:

```text

```

| Property | Result |
|---|---|
| Template ID |  |
| Field count |  |

List the template fields in order:

1. 
2. 
3. 
4. 
5. 
6. 
7. 
8. 
9. 
10. 

Why does the collector need the template before the data records?

> 

Why is the template refreshed periodically?

> 

## NetFlow data record

SMTP-oriented filter used:

```text

```

Record one decoded flow:

| Field | Value |
|---|---|
| Source IP |  |
| Source port |  |
| Destination IP |  |
| Destination port |  |
| Protocol |  |
| Packets |  |
| Bytes |  |
| First switched |  |
| Last switched |  |

Control-pair forward filter:

```text

```

Control-pair reverse filter:

```text

```

Why are forward and reverse directions separate NetFlow records here?

> 

Why are there more derived NetFlow records than CTU bidirectional rows?

> 

## Compare the evidence models

| Capability | Original PCAP | NetFlow v9 export PCAP | CTU bidirectional flow file |
|---|---|---|---|
| Full packet/application payload |  |  |  |
| Source/destination addresses |  |  |  |
| Ports/protocol |  |  |  |
| Byte/packet counters |  |  |  |
| Both directions in one record |  |  |  |
| Template needed for decoding |  |  |  |
| Efficient large-scale aggregation |  |  |  |

Which representation is best for plaintext command syntax?

> 

Which is best for ranking thousands of conversations?

> 

## SQLite import

SQLite database created successfully: [ ] yes [ ] no

Total imported rows:

> 

## Protocol counts

| Protocol | Flow count |
|---|---:|
| TCP |  |
| UDP |  |
| Other |  |

## Direction relative to `147.32.84.165`

| Direction | Flow count |
|---|---:|
| Outbound |  |
| Inbound |  |

## Top outbound destination ports

| Port | Flows | Distinct destinations | Total bytes |
|---:|---:|---:|---:|
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |

Top port by flow count:

> 

Top port by total bytes:

> 

Why are they different?

> 

## Top destination pairs by bytes

| Destination IP | Port | Flows | Bytes out | Bytes back | Total bytes |
|---|---:|---:|---:|---:|---:|
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |

Which pair is strongly bidirectional?

> 

Which behavior has many flows but essentially no return traffic?

> 

---

# Task 7 — Reproduce findings from flows

## SMTP

SQL query:

```sql

```

| Metric | Result |
|---|---:|
| Flow records |  |
| Distinct destination IPs |  |
| Source packets |  |
| Destination packets |  |
| Total bytes |  |
| Dominant state |  |

How does this compare with Wireshark?

> 

## Control pair

Candidate pair:

> 

SQL query:

```sql

```

| Metric | Result |
|---|---:|
| Flow count |  |
| FIN state count |  |
| RST state count |  |
| Source bytes |  |
| Destination bytes |  |

Which side sends most bytes?

> 

Does this agree with Follow TCP Stream?

> 

## Periodicity

Query used:

```sql

```

Candidate pair:

> 

Average gap:

> 

Common/typical gap values:

> 

Why are min/max values noisy?

> 

## RDP from flows

Inbound RDP source:

> 

Inbound flow count:

> 

Remote-source bytes:

> 

Host-response bytes:

> 

Outbound RDP rows from infected host:

> 

What did the flow representation make easier here?

> 

## PCAP vs flow differences

Give four reasons counts differ:

1. 
2. 
3. 
4. 

---

# Task 8 — Behavioral challenge

## Fan-out rule

SQL query:

```sql

```

Result:

> 

Why is this scan-like?

> 

False-positive possibility:

> 

One improvement to the rule:

> 

## Repeated low-fan-out rule

SQL query:

```sql

```

Result:

> 

Why does this look different from the fan-out behavior?

> 

## Packet cross-validation

Wireshark filter built from SQL result:

```text

```

Packet observation:

> 

Interpretation:

> 

Limitation:

> 

## Label validation

| Behavior | CTU label | Does it match your interpretation? |
|---|---|---|
| SMTP fan-out |  |  |
| Repeated control pair |  |  |
| Inbound RDP |  |  |
| HTTP request |  |  |

Why can a `From-Botnet` label still contain normal host activity?

> 

---

# Task 9 — Final analyst summary

## Timeline

| Time / range | Evidence source | Event | Filter/query | Confidence |
|---|---|---|---|---|
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |

## Final findings

What behavior can you prove?

> 

Strongest evidence of automated spam-related bot activity:

> 

Strongest direct C&C evidence:

> 

Traffic that should not be attributed to malware:

> 

What Wireshark answered best:

> 

What flow analysis answered best:

> 

What cannot be proven from the supplied evidence:

> 

What would you collect next on a live endpoint?

>
