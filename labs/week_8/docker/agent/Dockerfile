FROM debian:13-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates curl iproute2 netcat-openbsd procps python3 snmp snmpd \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/lab-entrypoint
COPY http_service.py /opt/lab/http_service.py
COPY send-notification.sh /opt/lab/send-notification.sh
RUN chmod +x /usr/local/bin/lab-entrypoint /opt/lab/send-notification.sh

EXPOSE 161/udp 8080/tcp
ENTRYPOINT ["/usr/local/bin/lab-entrypoint"]
