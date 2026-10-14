#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../certs"

rm -f ca.key ca.crt server.csr server.crt server.key ca.srl
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -sha256 \
  -subj '/CN=Logging Lab CA/O=Logging Lab' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign' \
  -keyout ca.key -out ca.crt
openssl req -new -newkey rsa:2048 -nodes -sha256 \
  -keyout server.key -out server.csr -config openssl.cnf
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 3650 -sha256 -extfile openssl.cnf -extensions v3_server -out server.crt
rm -f ca.key server.csr ca.srl
chmod 600 server.key
echo "Generated lab CA and syslog-ng server certificate."
