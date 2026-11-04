FROM python:3.14-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/lab
COPY server.py /opt/lab/server.py

EXPOSE 8080 9000 9999/udp
CMD ["python3", "/opt/lab/server.py"]