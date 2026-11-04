# Week 10 - Network Traffic Monitoring with Packets and NetFlow

**Prerequisite:** Docker / Docker Compose familiarity  
**Host software required:** Docker and a text editor

This lab moves from host/application metrics to **network traffic observation**. You will capture packets, export flow records, query traffic summaries, generate several traffic patterns, and write a small flow-analysis program.

Everything needed for the practical work runs in Docker. Wireshark on the host is optional: the supplied `analyzer` container contains `tshark`, the Wireshark command-line analyzer.

---

# Part A - Concepts

## 1. Learning outcomes

By the end of the lab you should be able to:

1. Explain the difference between host metrics, packet capture, and flow monitoring.
2. Explain why the location of a monitoring sensor matters.
3. Relate a Docker network observation point to the purpose of a TAP or SPAN port.
4. Capture packets with `tcpdump` and save them as PCAP.
5. Use `tshark` to filter and summarize a PCAP without a graphical interface.
6. Identify the main fields of a network flow and explain the idea of the five-tuple.
7. Explain the exporter -> collector -> analyzer model used by NetFlow/IPFIX.
8. Configure `softflowd` to export NetFlow v9.
9. Use `softflowctl` to inspect and expire active flow state.
10. Use `nfdump` to list flows, filter them, and calculate top talkers.
11. Distinguish a high-volume transfer from a high-flow-count scan pattern.
12. Write a small program that derives simple behavior indicators from flow records.
13. Explain what packet data can reveal that flow records cannot, and vice versa.
14. Explain why encrypted traffic can still be useful for flow monitoring even when payload content is unavailable.

---

## 2. Three different questions

The previous monitoring exercise used exporters and Prometheus-style metrics. That answers questions such as:

```text
How much CPU is being used?
How much memory is free?
How many requests has a service handled?
```

Packet and flow monitoring answer different questions.

### Metrics

Metrics are already summarized measurements.

```text
node_cpu_usage = 62%
http_requests_total = 18231
```

They are compact and easy to graph, but they normally do not tell you which remote systems created the network traffic.

### Packets

Packet capture records individual packets or frames seen at an observation point.

A packet capture can contain details such as:

- source and destination addresses;
- ports;
- TCP flags;
- packet length;
- protocol headers;
- sometimes application payload.

PCAP is detailed, but the detail has a cost: storage, processing, privacy concerns, and investigation time.

### Flows

A flow record summarizes communication rather than retaining every packet.

A simplified record might say:

```text
source       10.77.0.12:49152
destination  10.77.0.20:8080
protocol     TCP
packets      420
bytes        524900
first seen   14:02:15
last seen    14:02:17
```

The HTTP body is not present. The traffic relationship and volume are.

A useful working model is:

```text
metrics  -> summarized system/application state
packets  -> detailed network evidence
flows    -> summarized network conversations
```

None of these replaces the others.

---

## 3. Observation point: why placement matters

A packet analyzer only sees traffic that reaches its capture interface.

On a physical switched network, a normal host does not automatically receive every unicast frame exchanged by every other host. Network monitoring therefore commonly uses mechanisms such as:

- a network TAP;
- a switch SPAN / mirror port;
- capture on a router, firewall, host, or other path through which the traffic actually passes.

This lab does not emulate a physical switch SPAN implementation. Instead, the `sensor` container shares the network namespace of `observed-host`.

That means both processes see the same `eth0` interface:

```text
                              +-----------------------+
client-normal  -------------> |                       |
client-bulk    -------------> | observed-host : eth0  |
client-scan    -------------> |                       |
                              +-----------+-----------+
                                          ^
                                          |
                                    same network
                                     namespace
                                          |
                              +-----------+-----------+
                              | sensor                |
                              | tcpdump + softflowd   |
                              +-----------------------+
```

The sensor therefore sees traffic entering and leaving the monitored host.

It does **not** magically see every packet on every Docker network. Sensor placement is part of monitoring design.

---

## 4. Packet capture and PCAP

`tcpdump` captures packets using libpcap and can save them to a `.pcap` file.

Typical capture syntax:

```bash
tcpdump -ni eth0
```

Useful options:

```text
-n    do not perform name resolution
-i    interface to capture
-w    write raw packets to a PCAP file
-r    read a PCAP file
-c    stop after a number of packets
```

A capture filter can reduce what is stored:

```bash
tcpdump -ni eth0 'tcp port 8080'
```

The filter is evaluated while packets are captured. Packets rejected by the capture filter are not stored.

`tshark` can then read the PCAP and apply display filters:

```bash
tshark -r capture.pcap -Y 'http.request'
```

A display filter does not alter the PCAP; it selects which already-captured packets are displayed.

---

## 5. Flow records and the five-tuple

A common way to identify an IP conversation is the five-tuple:

```text
source IP
source port
destination IP
destination port
transport protocol
```

For example:

```text
10.77.0.11 : 51234 -> 10.77.0.20 : 8080 / TCP
```

Flow exporters track packets that belong to flows and periodically export records containing metadata and counters.

Flow records commonly contain:

- source/destination addresses;
- source/destination ports;
- protocol;
- packet and byte counters;
- start/end times;
- TCP flags;
- interface information;
- additional fields depending on exporter and protocol version.

They normally do not contain the full application payload.

---

## 6. Exporter, collector, analyzer

The practical pipeline is:

```text
                watches packets
                     |
                     v
              +--------------+
              |  softflowd   |
              |   exporter   |
              +------+-------+
                     |
                     | NetFlow v9 / UDP 2055
                     v
              +--------------+
              |   nfcapd     |
              |  collector   |
              +------+-------+
                     |
                     | binary flow files
                     v
              +--------------+
              |   nfdump     |
              |   analyzer   |
              +--------------+
```

### Exporter

An exporter observes traffic and creates flow records.

Real exporters are often routers, multilayer switches, firewalls, virtual switches, or software agents. In this lab, `softflowd` acts as the exporter.

### Collector

A collector receives exported flow records and stores them.

In this lab `nfcapd` listens on UDP/2055 and writes files under `output/flows/`.

### Analyzer

An analyzer reads stored flow records and answers questions about the traffic.

In this lab you use `nfdump` directly and later write a small Python analyzer.

---

## 7. NetFlow v9 and IPFIX

NetFlow originated as a Cisco technology for summarizing IP traffic. NetFlow v9 uses templates so that an exporter can describe the fields contained in its records.

IPFIX standardized a related template-based flow export protocol.

This lab uses **NetFlow v9** for the main tasks because it maps directly to the material in the lecture and is supported by both tools in the supplied stack.

`softflowd` can also export IPFIX (`-v 10`). `nfcapd` can receive both NetFlow v9 and IPFIX, which makes switching export formats a useful extension exercise.

---

## 8. Flow expiration

An exporter cannot wait forever before reporting a conversation.

Flows are exported when conditions such as these are reached:

- the conversation becomes idle;
- the maximum flow lifetime is reached;
- a protocol condition ends the flow;
- an operator forces expiration.

The lab uses short expiration settings because waiting several minutes during a practical exercise would add no educational value.

You will also use:

```bash
softflowctl expire-all
```

to force currently tracked flows to be exported.

---

## 9. Packet data versus flow data

| Question | Packet capture | Flow records |
|---|---|---|
| Who talked to whom? | yes | yes |
| Which ports/protocols? | yes | yes |
| How many bytes/packets? | can calculate | directly summarized |
| Exact TCP flags? | yes | often summarized |
| HTTP path/query on plaintext HTTP? | yes | normally no |
| Full payload? | potentially | normally no |
| Top talkers over large networks? | expensive to derive | natural use case |
| Long retention | expensive | much cheaper |
| Privacy exposure | high | lower, but still sensitive |
| Encrypted application payload | unreadable | conversation metadata still useful |

A common operational pattern is:

```text
flow monitoring -> identify something interesting
packet capture   -> investigate the selected traffic in more detail
```

---

## 10. Lab topology

The Docker network is `10.77.0.0/24`.

The addresses are fixed so that results are reproducible.

| Service | Address | Role |
|---|---:|---|
| `client-normal` | `10.77.0.11` | normal mixed traffic |
| `client-bulk` | `10.77.0.12` | large uploads |
| `client-scan` | `10.77.0.13` | scan + periodic requests |
| `observed-host` | `10.77.0.20` | monitored HTTP/TCP/UDP service |
| `flow-collector` | `10.77.0.30` | receives NetFlow on UDP/2055 |
| `analyzer` | `10.77.0.40` | `tshark`, `nfdump`, Python |
| `sensor` | shares `observed-host` | packet/flow sensor |

The monitored host exposes:

```text
TCP/8080  HTTP service
TCP/9000  TCP echo service
UDP/9999  UDP echo service
```

Port `8088` on your Docker host is mapped to `observed-host:8080` only as a convenience check.

---

# Part B - Practical work

## 11. Start the environment

From the lab directory:

```bash
docker compose up -d --build
```

Check all services:

```bash
docker compose ps
```

The expected services are:

```text
observed-host
client-normal
client-bulk
client-scan
flow-collector
sensor
analyzer
```

Check the application:

```bash
curl http://localhost:8088/health
```

Expected:

```text
ok
```

If a service has exited:

```bash
docker compose ps -a
docker compose logs SERVICE
```

Do not start changing random configuration until you have read the actual error.

---

# Task 1 - Capture and inspect packets

The first task uses packet evidence only. Do not start the NetFlow exporter yet.

## 1.1 Verify the observation point

Inspect the monitored interface from the observed host:

```bash
docker compose exec observed-host ip -br addr
```

Now inspect it from the sensor:

```bash
docker compose exec sensor ip -br addr
```

Compare the `eth0` address.

Question: why do the two containers report the same network interface and IP address?

Also verify client addresses:

```bash
docker compose exec client-normal ip -br addr
docker compose exec client-bulk ip -br addr
docker compose exec client-scan ip -br addr
```

Record:

```text
normal client:
bulk client:
scan client:
observed host:
```

## 1.2 Capture a plaintext request

Use two terminals.

In terminal A:

```bash
docker compose exec sensor \
  tcpdump -ni eth0 -w /captures/task1.pcap 'tcp port 8080'
```

Leave it running.

In terminal B:

```bash
docker compose exec client-normal \
  /lab/traffic/plaintext-demo.sh
```

Then generate a little more traffic:

```bash
docker compose exec client-normal \
  /lab/traffic/normal.sh
```

Return to terminal A and stop `tcpdump` with `Ctrl-C`.

Verify the file exists:

```bash
ls -lh output/pcap/task1.pcap
```

## 1.3 Inspect conversations

Use the supplied analyzer:

```bash
docker compose exec analyzer \
  tshark -r /captures/task1.pcap -q -z conv,ip
```

Questions:

1. Which two IP addresses dominate this capture?
2. Why is `flow-collector` absent at this stage?
3. Does the PCAP contain both request and response traffic?

## 1.4 Extract HTTP requests

```bash
docker compose exec analyzer \
  tshark -r /captures/task1.pcap \
  -Y 'http.request' \
  -T fields \
  -e ip.src \
  -e http.request.method \
  -e http.request.uri
```

Find the request containing:

```text
lab-demo-token-4821
```

Questions:

1. Why can `tshark` display this token?
2. Would you expect the same application path and token to be visible if this were HTTPS?
3. What privacy problem would arise if an organization retained unrestricted full packet captures for a long period?

Checkpoint: you should have a PCAP containing traffic to TCP/8080 and should be able to recover the plaintext HTTP URI from it.

---

# Task 2 - Build the NetFlow export pipeline

Now change from packet-by-packet evidence to summarized flows.

`nfcapd` is already running as the collector. The exporter is intentionally not configured for you.

## 2.1 Check the collector

```bash
docker compose logs --tail=20 flow-collector
```

Check that UDP/2055 is open inside the collector container:

```bash
docker compose exec flow-collector \
  ss -lunp
```

You should see a listener using port `2055`.

## 2.2 Complete the exporter configuration

Open:

```text
work/start-exporter.sh
```

There are three values to complete:

```text
IFACE
COLLECTOR
VERSION
```

Determine them from the topology and the requirements:

- capture the interface shared with `observed-host`;
- export to the Compose service running `nfcapd` on UDP/2055;
- use NetFlow v9.

The rest of the command is already present.

Important parts that are supplied:

```text
-T full
```

tracks source/destination addresses, ports, and protocol.

```text
-t maxlife=30s
-t expint=5s
```

make the lab export state quickly.

The final BPF expression excludes NetFlow export packets themselves:

```text
not (udp and dst port 2055)
```

Why is that exclusion useful?

## 2.3 Start the exporter

Run your script inside the sensor container:

```bash
docker compose exec sensor \
  bash /work/start-exporter.sh
```

Check the process:

```bash
docker compose exec sensor pgrep -a softflowd
```

Ask the running exporter for its timeout configuration:

```bash
docker compose exec sensor \
  softflowctl -c /run/softflowd.ctl timeouts
```

## 2.4 Observe active flow state before export

Generate normal traffic:

```bash
docker compose exec client-normal \
  /lab/traffic/normal.sh
```

Immediately inspect active flows:

```bash
docker compose exec sensor \
  softflowctl -c /run/softflowd.ctl dump-flows
```

Look for:

- TCP/8080;
- TCP/9000;
- UDP/9999;
- ICMP.

Not every protocol is guaranteed to still be active by the time you run the command because flows expire.

## 2.5 Force export

```bash
docker compose exec sensor \
  softflowctl -c /run/softflowd.ctl expire-all
```

The collector rotates files every 10 seconds. Wait until at least one `nfcapd.*` file appears:

```bash
ls -lh output/flows/
```

## 2.6 Read the flow records

```bash
docker compose exec analyzer \
  nfdump -R /flows -o long
```

If you see no completed flow file yet, wait a few seconds and try again.

Questions:

1. Which fields in the flow output correspond to the five-tuple?
2. Where are the HTTP request URI and token from Task 1?
3. Which representation is easier for answering "how many bytes did each host exchange?": the PCAP or the flow records?

Checkpoint: `softflowd` must be exporting to `flow-collector`, and `nfdump -R /flows` must show records.

---

# Task 3 - Generate traffic patterns and find top talkers

The point of flow monitoring is not to stare at individual records indefinitely. Summarize them.

First clear the previous exercise data:

```bash
./scripts/clear-data.sh
```

The exporter remains configured in the sensor network namespace. Confirm it still exists:

```bash
docker compose exec sensor pgrep -a softflowd
```

If it is not running, rerun your `work/start-exporter.sh`.

## 3.1 Generate three profiles

Run these from separate terminals if you want to observe them concurrently.

Normal mixed traffic:

```bash
docker compose exec client-normal \
  /lab/traffic/normal.sh
```

Large uploads:

```bash
docker compose exec client-bulk \
  /lab/traffic/bulk.sh
```

Connect scan followed by periodic requests:

```bash
docker compose exec client-scan \
  /lab/traffic/scan.sh
```

Force current flows out:

```bash
docker compose exec sensor \
  softflowctl -c /run/softflowd.ctl expire-all
```

Wait for collector rotation and inspect:

```bash
sleep 11
ls -lh output/flows/
```

## 3.2 Top sources by bytes

```bash
docker compose exec analyzer \
  nfdump -R /flows -s srcip/bytes -n 10
```

Question: which client is the largest **source** of bytes?

Explain why the large-upload profile was designed as an HTTP POST rather than a large HTTP download for this particular question.

## 3.3 Top sources by number of flows

```bash
docker compose exec analyzer \
  nfdump -R /flows -s srcip/flows -n 10
```

Compare the ranking to the previous command.

Questions:

1. Does the host with the most bytes necessarily have the most flows?
2. Which profile creates many relatively small TCP conversations?
3. Why can "many flows" and "many bytes" indicate very different behavior?

## 3.4 Destination ports

```bash
docker compose exec analyzer \
  nfdump -R /flows -s dstport/flows -n 20 'proto tcp'
```

Identify:

- the normal HTTP service port;
- the TCP echo service port;
- ports touched by the scan.

A scan does not need to transfer much data. Its distinguishing feature can be breadth rather than volume.

## 3.5 Conversations

Show IP pairs ordered by bytes:

```bash
docker compose exec analyzer \
  nfdump -R /flows -s record/bytes -A srcip,dstip -n 20
```

Then show only traffic involving the bulk client:

```bash
docker compose exec analyzer \
  nfdump -R /flows -o long 'host 10.77.0.12'
```

Change the filter to isolate one other client.

Question: how is this filter similar to a `tcpdump` expression, and how is it fundamentally different from a capture filter?

---

# Task 4 - Build a small flow behavior analyzer

Commercial monitoring systems automate the summaries you have just produced manually. You will build a deliberately small version.

## 4.1 Export flow records as CSV

`nfdump` can emit a custom CSV format.

Create a CSV containing:

```text
source IP
source port
destination IP
destination port
protocol
packets
bytes
```

Use:

```bash
docker compose exec analyzer sh -lc \
  "nfdump -R /flows -N -o 'csv:%sa,%sp,%da,%dp,%pr,%pkt,%byt' 'dst host 10.77.0.20' > /work/flows.csv"
```

Inspect it:

```bash
head -n 10 work/flows.csv
```

`-N` asks `nfdump` to print plain numeric counters instead of human-friendly scaling such as `4.2 M`.

The final flow filter, `dst host 10.77.0.20`, keeps the exercise focused on traffic **toward the monitored host**. Otherwise response traffic from `observed-host` would also be grouped as source behavior and would make this deliberately small classifier less clear.

Why is `-N` useful for a program that has to parse the data?

## 4.2 Complete the program

Open:

```text
work/analyze_flows.py
```

Complete the TODOs.

For each source IP, calculate:

- number of flow records;
- total bytes;
- total packets;
- number of distinct destination ports;
- protocols observed.

Then implement this simple lab heuristic:

```text
scan-like:
    at least 12 distinct destination ports
    AND at least 12 flow records

bulk-sender:
    at least 2 MiB of source bytes

otherwise:
    baseline
```

Run it:

```bash
docker compose exec analyzer \
  python3 /work/analyze_flows.py /work/flows.csv
```

Expected behavior:

- `10.77.0.12` should be identified as the bulk sender;
- `10.77.0.13` should show scan-like breadth;
- `10.77.0.11` should look closer to baseline traffic.

Exact byte/packet/flow counts can vary.

## 4.3 Critique your own detector

Answer these questions:

1. Why is "12 destination ports" not a universal definition of a port scan?
2. Give one legitimate application that could contact many destination ports.
3. Give one way an attacker could scan slowly enough to avoid this simple threshold.
4. Why should a real detection system compare behavior over time rather than rely only on a single fixed threshold?
5. What additional context could improve classification? Consider asset role, expected services, historical baseline, authentication logs, DNS, or threat intelligence.

A working program is not the same thing as a good detector. The logic matters.

---

# Task 5 - Incident-style investigation: flow first, packets second

This task uses both monitoring approaches on the same traffic.

Clear old data:

```bash
./scripts/clear-data.sh
```

Make sure the exporter is running:

```bash
docker compose exec sensor pgrep -a softflowd
```

## 5.1 Start a full packet capture

In terminal A:

```bash
docker compose exec sensor \
  tcpdump -ni eth0 -w /captures/incident.pcap \
  'not (udp and dst port 2055)'
```

Leave it running.

## 5.2 Generate the incident traffic

In terminal B run all four traffic sets:

```bash
docker compose exec client-normal /lab/traffic/normal.sh
```

```bash
docker compose exec client-bulk /lab/traffic/bulk.sh
```

```bash
docker compose exec client-scan /lab/traffic/scan.sh
```

Finally send the deliberately plaintext request again:

```bash
docker compose exec client-scan \
  /lab/traffic/plaintext-demo.sh
```

Stop the packet capture with `Ctrl-C`.

Force current flows to the collector:

```bash
docker compose exec sensor \
  softflowctl -c /run/softflowd.ctl expire-all
```

Wait for rotation:

```bash
sleep 11
```

## 5.3 Triage with flows only

Pretend you do not yet have permission to inspect packet payloads.

Use only `nfdump` and answer:

```text
Which source transferred the most bytes?
Which source contacted the greatest variety of TCP destination ports?
Which source generated the greatest number of flows?
Which service received the large data transfer?
Which source appears scan-like?
```

Useful starting commands:

```bash
docker compose exec analyzer nfdump -R /flows -s srcip/bytes -n 10
```

```bash
docker compose exec analyzer nfdump -R /flows -s srcip/flows -n 10
```

```bash
docker compose exec analyzer nfdump -R /flows -s dstport/flows -n 20 'proto tcp'
```

Construct at least **two additional `nfdump` commands yourself** to support your conclusions.

Record the commands and what each one proves.

## 5.4 Drill down with packet data

Now inspect the PCAP.

First summarize IP conversations:

```bash
docker compose exec analyzer \
  tshark -r /captures/incident.pcap -q -z conv,ip
```

Then list HTTP requests from the scan client only:

```bash
docker compose exec analyzer \
  tshark -r /captures/incident.pcap \
  -Y 'ip.src == 10.77.0.13 && http.request' \
  -T fields \
  -e frame.time_relative \
  -e ip.src \
  -e tcp.dstport \
  -e http.request.method \
  -e http.request.uri
```

Find the request containing the demo token.

Questions:

1. Could the flow records tell you the token value?
2. Could the flow records tell you that the source repeatedly connected to TCP/8080?
3. Which data source would you prefer to retain for 90 days across a large network, and why?
4. Which data source would you prefer for a short, targeted forensic capture?
5. How would HTTPS change the packet-investigation result?
6. Would HTTPS make flow monitoring useless? Explain.

## 5.5 Compare storage size

Check the packet capture:

```bash
ls -lh output/pcap/incident.pcap
```

Check the complete flow directory:

```bash
du -sh output/flows
```

Do not treat the size ratio in this tiny lab as a universal production ratio. The point is to identify why flow records are naturally much more compact: many packets are summarized into records.

---

# 12. Final practical questions

Be prepared to explain the following without reading commands from the handout:

1. Where is the observation point in this lab?
2. Why can the sensor see the monitored host's traffic?
3. What is a five-tuple?
4. What is the difference between `softflowd`, `nfcapd`, and `nfdump`?
5. Why do flow exporters expire flows?
6. Why do we exclude UDP/2055 from the exporter's capture filter?
7. What does a top-talker-by-bytes view reveal that a top-talker-by-flows view may not?
8. Why can a scan be conspicuous in flow data even when it transfers very few bytes?
9. What useful information remains visible when application payload is encrypted?
10. When would you choose packet capture rather than flow monitoring?

---

# 13. Optional extensions

## 13.1 Export IPFIX instead of NetFlow v9

Stop the current exporter:

```bash
docker compose exec sensor \
  softflowctl -c /run/softflowd.ctl shutdown
```

Modify your exporter to use version `10`, which `softflowd` uses for IPFIX.

Clear the flow directory, start the exporter again, generate traffic, expire flows, and verify that `nfcapd` still accepts the records.

Question: what stayed the same in your analysis workflow despite changing the wire export format?

## 13.2 Experiment with exporter tracking level

Read:

```bash
docker compose exec sensor softflowd -h
```

Compare the idea of:

```text
-T full
-T proto
-T ip
```

Predict what analysis becomes impossible if source/destination ports are no longer part of the flow key.

## 13.3 Open the PCAP in Wireshark

If Wireshark is installed on your own machine, open:

```text
output/pcap/incident.pcap
```

Try display filters such as:

```text
http.request
ip.addr == 10.77.0.13
tcp.flags.syn == 1 && tcp.flags.ack == 0
```

The lab does not require local Wireshark because `tshark` provides the required analysis inside Docker.

---

# 14. Cleanup

Stop the stack:

```bash
docker compose down
```

Remove generated capture and flow files if you no longer need them:

```bash
rm -f output/pcap/*.pcap
rm -f output/flows/nfcapd.* output/flows/current.*
```

---

# 15. Command reference

```text
tcpdump      capture packets / create PCAP files
tshark       Wireshark command-line packet analysis
softflowd    observe packets and create/export flow records
softflowctl  inspect/control a running softflowd exporter
nfcapd       receive NetFlow/IPFIX and store flow files
nfdump       query, filter, aggregate, and summarize stored flow records
```

Useful `nfdump` patterns:

```bash
nfdump -R /flows -o long
nfdump -R /flows -s srcip/bytes -n 10
nfdump -R /flows -s srcip/flows -n 10
nfdump -R /flows -s dstport/flows -n 20 'proto tcp'
nfdump -R /flows -o long 'host 10.77.0.12'
nfdump -R /flows -o long 'dst port 8080'
```

The important skill is not memorizing these exact commands. It is deciding what question you are trying to answer and selecting packet or flow evidence that can actually answer it.
