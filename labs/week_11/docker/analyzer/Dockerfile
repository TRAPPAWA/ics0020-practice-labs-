FROM debian:13-slim
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && echo 'wireshark-common wireshark-common/install-setuid boolean false' | debconf-set-selections \
 && apt-get install -y --no-install-recommends \
      ca-certificates coreutils gawk python3 sqlite3 tshark \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /work
