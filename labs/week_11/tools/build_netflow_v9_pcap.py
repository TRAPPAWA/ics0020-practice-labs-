#!/usr/bin/env python3
"""Build a small standards-based NetFlow v9 export PCAP from CTU bidirectional flows.

The source CTU .binetflow data is bidirectional Argus-style flow text, not a NetFlow
wire capture.  This script derives *unidirectional* NetFlow v9 records from the
source/destination counters so students can inspect the actual NetFlow v9 template
and data-record mechanism in Wireshark.  It does not claim to reproduce an original
router/exporter capture.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import ipaddress
import socket
import struct
from pathlib import Path

TEMPLATE_ID = 256
SOURCE_ID = 6
EXPORTER_IP = "192.0.2.6"       # TEST-NET-1 documentation address
COLLECTOR_IP = "192.0.2.200"    # TEST-NET-1 documentation address
EXPORTER_PORT = 9996
COLLECTOR_PORT = 2055

# RFC 3954 field type, field length.
FIELDS = [
    (8, 4),   # IPV4_SRC_ADDR
    (12, 4),  # IPV4_DST_ADDR
    (7, 2),   # L4_SRC_PORT
    (11, 2),  # L4_DST_PORT
    (4, 1),   # PROTOCOL
    (5, 1),   # TOS
    (2, 4),   # IN_PKTS
    (1, 4),   # IN_BYTES
    (22, 4),  # FIRST_SWITCHED
    (21, 4),  # LAST_SWITCHED
]
RECORD_LEN = sum(length for _, length in FIELDS)


def parse_ts(text: str, offset_hours: int = 2) -> float:
    naive = dt.datetime.strptime(text, "%Y/%m/%d %H:%M:%S.%f")
    tz = dt.timezone(dt.timedelta(hours=offset_hours))
    return naive.replace(tzinfo=tz).timestamp()


def integer(value: str | None) -> int:
    if value is None or value == "":
        return 0
    return int(float(value))


def port(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        # Some Argus exports can render a well-known service by name.
        try:
            return socket.getservbyname(value)
        except OSError:
            return 0


def protocol_number(name: str) -> int:
    name = (name or "").lower()
    if name == "tcp":
        return 6
    if name == "udp":
        return 17
    if name == "icmp":
        return 1
    try:
        return int(name)
    except ValueError:
        return 0


def ip_checksum(header: bytes) -> int:
    if len(header) % 2:
        header += b"\x00"
    total = sum(struct.unpack(f"!{len(header)//2}H", header))
    total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def ethernet_ipv4_udp(payload: bytes, ident: int) -> bytes:
    src_mac = bytes.fromhex("020000000006")
    dst_mac = bytes.fromhex("0200000000c8")
    eth = dst_mac + src_mac + struct.pack("!H", 0x0800)

    src_ip = ipaddress.IPv4Address(EXPORTER_IP).packed
    dst_ip = ipaddress.IPv4Address(COLLECTOR_IP).packed
    udp_len = 8 + len(payload)
    total_len = 20 + udp_len
    ip0 = struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0, total_len, ident & 0xFFFF, 0, 64, 17, 0, src_ip, dst_ip,
    )
    csum = ip_checksum(ip0)
    iphdr = struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0, total_len, ident & 0xFFFF, 0, 64, 17, csum, src_ip, dst_ip,
    )
    # UDP checksum 0 is valid for IPv4 and avoids pretending this was an original wire export.
    udp = struct.pack("!HHHH", EXPORTER_PORT, COLLECTOR_PORT, udp_len, 0)
    return eth + iphdr + udp + payload


def template_flowset() -> bytes:
    body = struct.pack("!HH", TEMPLATE_ID, len(FIELDS))
    for field_type, field_len in FIELDS:
        body += struct.pack("!HH", field_type, field_len)
    length = 4 + len(body)
    return struct.pack("!HH", 0, length) + body


def data_record(rec: dict, boot_epoch: float) -> bytes:
    first_ms = max(0, int(round((rec["start"] - boot_epoch) * 1000)))
    last_ms = max(first_ms, int(round((rec["last"] - boot_epoch) * 1000)))
    return b"".join([
        ipaddress.IPv4Address(rec["src"]).packed,
        ipaddress.IPv4Address(rec["dst"]).packed,
        struct.pack("!H", rec["sport"]),
        struct.pack("!H", rec["dport"]),
        struct.pack("!B", rec["proto"]),
        struct.pack("!B", rec["tos"] & 0xFF),
        struct.pack("!I", rec["packets"] & 0xFFFFFFFF),
        struct.pack("!I", rec["bytes"] & 0xFFFFFFFF),
        struct.pack("!I", first_ms & 0xFFFFFFFF),
        struct.pack("!I", last_ms & 0xFFFFFFFF),
    ])


def data_flowset(records: list[dict], boot_epoch: float) -> bytes:
    body = b"".join(data_record(r, boot_epoch) for r in records)
    padding = (-((4 + len(body)) % 4)) % 4
    length = 4 + len(body) + padding
    return struct.pack("!HH", TEMPLATE_ID, length) + body + (b"\x00" * padding)


def directional_records(csv_path: Path, offset_hours: int) -> list[dict]:
    out: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            start = parse_ts(row["StartTime"], offset_hours)
            last = parse_ts(row["LastTime"], offset_hours)
            proto = protocol_number(row["Proto"])
            sport = port(row["Sport"])
            dport = port(row["Dport"])
            src_pkts = integer(row["SrcPkts"])
            dst_pkts = integer(row["DstPkts"])
            src_bytes = integer(row["SrcBytes"])
            dst_bytes = integer(row["DstBytes"])
            stos = integer(row.get("sTos"))
            dtos = integer(row.get("dTos"))
            if src_pkts > 0:
                out.append(dict(
                    start=start, last=last, src=row["SrcAddr"], dst=row["DstAddr"],
                    sport=sport, dport=dport, proto=proto, tos=stos,
                    packets=src_pkts, bytes=src_bytes,
                ))
            if dst_pkts > 0:
                out.append(dict(
                    start=start, last=last, src=row["DstAddr"], dst=row["SrcAddr"],
                    sport=dport, dport=sport, proto=proto, tos=dtos,
                    packets=dst_pkts, bytes=dst_bytes,
                ))
    out.sort(key=lambda r: (r["last"], r["start"], r["src"], r["dst"], r["sport"], r["dport"]))
    return out


def export_packets(records: list[dict], records_per_packet: int, template_every: int):
    if not records:
        return
    boot_epoch = min(r["start"] for r in records) - 3600.0
    sequence = 0
    for packet_index, pos in enumerate(range(0, len(records), records_per_packet)):
        chunk = records[pos:pos + records_per_packet]
        export_epoch = max(r["last"] for r in chunk) + 0.001
        sys_uptime = int(round((export_epoch - boot_epoch) * 1000)) & 0xFFFFFFFF
        include_template = packet_index == 0 or (template_every > 0 and packet_index % template_every == 0)
        sets = []
        count = len(chunk)
        if include_template:
            sets.append(template_flowset())
            count += 1  # Count is total template + data records, per RFC 3954.
        sets.append(data_flowset(chunk, boot_epoch))
        header = struct.pack(
            "!HHIIII",
            9, count, sys_uptime, int(export_epoch), sequence & 0xFFFFFFFF, SOURCE_ID,
        )
        payload = header + b"".join(sets)
        sequence += 1
        yield export_epoch, ethernet_ipv4_udp(payload, packet_index + 1), include_template, len(chunk)


def write_pcap(path: Path, packet_iter) -> tuple[int, int, int]:
    packets = records = templates = 0
    with path.open("wb") as handle:
        # Classic little-endian PCAP, microsecond timestamps, Ethernet linktype.
        handle.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for epoch, frame, has_template, record_count in packet_iter:
            sec = int(epoch)
            usec = int(round((epoch - sec) * 1_000_000))
            if usec >= 1_000_000:
                sec += 1
                usec -= 1_000_000
            handle.write(struct.pack("<IIII", sec, usec, len(frame), len(frame)))
            handle.write(frame)
            packets += 1
            records += record_count
            templates += int(has_template)
    return packets, records, templates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_pcap", type=Path)
    parser.add_argument("--utc-offset", type=int, default=2,
                        help="source text timestamp offset from UTC; CTU Scenario 6 uses +02")
    parser.add_argument("--records-per-packet", type=int, default=25)
    parser.add_argument("--template-every", type=int, default=50,
                        help="resend template every N export packets; 0 disables refresh after first")
    args = parser.parse_args()

    records = directional_records(args.input_csv, args.utc_offset)
    args.output_pcap.parent.mkdir(parents=True, exist_ok=True)
    packets, emitted, templates = write_pcap(
        args.output_pcap,
        export_packets(records, args.records_per_packet, args.template_every),
    )
    print(f"source bidirectional rows: {sum(1 for _ in args.input_csv.open()) - 1}")
    print(f"derived unidirectional records: {len(records)}")
    print(f"NetFlow v9 export packets: {packets}")
    print(f"template refresh packets: {templates}")
    print(f"data records written: {emitted}")
    print(f"output: {args.output_pcap}")


if __name__ == "__main__":
    main()
