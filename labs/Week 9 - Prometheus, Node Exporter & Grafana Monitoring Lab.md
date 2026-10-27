# Week 9 - Prometheus, Node Exporter & Grafana Monitoring Lab

A hands-on guide to setting up a sample Flask application and monitoring the host and Nginx using **Prometheus**, **Node Exporter**, **Grafana**, and **Nginx Prometheus Exporter**.

## Component versions

| Component | Version |
| --- | --- |
| Python | `3.14` |
| Redis | `8.10` |
| Prometheus | `v3.15.1` |
| Node Exporter | `v1.12.1` |
| Grafana | `13.2.4` |
| Nginx Prometheus Exporter | `1.5.3` |

## Contents

- [1. Sample application](#1-sample-application)
- [2. Prometheus and Node Exporter](#2-prometheus-and-node-exporter)
- [3. Explore Prometheus metrics](#3-explore-prometheus-metrics)
- [4. Add Grafana](#4-add-grafana)
- [5. Monitor Nginx](#5-monitor-nginx)
- [6. Clean up](#6-clean-up)

---

## 1. Sample application

### Create the project directory

```bash
mkdir composetest
cd composetest
```

### Create `app.py`

```bash
vim app.py
```

```python
import time
import redis
from flask import Flask

app = Flask(__name__)
cache = redis.Redis(host='redis', port=6379)

def get_hit_count():
    retries = 5
    while True:
        try:
            return cache.incr('hits')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)

@app.route('/')
def hello():
    count = get_hit_count()
    return 'Hello World! I have been seen {} times.\n'.format(count)
```

### Create `requirements.txt`

```bash
vim requirements.txt
```

```text
flask
redis
```

### Create the `Dockerfile`

```bash
vim Dockerfile
```

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.14-alpine
WORKDIR /code
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000
COPY . .
CMD ["flask", "run"]
```

### Define the Compose services

The `version:` field is no longer needed in a Compose file.

```bash
vim compose.yaml
```

```yaml
services:
  web:
    build: .
    ports:
      - "8002:5000"
  redis:
    image: "redis:8.10.2-alpine"
```

### Build and start the sample app

```bash
docker compose up -d --build
```

Expected output:

```text
 ✔ Image composetest-web        Built
 ✔ Network composetest_default  Created
 ✔ Container composetest-redis-1  Started
 ✔ Container composetest-web-1    Started
```

Check that both containers are running, then inspect their logs:

```bash
docker compose ps
docker compose logs
```

Open `http://192.168.180.X:8002/` in a browser. Refresh a few times to see the Redis-backed counter increase.

```bash
curl http://localhost:8002/
```

Example response:

```text
Hello World! I have been seen 1 times.
```

## 2. Prometheus and Node Exporter

### Create the monitoring directory

```bash
cd
mkdir monitoring
cd monitoring
```

### Create the initial Compose configuration

```bash
vim docker-compose.yml
```

```yaml
networks:
  monitoring:
    driver: bridge

volumes:
  prometheus_data: {}

services:
  node-exporter:
    image: prom/node-exporter:v1.12.1
    container_name: node-exporter
    restart: unless-stopped
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    expose:
      - 9100
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:v3.15.1
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    ports:
      - 9090:9090
    networks:
      - monitoring
```

> [!NOTE]
> Older versions of this lab also passed `--web.console.libraries` and `--web.console.templates`. Those flags were removed in Prometheus 3; the container will not start if you keep them.

### Create `prometheus.yml`

```bash
vim prometheus.yml
```

```yaml
global:
  scrape_interval: 1m

scrape_configs:
  - job_name: 'prometheus'
    scrape_interval: 1m
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

### Start monitoring

```bash
docker compose up -d
```

Check that both containers are **Up**. If Prometheus keeps restarting, inspect its logs with `docker logs prometheus`:

```bash
docker compose ps
```

### Open Prometheus

`http://192.168.180.X:9090`

Go to **Status -> Target health**. Both **prometheus** and **node** should be **UP**.

## 3. Explore Prometheus metrics

Run the following queries in Prometheus:

### Memory usage (%)

```promql
((1-(node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes))*100)
```

### CPU usage (%)

```promql
100 - avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100
```

### Disk usage (%)

```promql
100 - ((node_filesystem_avail_bytes{mountpoint="/",fstype!="rootfs"} * 100) / node_filesystem_size_bytes{mountpoint="/",fstype!="rootfs"})
```

### System load

```promql
node_load1
```

### Network traffic

```promql
irate(node_network_transmit_bytes_total{device="eth0"}[5m])*8
irate(node_network_receive_bytes_total{device="eth0"}[5m])*8
```

> [!NOTE]
> Node Exporter runs inside a container, so `eth0` is the container network interface. To see all interfaces, use `node_network_receive_bytes_total{device!="lo"}`.

> [!TIP]
> The scrape interval is `1m`, so wait a couple of minutes before `rate()` / `irate()` queries return data.

## 4. Add Grafana

### Extend `docker-compose.yml` with Grafana

```bash
vim docker-compose.yml
```

```yaml
networks:
  monitoring:
    driver: bridge

volumes:
  prometheus_data: {}
  grafana_data: {}

services:
  node-exporter:
    image: prom/node-exporter:v1.12.1
    container_name: node-exporter
    restart: unless-stopped
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    expose:
      - 9100
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:v3.15.1
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    ports:
      - 9090:9090
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:13.2.4
    container_name: grafana
    restart: unless-stopped
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - 3000:3000
    networks:
      - monitoring
```

### Start the updated stack

```bash
docker compose up -d
```

### Open Grafana and configure Prometheus

Open Grafana. The default login is `admin` / `admin`; you will be prompted to set a new password.

`http://192.168.180.X:3000`

Add **Prometheus** as a data source:

`http://192.168.180.X:3000/connections/datasources/new`

Select Prometheus and enter its address in the **Prometheus server URL** field. Grafana and Prometheus share the Docker network, so use the container name:

`http://prometheus:9090`

> [!NOTE]
> `http://192.168.180.X:9090` also works because port `9090` is published on the host.

Click **Save & test**. You should see **Successfully queried the Prometheus API.**

### Import the Node Exporter dashboard

`http://192.168.180.X:3000/dashboard/import`

Use the [Node Exporter Full dashboard](https://grafana.com/grafana/dashboards/1860-node-exporter-full/) and enter this dashboard ID:

`1860`

Click **Load**, select the Prometheus data source, and click **Import**.

## 5. Monitor Nginx

### Install Nginx

```bash
sudo apt-get update
sudo apt-get install -y nginx
```

### Expose the Nginx status endpoint

```bash
sudo vim /etc/nginx/conf.d/status.conf
```

```nginx
server {
    listen 8081;

    server_name _;

    location /metrics {
        stub_status on;
    }
}
```

Test the Nginx configuration and restart the service:

```bash
sudo nginx -t
sudo systemctl restart nginx.service
```

Check the status endpoint:

```bash
curl http://localhost:8081/metrics
```

Example output:

```text
Active connections: 1
server accepts handled requests
 11 11 11
Reading: 0 Writing: 1 Waiting: 0
```

### Add Nginx Prometheus Exporter

```bash
vim docker-compose.yml
```

```yaml
networks:
  monitoring:
    driver: bridge

volumes:
  prometheus_data: {}
  grafana_data: {}

services:
  node-exporter:
    image: prom/node-exporter:v1.12.1
    container_name: node-exporter
    restart: unless-stopped
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    expose:
      - 9100
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:v3.15.1
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    ports:
      - 9090:9090
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:13.2.4
    container_name: grafana
    restart: unless-stopped
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - 3000:3000
    networks:
      - monitoring

  nginx_exporter:
    image: nginx/nginx-prometheus-exporter:1.5.3
    container_name: nginx_exporter
    restart: unless-stopped
    # host.docker.internal = the machine running docker (where nginx is installed)
    extra_hosts:
      - "host.docker.internal:host-gateway"
    command:
      - '--nginx.scrape-uri=http://host.docker.internal:8081/metrics'
    ports:
      - 9113:9113
    networks:
      - monitoring
```

> [!NOTE]
> Nginx Prometheus Exporter 1.x requires the double-dash `--nginx.scrape-uri` flag. The old single-dash `-nginx.scrape-uri` form no longer works. You can also use your VM IP: `--nginx.scrape-uri=http://192.168.180.X:8081/metrics`.

### Add Nginx to Prometheus scrape targets

```bash
vim prometheus.yml
```

```yaml
global:
  scrape_interval: 1m

scrape_configs:
  - job_name: 'prometheus'
    scrape_interval: 1m
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'nginx'
    scrape_interval: 5s
    static_configs:
      - targets: ['nginx_exporter:9113']
```

Start the new exporter and restart Prometheus to load its updated configuration:

```bash
docker compose up -d
docker compose restart prometheus
```

Verify the exporter works. `nginx_up 1` means it can read the Nginx status page:

```bash
curl -s http://localhost:9113/metrics | grep nginx_up
```

The **nginx** target should now also show **UP** in Prometheus under **Status -> Target health**.

### Import the Nginx dashboard and generate traffic

`http://192.168.180.X:3000/dashboard/import`

Use the [Nginx dashboard](https://grafana.com/grafana/dashboards/12708-nginx/) with this dashboard ID:

`12708`

Click **Load**, select the Prometheus data source, and click **Import**.

> [!NOTE]
> This older dashboard uses legacy **Graph** and **Singlestat** panels; Grafana automatically converts them to **Time series** and **Stat** panels when you open it.

Generate some traffic so the graphs start moving:

```bash
for i in $(seq 1 100); do curl -s http://localhost/ > /dev/null; done
```

## 6. Clean up

```bash
docker compose down
```
