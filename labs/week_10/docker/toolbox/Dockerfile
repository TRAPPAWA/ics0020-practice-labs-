FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       curl \
       iproute2 \
       iputils-ping \
       netcat-openbsd \
       nfdump \
       nmap \
       procps \
       python3 \
       softflowd \
       tcpdump \
       tshark \
    && rm -rf /var/lib/apt/lists/*

CMD ["sleep", "infinity"]
