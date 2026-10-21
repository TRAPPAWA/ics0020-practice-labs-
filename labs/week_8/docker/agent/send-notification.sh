#!/bin/sh
set -eu
MODE="${1:-trap}"
TARGET="${2:-trap-receiver}"
COMMUNITY="${3:-labtraps}"
INDEX="$(cat /sys/class/net/eth0/ifindex)"

# SNMPv2-MIB::linkDown
TRAP_OID='.1.3.6.1.6.3.1.1.5.3'
IFINDEX=".1.3.6.1.2.1.2.2.1.1.${INDEX}"
IFDESCR=".1.3.6.1.2.1.2.2.1.2.${INDEX}"
IFOPER=".1.3.6.1.2.1.2.2.1.8.${INDEX}"

case "$MODE" in
  trap)
    exec snmptrap -v2c -c "$COMMUNITY" "$TARGET" '' "$TRAP_OID" \
      "$IFINDEX" i "$INDEX" "$IFDESCR" s eth0 "$IFOPER" i 2
    ;;
  inform)
    exec snmpinform -v2c -c "$COMMUNITY" -t 2 -r 1 "$TARGET" '' "$TRAP_OID" \
      "$IFINDEX" i "$INDEX" "$IFDESCR" s eth0 "$IFOPER" i 2
    ;;
  *)
    echo "usage: $0 trap|inform [target] [community]" >&2
    exit 2
    ;;
esac
