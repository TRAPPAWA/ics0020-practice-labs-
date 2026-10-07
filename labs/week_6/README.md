# Fluentd in Docker

**Format:** task-based, individual
**Prior Fluentd experience:** none required  
**Goal:** build and operate a small Fluentd pipeline, test normal and failed delivery paths, recover it, and decide when Fluentd is or is not the right logging tool.

This guide is written so that you can complete the lab independently on your own machine. The normal task path includes the commands, explanations, checkpoints, and troubleshooting guidance you need.

---

## 1. What you will learn

By the end of the lab you should be able to:

1. Explain Fluentd's event model: **tag + time + record**.
2. Read a Fluentd configuration and identify inputs, filters, routing, outputs, and buffers.
3. Ingest events over HTTP, from a tailed JSON file, from Docker's Fluentd logging driver, and from RFC 5424 syslog.
4. Parse, filter, enrich, route, copy, and discard events.
5. Explain what a Fluentd position file does and why deleting it can replay data.
6. Configure a disk buffer and observe retry/recovery when a downstream destination fails.
7. Distinguish **syslog the protocol** from **rsyslog the daemon/framework**.
8. Compare Fluentd with rsyslog, Fluent Bit, Vector, Logstash, and traditional syslog.
9. Identify several production concerns that this classroom stack simplifies.

The objective is to understand the pipeline and its failure modes rather than memorize configuration syntax. You should know what each section does, how events move through the pipeline, and how to verify the result.

---

## 2. Lab architecture

The lab contains these containers:

```text
                          +-----------------------+
HTTP events ------------->|                       |
                          |                       |----> stdout (debug/inspection)
JSON file ---- tail ----->|       Fluentd         |----> file output
                          |                       |----> HTTP sink (buffered)
Docker logging driver --->|  forward :24224       |
                          |                       |
RFC5424 syslog ---------->|  syslog UDP :5140     |
                          +-----------------------+
                              |        |
                              |        +---- monitor_agent :24220
                              |
                        disk state/buffers
```

Supporting services:

- `app` is a tiny HTTP application. It writes structured JSON logs to stdout **and** `/var/log/lab/app.jsonl`.
- `sink` accepts HTTP events and stores them. You will stop it on purpose to create a downstream failure.
- `toolbox` is a containerized test client. It sends HTTP events, requests to the app, syslog messages, and queries the sink/monitor endpoint.
- `docker-logger` is optional and uses Docker's **Fluentd logging driver** instead of the normal local Docker log driver.

The Fluentd configuration is mounted from:

```text
fluentd/conf/fluent.conf
```

Edit that file on your host, then restart Fluentd when a task tells you to do so.

---

## 3. Before starting

You need Docker Engine or Docker Desktop with Docker Compose v2 and a text editor. You do not need Fluentd, Ruby, Python, `curl`, `logger`, or `netcat` installed on the host.

Run all commands from the directory that contains `docker-compose.yml`.

The lab supports:

- Linux with Docker Engine and Docker Compose v2;
- macOS with Docker Desktop;
- Windows with Docker Desktop and a normal terminal such as PowerShell, Windows Terminal, or a WSL shell.

The first build may require internet access to pull the Fluentd and Python base images. After the required images are available locally, the lab itself runs on your machine and does not require external services.

Recommended available resources are about 2 CPU cores, 2 GB RAM, and 1 GB of free disk space for the lab and pulled images.

The student tasks use `docker compose` commands only. No helper scripts are required.

Work through the tasks in order because later tasks extend the configuration created earlier. Each task ends with a checkpoint. If your result differs from the checkpoint, use the troubleshooting section before moving on.

Check Docker:

```bash
docker version
docker compose version
```

Start the base stack:

```bash
docker compose up -d --build fluentd app sink
```

Check status:

```bash
docker compose ps
```

Look at Fluentd startup output:

```bash
docker compose logs --tail=40 fluentd
```

You should see Fluentd start without a configuration error.

If the stack does not start, check whether these host ports are already used:

- TCP 8080
- TCP 9000
- TCP 9880
- TCP 24220
- TCP 24224
- UDP 5514

If startup fails, inspect the container status and Fluentd logs first. Change one configuration item at a time so that you can identify the cause.

---

## 4. Fluentd basics before the tasks

No previous Fluentd experience is required for this lab. The following concepts are enough to start.

### 4.1 What Fluentd is

Fluentd is a log and event collector. It receives events, can parse or modify them, and sends them to one or more destinations.

In this lab, Fluentd is **not** the final log database or search interface. The data path is:

```text
producer -> Fluentd -> output destination
```

A producer can be an application, Docker, a file, or a syslog sender. An output destination can be stdout, a file, an HTTP service, Kafka, S3, Elasticsearch/OpenSearch, and many other systems.

### 4.2 The main configuration blocks

You will work with four ideas repeatedly:

```conf
<source>
  ...
</source>

<filter some.tag>
  ...
</filter>

<match some.tag>
  ...
</match>
```

A buffer is normally configured inside an output:

```conf
<match some.tag>
  @type http
  ...
  <buffer>
    ...
  </buffer>
</match>
```

Their roles are:

| Block | Purpose |
|---|---|
| `<source>` | Receives or reads events. |
| `<filter>` | Changes or removes matching events, then passes the remaining events onward. |
| `<match>` | Selects an output for matching events. |
| `<buffer>` | Temporarily stores output data before delivery or while retrying. |

### 4.3 `@type` selects the plugin

Inside a block, `@type` tells Fluentd which plugin to use.

Examples from this lab:

```conf
@type http
@type tail
@type grep
@type record_transformer
@type stdout
@type forward
@type syslog
```

Some are input plugins, some are filters, and some are outputs. The surrounding block tells you what role the plugin is playing.

### 4.4 Fluentd events: tag, time, record

A Fluentd event is usually described as:

```text
tag + time + record
```

Example:

```text
tag:    app.file
time:   2026-10-07T10:20:30Z
record: {"level":"error","message":"database unavailable"}
```

The **record** is the structured data. The **tag** is routing metadata. Fluentd uses the tag to decide which filters and outputs apply.

### 4.5 Tag patterns and rule order

A tag is normally split into dot-separated parts:

```text
lab.intro
lab.audit
app.file
syslog.lab.local0.info
```

Common patterns include:

```text
lab.*    # one level below lab
lab.**   # lab plus deeper descendants
**       # any tag
```

Specific rules should normally appear before broad rules. In this lab, a generic `<match **>` is kept near the end so that it does not catch events before more-specific routes can handle them.

### 4.6 A simple event path

For an HTTP event sent to `/lab.intro`, the path is approximately:

```text
HTTP request
  -> HTTP source creates tag lab.intro
  -> matching filters run, if any
  -> first matching output route is selected
  -> stdout prints the event
```

Later tasks add file parsing, Docker forwarding, syslog, fan-out, and buffering, but the same basic model remains.

### 4.7 Applying configuration changes

The configuration file is mounted from your project directory into the Fluentd container. After editing it, restart Fluentd:

```bash
docker compose restart fluentd
```

Then check for errors:

```bash
docker compose logs --tail=80 fluentd
```

A failed restart usually means the configuration has a syntax error, a missing required setting, a port conflict, or a file/permission problem. The troubleshooting section near the end of this guide covers the common cases used in the lab.

### 4.8 Quick glossary

| Term | Meaning in this lab |
|---|---|
| Event | One item moving through Fluentd: tag, time, and record. |
| Tag | Routing label such as `app.file` or `lab.audit`. |
| Record | Structured key/value payload of an event. |
| Source / input | Component that receives or reads events. |
| Filter | Component that changes or removes matching events. |
| Match / output | Rule that sends matching events to a destination. |
| Plugin | Fluentd component selected with `@type`. |
| Buffer | Temporary storage used by an output before or during delivery. |
| Chunk | A group of buffered events handled together for output. |
| Position file | State used by `tail` to remember how far it has read. |
| Forward | Fluentd's native event transport protocol. |
| Syslog | A logging protocol/message-format family; not a specific daemon. |

---

# Task 1 — First event: source, tag, record, match

## Concepts used in this task

This task introduces the minimum Fluentd pipeline: an input and an output.

The HTTP `<source>` accepts an HTTP request and creates a Fluentd event. With the HTTP input used here, the URL path becomes the tag. A `<match>` block then decides where events with that tag are sent. The `stdout` output is used so that you can inspect the event directly in the Fluentd container logs.

At this stage there are no filters and no buffer. The goal is to see how a source creates an event and how a tag selects an output.


## 1.1 Read the starter configuration

Open:

```text
fluentd/conf/fluent.conf
```

Find these elements:

- `<system>`
- an HTTP `<source>`
- a `monitor_agent` `<source>`
- `<match lab.**>`
- `<match **>`

The starter HTTP input listens on port `9880`. With Fluentd's HTTP input, the URL path becomes the event tag.

For example, sending JSON to:

```text
http://fluentd:9880/lab.intro
```

creates an event whose tag is approximately:

```text
lab.intro
```

## 1.2 Send an event

Use the toolbox:

```bash
docker compose run --rm toolbox post lab.intro --message "my first Fluentd event"
```

Now inspect Fluentd:

```bash
docker compose logs --tail=30 fluentd
```

You should see an event containing your record.

Send a few more:

```bash
docker compose run --rm toolbox post lab.intro --message "second event" --level warn
docker compose run --rm toolbox post lab.demo --message "different tag"
```

## 1.3 Identify the Fluentd event model

A Fluentd event has three conceptual parts:

```text
tag   -> routing label, e.g. lab.intro
time  -> event time
record-> key/value data, e.g. {"message":"...","level":"warn"}
```

The tag is separate routing metadata. Fluentd uses it to decide which filters and outputs apply.

## 1.4 Test wildcard matching

Predict whether these tags match `<match lab.**>`:

| Tag | Your prediction |
|---|---|
| `lab` | |
| `lab.demo` | |
| `lab.demo.api` | |
| `application.lab` | |
| `docker.lab` | |

Test your predictions with the toolbox.

Then answer:

1. What does `**` match that `*` would not?
2. Why should a broad `<match **>` normally appear after more-specific matches?
3. What would happen if `<match **>` appeared before `<match lab.**>`?

## 1.5 Query Fluentd's internal monitor endpoint

Run:

```bash
docker compose run --rm toolbox monitor
```

The response is verbose. Find evidence that the HTTP input and stdout output exist.

### Checkpoint 1

You are done when you can explain the following event path in your own words:

> An input emits an event with a tag, time, and record; filters can mutate or remove it; the first matching output route handles it.

---

# Task 2 — Tail and parse an application JSON log

## Concepts used in this task

A `tail` input follows a file as new lines are appended. Each line must then be parsed into an event. The demo application writes one JSON object per line, so Fluentd can use the JSON parser instead of extracting fields with a regular expression.

The `pos_file` stores the byte position already read from the log. Without that state, a restart could cause Fluentd either to reread old data or to lose track of where it stopped. In this lab the position file is stored on a persistent Docker volume so it survives a Fluentd container restart.

`read_from_head true` tells Fluentd what to do the first time it sees a file that has no saved position yet: begin at the start of the file instead of only reading new lines.


The demo application writes JSON lines to a shared Docker volume. Fluentd can read the same file with its built-in `tail` input.

## 2.1 Generate application logs before adding Fluentd tailing

Call several endpoints:

```bash
docker compose run --rm toolbox app-hit /
docker compose run --rm toolbox app-hit /debug
docker compose run --rm toolbox app-hit /slow
docker compose run --rm toolbox app-hit /error
```

The `/error` request returns HTTP 500, so the toolbox command may report a non-zero result. That is expected; the point is to generate an error log.

Inspect the application's raw file:

```bash
docker compose exec app sh -lc 'tail -n 8 /var/log/lab/app.jsonl'
```

Notice that each line is a complete JSON object. This is often called **JSON Lines** or **NDJSON-style logging**.

## 2.2 Add a `tail` input

Edit `fluentd/conf/fluent.conf` and add a new source **before the match rules**:

```conf
<source>
  @type tail
  @id in_app_file
  path /var/log/lab/app.jsonl
  pos_file /fluentd/state/app.pos
  tag app.file
  read_from_head true
  <parse>
    @type json
    time_key ts
    time_type string
    time_format %Y-%m-%dT%H:%M:%S.%LZ
    keep_time_key true
  </parse>
</source>
```

Restart only Fluentd:

```bash
docker compose restart fluentd
```

Check for configuration errors:

```bash
docker compose logs --tail=50 fluentd
```

Generate more application traffic:

```bash
docker compose run --rm toolbox app-hit /
docker compose run --rm toolbox app-hit /error
```

Because the catch-all `<match **>` still exists, `app.file` events should appear on Fluentd's stdout.

## 2.3 Inspect the position file

Run:

```bash
docker compose exec fluentd sh -lc 'cat /fluentd/state/app.pos || true'
```

The position file records how far Fluentd has read in the tailed file. It lets Fluentd resume after restart instead of rereading the entire file.

Answer:

1. Why is the position file stored on persistent state rather than `/tmp`?
2. What could happen if you delete it while the application log still contains old lines?
3. What problem does a position file solve that plain `tail -f` does not solve after a process restart?

## 2.4 Observe restart behavior

Record the current end of the application log:

```bash
docker compose exec app sh -lc 'wc -l /var/log/lab/app.jsonl'
```

Restart Fluentd:

```bash
docker compose restart fluentd
```

Generate one new request and inspect logs.

Did Fluentd replay every old application event? It should not, because it has the position file.

### Checkpoint 2

You are done when:

- `app.file` events are parsed into structured fields rather than one giant string;
- the event time comes from the application's `ts` field;
- you can show the position file and explain what it protects against.

---

# Task 3 — Filter, enrich, and fan out

## Concepts used in this task

A filter processes events that already exist in the pipeline. It does not receive data from the network and it does not store the final result by itself.

In this task:

- `grep` removes records that match a condition;
- `record_transformer` adds fields to records;
- the `copy` output sends one event to more than one destination.

This is also where rule order becomes important. Filters must match the event tag, and specific output routes must appear before a broad fallback route.


Now add filtering, enrichment, and multiple outputs to the pipeline.

## 3.1 Remove debug events from the `app.file` stream

Add this filter after your sources and before outputs:

```conf
<filter app.file>
  @type grep
  <exclude>
    key level
    pattern /^debug$/
  </exclude>
</filter>
```

## 3.2 Enrich remaining events

Immediately after the grep filter, add:

```conf
<filter app.file>
  @type record_transformer
  <record>
    pipeline fluentd-lab
    ingestion_source file
    event_tag ${tag}
  </record>
</filter>
```

This changes the record without changing the application that produced it.

## 3.3 Route one stream to two outputs

Add a specific match for `app.file` **before** the broad catch-all:

```conf
<match app.file>
  @type copy

  <store>
    @type stdout
  </store>

  <store>
    @type file
    path /fluentd/output/app
    append true

    <buffer time>
      timekey 5s
      timekey_wait 0s
      timekey_use_utc true
      flush_mode interval
      flush_interval 1s
    </buffer>

    <format>
      @type json
    </format>
  </store>
</match>
```

Restart Fluentd:

```bash
docker compose restart fluentd
```

Then generate a mixture:

```bash
docker compose run --rm toolbox app-hit /debug
docker compose run --rm toolbox app-hit /
docker compose run --rm toolbox app-hit /slow
docker compose run --rm toolbox app-hit /error
```

Inspect Fluentd output:

```bash
docker compose logs --tail=60 fluentd
```

Wait a few seconds and inspect generated files:

```bash
docker compose exec fluentd sh -lc 'find /fluentd/output -maxdepth 3 -type f -print'
```

Then inspect their contents:

```bash
docker compose exec fluentd sh -lc 'find /fluentd/output -maxdepth 3 -type f -print -exec tail -n 5 {} \;'
```

The exact filename is time-based and may include buffer-related naming while a chunk is being flushed.

## 3.4 Verify that filtering works

The app itself still writes debug logs. Check:

```bash
docker compose exec app sh -lc 'tail -n 10 /var/log/lab/app.jsonl'
```

Now compare with Fluentd's output.

Answer:

1. Where was the debug event discarded: producer, input, filter, or output?
2. Why might dropping noisy debug events at the collector be useful?
3. Why might it also be dangerous?
4. Does `copy` mean “load balance” or “send the same event to multiple stores”?

### Checkpoint 3

Show that:

- debug exists in the raw source file;
- debug does not continue through the `app.file` Fluentd pipeline;
- remaining records contain `pipeline`, `ingestion_source`, and `event_tag`;
- the same event reaches stdout and file output.

---

# Task 4 — Docker's Fluentd logging driver and the forward protocol

## Concepts used in this task

Docker containers normally write application logs to stdout and stderr. Docker then decides which logging driver handles those streams.

With the Fluentd logging driver, the Docker daemon sends the log records to a Fluentd `forward` input. The application itself does not need Fluentd code or a Fluentd library. The sender in this path is Docker, not the application process.

The `forward` protocol is Fluentd's native event transport. It carries event records and metadata between compatible senders and Fluentd-compatible receivers.


Docker can send a container's stdout/stderr directly to Fluentd using its Fluentd logging driver. The driver uses Fluentd's **forward** protocol.

This is different from Fluentd tailing a file.

## 4.1 Add a forward input

Add:

```conf
<source>
  @type forward
  @id in_forward
  bind 0.0.0.0
  port 24224
</source>
```

Also add a specific route before the broad catch-all:

```conf
<match docker.**>
  @type stdout
</match>
```

Restart Fluentd:

```bash
docker compose restart fluentd
```

## 4.2 Start a container whose Docker log driver is Fluentd

Run:

```bash
docker compose --profile dockerlog up -d docker-logger
```

Watch Fluentd for around 15 seconds:

```bash
docker compose logs -f fluentd
```

Stop following with Ctrl-C; that does not stop the container.

You should see events tagged `docker.lablogger`. Docker's logging driver wraps the original stdout/stderr line in a structured event and adds metadata such as container identity and source stream.

## 4.3 Compare two collection models

You have now used both:

**File tailing**

```text
application -> writes file -> Fluentd tail input -> pipeline
```

**Docker logging driver**

```text
application -> stdout/stderr -> Docker daemon -> forward protocol -> Fluentd -> pipeline
```

Answer:

1. Which design depends on the application writing a file?
2. Which design couples container startup/log delivery to the logging driver and collector availability?
3. Why does the Compose file use the driver's asynchronous connection option for this lab?
4. Which approach gives Docker-provided metadata such as container ID without parsing a log filename?
5. If you run `docker compose logs docker-logger`, what happens on your Docker version? Explain why this may differ from the default `json-file` driver experience.

Stop the log generator when you are finished:

```bash
docker compose --profile dockerlog stop docker-logger
```

### Checkpoint 4

You are done when you can describe the data path from a `print()` call inside `docker-logger` to the Fluentd stdout output.

---

# Task 5 — Buffering, retries, and a failed destination

## Concepts used in this task

An output buffer separates event collection from immediate delivery. Fluentd can place output data into buffer chunks and flush those chunks to the destination later.

A **file buffer** stores chunks on disk. If the destination is unavailable, Fluentd can keep queued chunks and retry. Because this lab mounts the buffer directory on a Docker volume, buffered data can also survive a Fluentd container restart.

A buffer is not unlimited storage and it is not an archive. If the destination remains unavailable long enough, buffer capacity and disk capacity become operational limits. Retry-based delivery can also produce duplicates if the destination receives data but the sender does not receive the acknowledgement it expected.


This task focuses on output failure and recovery. You will observe what Fluentd does when a destination becomes unavailable.

You will send a special tag, `lab.buffered`, to the HTTP sink through a **file buffer**.

## 5.1 Add a buffered HTTP output

Place this route **before `<match lab.**>`**:

```conf
<match lab.buffered>
  @type http
  endpoint http://sink:9000/events
  open_timeout 2
  read_timeout 2
  json_array true

  <format>
    @type json
  </format>

  <buffer>
    @type file
    path /fluentd/buffer/reliable
    flush_mode interval
    flush_interval 2s
    chunk_limit_size 64k
    retry_type periodic
    retry_wait 2s
    retry_forever true
  </buffer>
</match>
```

Restart Fluentd and inspect startup logs:

```bash
docker compose restart fluentd
docker compose logs --tail=50 fluentd
```

## 5.2 Healthy delivery baseline

Reset the sink:

```bash
docker compose run --rm toolbox sink-reset
```

Check count:

```bash
docker compose run --rm toolbox sink-count
```

Send five events:

```bash
docker compose run --rm toolbox post lab.buffered --message "healthy path" --count 5
```

Wait roughly 3–5 seconds, then:

```bash
docker compose run --rm toolbox sink-count
docker compose run --rm toolbox sink-tail --limit 5
```

## 5.3 Break the destination

Stop the sink:

```bash
docker compose stop sink
```

Now send 20 more events:

```bash
docker compose run --rm toolbox post lab.buffered --message "sink is down" --count 20
```

Look at Fluentd's errors/retries:

```bash
docker compose logs --tail=80 fluentd
```

Inspect buffer files:

```bash
docker compose exec fluentd sh -lc 'find /fluentd/buffer -maxdepth 2 -type f -ls'
```

The point is not the exact filenames. The point is that the events have somewhere to wait while the destination is unavailable.

## 5.4 Recover

Start the sink again:

```bash
docker compose start sink
```

Wait a few seconds, then:

```bash
docker compose run --rm toolbox sink-count
docker compose run --rm toolbox sink-tail --limit 5
```

Inspect the buffer directory again:

```bash
docker compose exec fluentd sh -lc 'find /fluentd/buffer -maxdepth 2 -type f -ls'
```

## 5.5 Reliability questions

Answer carefully:

1. Did Fluentd need the producer to resend the 20 events after the sink returned?
2. What is the advantage of a **file** buffer over a memory-only buffer if Fluentd itself restarts?
3. Is `retry_forever true` automatically a good production setting? Why not?
4. What happens if the destination is down long enough for the disk to fill?
5. Is this “exactly once” delivery? Do not claim exactly-once unless you can prove the complete producer/collector/destination acknowledgement model.
6. What should be monitored in production: only application logs, or also collector queues/buffers/retry state?

### Checkpoint 5

You are done when you can show a failed downstream request, file-buffer state, and eventual delivery after the sink returns.

---

# Task 6 — Ingest RFC 5424 syslog and compare the tools

## Concepts used in this task

Three terms must be kept separate:

- **syslog** is a protocol/message-format family used by operating systems and network devices;
- **rsyslog** is a logging daemon and processing framework that can send, receive, queue, parse, and route syslog and other data;
- **Fluentd** is a general event collector and router that can receive syslog as one of many possible inputs.

This lab uses RFC 5424-formatted messages over UDP. UDP keeps the exercise simple, but UDP does not provide delivery acknowledgement or retransmission by itself.


Syslog is common on Linux hosts, switches, routers, firewalls, hypervisors, and other infrastructure. Fluentd can ingest syslog alongside other event sources.

## 6.1 Add a syslog input

Add:

```conf
<source>
  @type syslog
  @id in_syslog
  bind 0.0.0.0
  port 5140
  tag syslog.lab
  severity_key severity
  facility_key facility
  source_address_key source_ip

  <transport udp>
  </transport>

  <parse>
    @type syslog
    message_format rfc5424
    with_priority true
  </parse>
</source>
```

Add enrichment if you want the origin visible:

```conf
<filter syslog.**>
  @type record_transformer
  <record>
    pipeline fluentd-lab
    ingestion_source syslog-rfc5424
    event_tag ${tag}
  </record>
</filter>
```

Add a route before catch-all:

```conf
<match syslog.**>
  @type stdout
</match>
```

Restart Fluentd:

```bash
docker compose restart fluentd
```

## 6.2 Send RFC 5424 events

Send an info event:

```bash
docker compose run --rm toolbox syslog --severity info --message "student syslog info"
```

Send an error event:

```bash
docker compose run --rm toolbox syslog --severity error --message "student syslog error"
```

Inspect:

```bash
docker compose logs --tail=60 fluentd
```

Look for fields such as facility, severity, host/ident/message, and for the generated tag. Depending on Fluentd's syslog input behavior, the configured tag prefix is extended with facility/severity information.

## 6.3 Important terminology

**syslog** is a protocol/message-format family and ecosystem. RFC 5424 standardizes a syslog message format and layered architecture. It is not itself “the Linux logging daemon.”

**rsyslog** is a logging daemon and processing framework. It can receive local/system logs and network syslog, parse/filter them, queue them, and forward/store them. Modern rsyslog provides substantially more functionality than the original `syslogd` model.

**Fluentd** is a general event/log collector and router. It can ingest syslog, but syslog is only one input among many.

## 6.4 Comparison matrix

Do not treat one tool as universally better. Choose based on the source, required processing, destinations, resource limits, and existing operational environment.

| Technology | What it primarily is | Strong fit | Weakness / trade-off |
|---|---|---|---|
| Syslog / RFC 5424 | Standard protocol/message format | Interoperability with OSes, network gear, appliances | A protocol is not a complete storage/processing architecture; UDP can lose data; structure is more constrained than arbitrary JSON events |
| rsyslog | High-performance logging daemon/framework | Linux/system logging, native syslog, mature queues, forwarding, TLS/RELP-style reliable transports, very high throughput | Configuration/history can feel irregular; less natural than Fluentd for some application/plugin-centric pipelines |
| Fluentd | General log/event collector and router | Heterogeneous sources/destinations, structured events, tag routing, plugin ecosystem, aggregation | Ruby-based core is heavier than lightweight agents; plugin quality varies; careless buffering/routing can lose or duplicate data |
| Fluent Bit | Lightweight telemetry agent/collector in the Fluent ecosystem | Edge nodes, containers/Kubernetes, constrained resources, high-throughput collection | Smaller transformation/plugin surface than full Fluentd in some use cases; configuration/model differs from Fluentd |
| Vector | Rust-based observability pipeline | Efficient modern agent/aggregator, logs/metrics, explicit transforms and pipeline topology | Different ecosystem and transform language; migration cost if an organization already standardized elsewhere |
| Logstash | JVM data-processing pipeline from Elastic | Deep Elastic integration, rich ETL/filtering, many integrations | Usually heavier operational footprint; often excessive for simple node-level shipping |
| syslog-ng | Syslog-focused logging daemon/framework | Network/system log collection, parsing, routing, mature syslog deployments | Similar category trade-offs to rsyslog; not automatically the best fit for every cloud-native telemetry pipeline |

### When Fluentd is a better fit than rsyslog

Fluentd is often attractive when:

- logs come from many non-syslog sources;
- records are already JSON or other structured objects;
- you need tag-oriented routing and a large plugin ecosystem;
- the collector is an application/observability integration layer rather than primarily a host syslog daemon;
- container and service logs need to feed several backends.

### When rsyslog can be the better choice

Rsyslog is often the better engineering choice when:

- the problem is fundamentally Linux/system/network syslog;
- you want a daemon already integrated with the host OS;
- very high-throughput syslog forwarding and mature queueing are central requirements;
- you need existing rsyslog rulesets/modules/operations expertise;
- adding a Ruby-based collector would solve no real problem.

Configuration style alone is not a reason to replace a working logging architecture.

### Where Fluent Bit fits

For node-level or Kubernetes collection, a common modern pattern is:

```text
Fluent Bit on many nodes -> Fluentd or another central aggregator -> storage/search backend
```

But Fluent Bit can also work as the aggregator itself. The correct choice depends on transformations, destinations, resource limits, and operational preference.

### Checkpoint 6

Explain why Fluentd and syslog are not a direct tool-to-tool comparison.

---

# Task 7 — Capstone: build a small policy

## What you are combining

The capstone uses the same ideas from the previous tasks: tag matching, enrichment, explicit discard, fan-out, buffering, and rule order. There is no new Fluentd mechanism here. The task checks whether you can assemble the pieces into one coherent policy.


Complete this using the configuration you built in the previous tasks. The student package does not include the solution files.

You are given two incoming HTTP tags:

- `lab.audit` — important records that must be enriched and sent to two destinations;
- `lab.debug` — debug records that should be discarded.

## Requirements

1. For `lab.audit`, add:

```text
pipeline = fluentd-lab
data_class = audit
event_tag = <the Fluentd tag>
```

2. Send each `lab.audit` event to:
   - stdout;
   - the HTTP sink with a file buffer and retries.

3. Explicitly discard `lab.debug` with the null output.

4. Leave the generic `<match lab.**>` route as a fallback for other lab tags.

5. Put rules in the correct order so the fallback does not swallow the specific routes.

## Test data

Reset the sink first:

```bash
docker compose run --rm toolbox sink-reset
```

Send audit events:

```bash
docker compose run --rm toolbox post lab.audit --message "audit A" --count 3
```

Send debug noise:

```bash
docker compose run --rm toolbox post lab.debug --message "please discard me" --count 3
```

Send an unrelated lab tag:

```bash
docker compose run --rm toolbox post lab.other --message "fallback route"
```

Wait for buffered flush and check:

```bash
docker compose run --rm toolbox sink-count
docker compose run --rm toolbox sink-tail --limit 10
docker compose logs --tail=80 fluentd
```

## Acceptance criteria

- Sink count increases because of `lab.audit`.
- Sink records include the enrichment fields.
- `lab.debug` does not reach the sink and does not appear through the broad fallback route.
- `lab.other` remains visible through the fallback.
- Fluentd restarts cleanly with no configuration error.

---

# 5. Production reality check

This lab is designed for learning, not for direct copy/paste into production.

Production topics you must think about include:

- Run the collector with the minimum privileges it needs. The lab uses root inside the Fluentd container solely to avoid cross-platform volume-permission trouble.
- Protect network inputs. Do not expose unauthenticated log ingestion ports to untrusted networks.
- Use TLS where transport confidentiality/integrity matters.
- Size file buffers. A “reliable” buffer that fills the disk can take the host down with it.
- Monitor Fluentd itself: input rates, output retries, buffer queue length, failed chunks, CPU/memory, and disk.
- Decide what happens under sustained backpressure: block, drop old data, reject new data, spill to disk, or route to a secondary destination.
- Define log retention separately from transport buffering. A buffer is not your archive.
- Protect secrets and personal/sensitive data. Centralizing logs can centralize your mistakes too.
- Test log rotation with `tail` and preserve position-file state.
- Pin versions and test upgrades. Plugin ecosystems are useful, but each plugin is also another dependency.
- Avoid claiming exactly-once semantics casually. Most practical logging pipelines are designed around at-most-once or at-least-once behavior at different stages.
- Separate collection from search/analytics in your mental model. Fluentd moves/processes data; Elasticsearch/OpenSearch/Loki/S3/etc. solve different problems.

---

# 6. Troubleshooting guide

## Fluentd exits immediately after editing the config

Run:

```bash
docker compose logs --tail=100 fluentd
```

Look for:

- unknown plugin/type;
- malformed `<source>`, `<filter>`, `<match>`, or nested section;
- missing required property;
- duplicate input port;
- invalid time format;
- a file path or buffer permission issue.

If the error is unclear, compare the current file with the last version that worked and review the most recent change.

## Events are visible but a filter does nothing

Check the tag. A filter only applies to matching tags.

Also check ordering: filters must be encountered before the event is consumed by an output match.

## A specific route never receives events

Look for a broader match above it, especially:

```conf
<match **>
```

or:

```conf
<match lab.**>
```

Fluentd uses match order. A broad route placed first can make a later route unreachable.

## Tail input does not reread old lines

That is usually the position file doing its job.

Inspect:

```bash
docker compose exec fluentd cat /fluentd/state/app.pos
```

Delete position state only when you intentionally want Fluentd to reread data and you understand the resulting duplication risk.

## Sink count does not rise immediately

Buffered outputs flush in chunks/intervals. Wait several seconds and inspect Fluentd retry messages.

## `docker-logger` produces no Fluentd events

Confirm:

1. Fluentd has a `forward` source on `24224`.
2. Port `24224` is published by Compose.
3. Fluentd was restarted after the config edit.
4. `docker compose --profile dockerlog ps` shows the logger running.
5. Fluentd logs do not show connection/protocol errors.

The Docker logging driver connects from the Docker daemon side, not from normal application code inside the container. That distinction matters when debugging addresses.

## Syslog messages are unmatched

Confirm that:

- the syslog source exists and listens on UDP 5140 inside the Compose network;
- the parser is configured for RFC 5424;
- your match catches `syslog.**`, because the input can append facility/severity to the tag prefix.

---

# 7. Short review questions

1. What are the three conceptual parts of a Fluentd event?
2. What is the difference between `<filter>` and `<match>`?
3. What does a tag control?
4. Why is match order important?
5. What does a tail position file store?
6. What happens to debug application logs in your Task 3 pipeline?
7. What is the role of `copy`?
8. What is the difference between file tailing and Docker's Fluentd logging driver?
9. Why use a file buffer?
10. What can still go wrong even with a file buffer?
11. Is syslog a daemon?
12. Name one case where rsyslog is a better fit than Fluentd.
13. Name one case where Fluent Bit is a better fit than full Fluentd.
14. Why is an HTTP sink in this lab useful even though nobody would call it a real log analytics platform?
15. Which part of the pipeline would you monitor first if the downstream destination became slow?

---

# 8. References

These are primary or upstream references for the features used in the lab.

- Fluentd configuration syntax: https://docs.fluentd.org/configuration/config-file
- Fluentd Docker image: https://docs.fluentd.org/container-deployment/install-by-docker
- Fluentd Docker Compose guidance: https://docs.fluentd.org/container-deployment/docker-compose
- HTTP input: https://docs.fluentd.org/input/http
- Tail input: https://docs.fluentd.org/input/tail
- Syslog input: https://docs.fluentd.org/input/syslog
- Input plugin overview: https://docs.fluentd.org/input/
- Grep filter: https://docs.fluentd.org/filter/grep
- Parser filter: https://docs.fluentd.org/filter/parser
- Buffer configuration: https://docs.fluentd.org/configuration/buffer-section
- Buffer concepts: https://docs.fluentd.org/buffer/
- HTTP output: https://docs.fluentd.org/output/http
- Output plugin overview: https://docs.fluentd.org/output/
- Docker Fluentd logging driver: https://docs.docker.com/engine/logging/drivers/fluentd/
- RFC 5424, The Syslog Protocol: https://www.rfc-editor.org/rfc/rfc5424
- rsyslog official documentation: https://docs.rsyslog.com/doc/
- rsyslog queue concepts: https://docs.rsyslog.com/doc/concepts/queues.html
- Fluent Bit manual: https://docs.fluentbit.io/manual
- Fluentd vs Fluent Bit overview: https://docs.fluentbit.io/manual/about/fluentd-and-fluent-bit
- Vector pipeline components: https://vector.dev/docs/reference/configuration/pipeline-components/
- Logstash getting started: https://www.elastic.co/docs/reference/logstash/getting-started-with-logstash

---

# 9. Cleanup

When you are finished with the lab:

```bash
docker compose --profile dockerlog down -v --remove-orphans
```

The `-v` matters: it removes lab volumes containing the application log, Fluentd position state, buffers, outputs, and sink data.
