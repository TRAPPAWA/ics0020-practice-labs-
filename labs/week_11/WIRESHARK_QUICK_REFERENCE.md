# Wireshark Quick Reference for This Lab

This is a reference sheet, not a solution sheet.

## Main workflow

1. State the question.
2. Apply a display filter.
3. Use a statistics view if the question is about counts, endpoints, conversations, or time.
4. Inspect individual packets only after narrowing the evidence.
5. Record the filter and observation in `WORKSHEET.md`.

## Useful menus

```text
Statistics -> Capture File Properties
Statistics -> Protocol Hierarchy
Statistics -> Endpoints
Statistics -> Conversations
Statistics -> I/O Graphs
Analyze -> Follow -> TCP Stream
Analyze -> Expert Information
Edit -> Find Packet
View -> Time Display Format
```

## Useful filters

```text
# One host, either direction
ip.addr == 147.32.84.165

# Host as initiator/source
ip.src == 147.32.84.165

# Host as receiver/destination
ip.dst == 147.32.84.165

# Initial TCP SYN
tcp.flags.syn == 1 && tcp.flags.ack == 0

# SYN-ACK
tcp.flags.syn == 1 && tcp.flags.ack == 1

# SMTP target
tcp.dstport == 25

# RDP either direction
tcp.port == 3389

# DNS query packets
dns.flags.response == 0

# DNS blacklist lookup names
dns.qry.name contains "spamcop.net"

# HTTP request packets
http.request

# One TCP stream
tcp.stream eq N

# Search raw TCP data for readable text
tcp contains "mstshash"
tcp contains "RBL:"

# TCP analysis flags
tcp.analysis.retransmission
tcp.analysis.spurious_retransmission
```

## GUI shortcuts that reduce typing

In the Packet Details pane, right-click a field and use:

```text
Apply as Filter -> Selected
Apply as Column
```

Useful temporary columns:

```text
tcp.stream
tcp.srcport
tcp.dstport
dns.qry.name
frame.time_epoch
```

## Time analysis

For a timeline relative to capture start:

```text
View -> Time Display Format -> Seconds Since First Captured Packet
```

For measuring gaps between packets that match your current filter:

```text
View -> Time Display Format -> Seconds Since Previous Displayed Packet
```

Remember that display filters do not delete packets. They only change what Wireshark shows.

## NetFlow v9 capture

Open `evidence/donbot-scenario6-netflow-v9.pcap` for the NetFlow-wire-format part of Task 6.

Wireshark's display-filter protocol name for NetFlow/IPFIX is `cflow`.

```text
# All decoded NetFlow/IPFIX export packets
cflow

# NetFlow version 9 only
cflow.version == 9

# Packets containing Template ID 256
cflow.template_id == 256

# Export packets containing a record sourced by the investigated host
cflow.srcaddr == 147.32.84.165

# Export packets containing an SMTP-oriented flow record
cflow.srcaddr == 147.32.84.165 && cflow.dstport == 25

# C&C-like forward flow records
cflow.srcaddr == 147.32.84.165 && cflow.dstaddr == 91.212.135.158 && cflow.dstport == 5678

# C&C-like reverse flow records
cflow.srcaddr == 91.212.135.158 && cflow.dstaddr == 147.32.84.165 && cflow.srcport == 5678
```

Remember: one UDP export packet can contain many NetFlow data records. A display filter can match an export packet because **one embedded record** matches; inspect the expanded Data FlowSet rather than assuming every record in the packet has the filtered value.
