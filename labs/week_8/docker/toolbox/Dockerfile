FROM debian:13-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash bc ca-certificates curl gawk iproute2 jq netcat-openbsd procps \
       snmp snmptrapd tcpdump \
    && rm -rf /var/lib/apt/lists/*
CMD ["sleep", "infinity"]
