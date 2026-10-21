#!/bin/sh
set -eu

mkdir -p /var/lib/snmp

if [ -n "${SNMPV3_USER:-}" ] && [ ! -f /var/lib/snmp/.lab_v3_initialized ]; then
    : "${SNMPV3_AUTH_PASS:?SNMPV3_AUTH_PASS is required when SNMPV3_USER is set}"
    : "${SNMPV3_PRIV_PASS:?SNMPV3_PRIV_PASS is required when SNMPV3_USER is set}"
    cat >> /var/lib/snmp/snmpd.conf <<EOV3
createUser ${SNMPV3_USER} SHA "${SNMPV3_AUTH_PASS}" AES "${SNMPV3_PRIV_PASS}"
EOV3
    chmod 600 /var/lib/snmp/snmpd.conf
    touch /var/lib/snmp/.lab_v3_initialized
fi

python3 /opt/lab/http_service.py --port 8080 >/tmp/http-service.log 2>&1 &
HTTP_PID=$!
trap 'kill "$HTTP_PID" 2>/dev/null || true' EXIT INT TERM

exec snmpd -f -Lo
