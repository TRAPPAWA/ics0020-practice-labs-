# Sources and attribution

## Primary dataset

**Stratosphere Laboratory — CTU-13 Dataset**  
https://www.stratosphereips.org/datasets-ctu13

Scenario used:

**CTU-Malware-Capture-Botnet-47 / Scenario 6**  
https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-47/

Authoritative scenario facts used by this lab include:

- probable malware name listed as DonBot;
- public bot-only PCAP `botnet-capture-20110816-donbot.pcap` captured on the infected VM interface;
- infected host `147.32.84.165`, Windows XP, host name SARUMAN;
- CTU bidirectional flow files and host/direction-based labels;
- documented malware-start and capture timeline.

CTU-13 is published under **CC BY**. The lab does not contain or download the malware executable.

## Flow evidence in this package

The CTU `.binetflow` material is Argus-style **bidirectional flow text**. It is valuable flow evidence, but it is not literally a NetFlow-v9 export capture.

To teach the NetFlow wire format honestly, the package also includes:

```text
donbot-scenario6-netflow-v9.pcap
```

This file is generated locally by:

```text
tools/build_netflow_v9_pcap.py
```

from the unlabeled CTU flow subset. Each source-direction counter becomes one unidirectional NetFlow record; rows with reverse-direction packets also produce a reverse record. The artifact uses TEST-NET documentation addresses for the synthetic exporter/collector and must not be presented as original CTU wire evidence.

## NetFlow v9 specification

**RFC 3954 — Cisco Systems NetFlow Services Export Version 9**  
https://www.rfc-editor.org/rfc/rfc3954

The derived teaching PCAP follows the RFC 3954 structure used in the lab:

- NetFlow v9 export packet header;
- Template FlowSet ID 0;
- Template ID 256;
- Data FlowSets referencing Template 256;
- fields for IPv4 source/destination, transport ports, protocol, ToS, packet/byte counters and FIRST/LAST_SWITCHED times;
- periodic template refresh.

## Wireshark

Wireshark User's Guide:  
https://www.wireshark.org/docs/wsug_html_chunked/

Cisco NetFlow/IPFIX display-filter reference (`cflow`):  
https://www.wireshark.org/docs/dfref/c/cflow.html

TShark manual:  
https://www.wireshark.org/docs/man-pages/tshark.html

TShark is used only for reproducible verification. The student practical is designed around Wireshark Desktop.

## Published scenario behavior

A published CTU-13 analysis describes Scenario 6 behavior including SMTP scanning and approximately periodic proprietary command/control communication. The lab does not ask students to accept that description first; they derive the behavior from the supplied evidence and use external descriptions only as supporting context.

## Course connection

The accompanying lecture on simple/manual log analysis emphasizes moving beyond line-by-line review toward summaries, trends, correlations and actionable conclusions. This lab applies those ideas to packet and flow evidence instead of repeating basic text-log parsing.
