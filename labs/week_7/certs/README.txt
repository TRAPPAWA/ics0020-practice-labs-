These are lab-only TLS credentials for the optional exercise.

- ca.crt is the lab CA certificate trusted by the toolbox client.
- server.crt is the syslog-ng server certificate for DNS name "syslog-ng".
- server.key is the matching private key.

The private key is intentionally distributed with the classroom package so the
exercise works offline. Never reuse these credentials outside the lab.
Run scripts/regenerate-certs.sh if you want a fresh lab CA and server key pair.
