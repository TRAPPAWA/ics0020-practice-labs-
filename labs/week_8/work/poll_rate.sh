#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-student-agent}"
INDEX="${2:-2}"
INTERVAL="${3:-5}"
COMMUNITY="labpublic"

# Task 3: complete this script.
# Use the 64-bit outbound octet counter:
#   .1.3.6.1.2.1.31.1.1.1.10.<ifIndex>
#
# Useful Net-SNMP output option:
#   -Oqv    print only the value
#
# Formula:
#   bits_per_second = (counter_after - counter_before) * 8 / interval
#
# TODO 1: build the OID using INDEX.
# TODO 2: read the first counter value with snmpget.
# TODO 3: sleep for INTERVAL seconds.
# TODO 4: read the second counter value.
# TODO 5: print the delta and calculated bit/s.
