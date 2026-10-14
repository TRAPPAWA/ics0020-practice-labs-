# Student Lab - syslog-ng in Docker

**Prior syslog-ng experience:** not required  
**Prerequisite:** basic Docker familiarity and the previous logging/Fluentd material

This lab is self-contained. You can complete the practical work on your own machine without a local syslog-ng installation. The supplied Docker stack includes the server, a second collector, test clients, and traffic generators.

---

# Part A - Theory and preparation

## 1. Learning outcomes

By the end of the session you should be able to:

1. Distinguish **syslog as a protocol/message family** from **syslog-ng as an implementation and processing framework**.
2. Explain the practical differences between BSD-style/RFC3164 syslog and IETF/RFC5424 syslog.
3. Calculate a syslog `PRI` value from facility and severity.
4. Read a syslog-ng configuration and identify sources, destinations, filters, templates, rewrites, parsers, and log paths.
5. Build network sources for UDP and TCP syslog.
6. Route messages by facility, severity, program, and message content.
7. Use macros such as `${HOST}`, `${SOURCEIP}`, `${FACILITY}`, `${LEVEL}`, `${PROGRAM}`, and `${R_ISODATE}`.
8. Rewrite message fields before forwarding or storage.
9. Use a dynamic file path based on message metadata.
10. Explain flow-control and disk buffering, including what they can and cannot guarantee.
11. Test all of the above in Docker using generated traffic.

---

## 2. What syslog-ng is

`syslog-ng` is a logging daemon and log-processing framework. It can receive messages, parse them, filter them, rewrite fields, format them, store them, and forward them to other systems.

A simple pipeline looks like this:

```text
source -> optional filter/parser/rewrite -> destination
             \__________________________/
                     log path
```

A configuration can have many sources, many destinations, and many log paths. The same source or filter can be reused in several paths.

This is close to what you already saw with Fluentd, but the configuration model and the syslog-specific concepts are different.

### 2.1 Bridge from Fluentd

A rough mapping is:

| Fluentd | syslog-ng | Comment |
|---|---|---|
| `<source>` | `source { ... };` | Where events enter. |
| `<filter>` | `filter`, `parser`, `rewrite` | syslog-ng separates these concerns more explicitly. |
| `<match>` / output | `destination` + `log` | A destination defines where to send; a log path connects pieces. |
| tag-based routing | fields, filters, log paths | syslog-ng commonly routes by facility, severity, host, program, source IP, or message content. |
| buffer in output | destination queue / `disk-buffer()` | Same broad reliability problem, different configuration model. |

---

## 3. Syslog is not rsyslog and it is not syslog-ng

These names are easy to mix up:

- **syslog** refers to a family of message formats and transport conventions used for system and application logging.
- **rsyslog** is a logging daemon/framework that implements syslog and many additional inputs, outputs, queues, parsers, and filters.
- **syslog-ng** is another logging daemon/framework with similar responsibilities and a different configuration language and feature set.
- **Fluentd** is a more general event/log collector. It handles syslog but is not centered on the traditional syslog data model.

When someone says "the syslog server", you still need to know which implementation and which message format/transport they mean.

---

## 4. Syslog message basics

### 4.1 Facility and severity

Traditional syslog encodes two values in the priority field:

```text
PRI = facility_number * 8 + severity_number
```

Common severity values:

| Severity | Number | Meaning |
|---|---:|---|
| `emerg` | 0 | system unusable |
| `alert` | 1 | immediate action required |
| `crit` | 2 | critical condition |
| `err` | 3 | error |
| `warning` | 4 | warning |
| `notice` | 5 | normal but significant |
| `info` | 6 | informational |
| `debug` | 7 | debug information |

Common facility values used in this lab:

| Facility | Number | Typical use |
|---|---:|---|
| `user` | 1 | user-level messages |
| `mail` | 2 | mail subsystem |
| `daemon` | 3 | system daemons |
| `authpriv` | 10 | security/authentication |
| `cron` | 9 | scheduled jobs |
| `local0` ... `local7` | 16 ... 23 | locally defined use |

Example:

```text
daemon.debug
facility = 3
severity = 7
PRI = 3 * 8 + 7 = 31
```

The wire message starts with `<31>`.

You can verify values using the toolbox:

```bash
docker compose run --rm toolbox pri --facility daemon --severity debug
```

### 4.2 BSD-style / RFC3164 message

A typical legacy message looks like:

```text
<31>Oct 14 12:00:00 myhost sshd[3179]: This is a test
```

Important properties:

- compact and widely supported;
- commonly sent over UDP, although TCP is also used;
- no year in the traditional timestamp;
- fewer standardized structured fields;
- sender-provided `HOST` and program information can be parsed by the receiver.

### 4.3 IETF / RFC5424 message

A simplified RFC5424 message looks like:

```text
<134>1 2026-10-14T12:00:00Z api01 api 1234 LAB42 [lab@32473 env="docker"] request completed
```

It includes explicit fields for:

- version;
- timestamp;
- hostname;
- application/program;
- process ID;
- message ID;
- structured data;
- message body.

RFC5424 is a better fit when you need a standardized structured syslog representation.

### 4.4 UDP, TCP, and TLS are separate choices

The message format and transport are separate concerns.

**UDP** is simple and cheap, but there is no connection and no retransmission at the application level. A sender can transmit a datagram and never know whether the receiver processed it.

**TCP** is connection-oriented. Lost IP packets are retransmitted by TCP and broken connections can be detected. This makes it a better default for reliable forwarding, although TCP alone does not provide exactly-once application delivery.

**TLS** normally runs over TCP and adds encryption plus certificate-based identity/trust decisions.

---

## 5. The syslog-ng configuration model

A modern configuration begins with a version line:

```conf
@version: 4.12
@include "scl.conf"
```

The main object types used in this lab are:

```conf
source s_name {
    ...
};

filter f_name {
    ...
};

parser p_name {
    ...
};

rewrite r_name {
    ...
};

template t_name {
    ...
};

destination d_name {
    ...
};

log {
    source(s_name);
    filter(f_name);
    rewrite(r_name);
    destination(d_name);
};
```

A `log` statement is the path that connects the processing objects.

### 5.1 Sources

A source defines where messages enter syslog-ng.

Examples:

```conf
source s_udp {
    network(transport(udp) port(514));
};
```

```conf
source s_tcp {
    network(transport(tcp) port(1514));
};
```

In current syslog-ng documentation:

- `network()` is the normal driver for BSD/RFC3164-style network syslog;
- `syslog()` is the driver used for the IETF syslog protocol and can use UDP, TCP, or TLS;
- older `udp()` and `tcp()` aliases exist for compatibility but should not be your default for new configuration.

### 5.2 Destinations

A destination defines where a message goes.

File example:

```conf
destination d_example {
    file("/var/log/lab/example.log");
};
```

Network example:

```conf
destination d_remote {
    network("collector" transport(tcp) port(1601));
};
```

A destination definition by itself does nothing. A `log` path must connect a source to it.

### 5.3 Log paths

A basic path:

```conf
log {
    source(s_udp);
    destination(d_example);
};
```

A filtered path:

```conf
log {
    source(s_udp);
    filter(f_auth);
    destination(d_secure);
};
```

If a log path has several filters, a message must pass all of them unless the Boolean expression inside a filter says otherwise.

---

## 6. Fields and macros

syslog-ng parses incoming messages into fields. Templates and dynamic file names can refer to those fields with macros.

Important macros for this lab:

| Macro | Meaning |
|---|---|
| `${HOST}` | hostname contained in the message, depending on hostname settings |
| `${SOURCEIP}` | IP address of the network peer that actually sent the message |
| `${FACILITY}` | textual facility |
| `${LEVEL}` | textual severity |
| `${PRI}` | numeric priority |
| `${PROGRAM}` | application/program name |
| `${PID}` | process ID if available |
| `${MESSAGE}` | message body |
| `${R_ISODATE}` | reception time at syslog-ng in ISO form |
| `${R_YEAR}`, `${R_MONTH}`, `${R_DAY}` | reception date components |
| `${SDATA}` | RFC5424 structured data |

`HOST` and `SOURCEIP` are not the same thing.

Example:

```text
message says HOST=web01
actual TCP peer SOURCEIP=172.21.0.7
```

That distinction is important when logs pass through relays or when sender-provided hostnames cannot be trusted.

### 6.1 Message time vs reception time

Date macros without an `R_` prefix normally refer to the message timestamp. `R_` macros refer to the time the receiver got the message.

That difference matters when:

- a sender clock is wrong;
- messages were buffered and arrive late;
- you want directory names based on ingestion time rather than event time.

---

## 7. Templates

A template controls output formatting.

Example:

```conf
template t_short {
    template("${R_ISODATE} ${HOST} ${PROGRAM}: ${MESSAGE}\n");
};
```

Attach it to a destination:

```conf
destination d_example {
    file("/var/log/lab/example.log" template(t_short));
};
```

Templates can also be used in file names:

```conf
file("/var/log/lab/${HOST}/${R_YEAR}${R_MONTH}${R_DAY}.log")
```

If the expanded path can create new directories, you normally need `create-dirs(yes)`.

---

## 8. Filters

Filters decide whether a message continues through a log path.

Examples:

```conf
filter f_mail {
    facility(mail);
};
```

```conf
filter f_sshd {
    program('^sshd$');
};
```

```conf
filter f_error_words {
    match('critical|fatal' value("MESSAGE") flags(ignore-case));
};
```

Filters can use Boolean operators:

```text
and
or
not
```

Severity ranges are useful. In syslog terminology, "info or more severe" means:

```conf
level(info..emerg)
```

Remember that smaller severity numbers are more severe.

---

## 9. Rewrite rules

A rewrite changes a field before later parts of the log path process the message.

Set a field:

```conf
rewrite r_example {
    set("new-program", value("PROGRAM"));
};
```

Change syslog priority components with dedicated functions:

```conf
set-facility("user");
set-severity("alert");
```

The order in the log path matters:

```text
source -> filter -> rewrite -> destination
```

A destination template sees the rewritten values if the rewrite appears before the destination.

---

## 10. Parsers

Parsers extract structure from message content and create fields that can be used later by filters, templates, or destination file names.

The supplied reference material shows examples using `csv-parser()` and `regexp-parser()` to derive fields from an IP address.

You will not build a custom parser in the core practical tasks because the session focuses on routing, rewriting, remote collection, and reliability. Parser work is a suitable extension once the basic configuration model is solid.

---

## 11. Reliability: queues, flow-control, and disk buffers

A logging pipeline can fail downstream. The collector might be unreachable, slow, or restarted.

### 11.1 Flow-control

With flow-control, syslog-ng can stop reading from an input when the downstream path cannot keep up.

Conceptually:

```text
source -> processing -> destination queue -> destination
  ^                            |
  |------ slow/stop input -----|
```

This is useful with connection-oriented sources such as TCP, where slowing the read side can apply backpressure to the sender.

UDP has a hard limitation: the sender keeps sending datagrams whether the receiver is ready or not. Backpressure cannot travel back through a connection that does not exist.

### 11.2 Disk buffer

A destination can use a disk buffer so messages wait on disk when the destination is unavailable.

Current syslog-ng uses configuration such as:

```conf
disk-buffer(
    reliable(yes)
    capacity-bytes(...)
    dir("...")
)
```

`reliable(yes)` improves crash/restart resilience at some performance cost.

Do not translate this into "exactly once". Network logging can still produce duplicates or lose messages in failure windows depending on the protocol, sender behavior, queue limits, and acknowledgement semantics.

---

## 12. TLS in one page

For a TLS source the server needs a certificate and private key. The client must decide whether and how to verify the server certificate.

A simplified server source looks like:

```conf
source s_tls {
    syslog(
        transport(tls)
        port(6514)
        tls(
            key-file("...")
            cert-file("...")
        )
    );
};
```

This lab includes a small lab CA plus a server certificate and private key for the optional task. They are intentionally shared lab credentials and must never be reused outside the exercise.

---

## 13. Comparison: syslog-ng, rsyslog, Fluentd, Fluent Bit

| Area | syslog-ng | rsyslog | Fluentd | Fluent Bit |
|---|---|---|---|---|
| Traditional syslog role | Strong | Strong | Supported, not its center | Supported |
| RFC3164 / RFC5424 | Native focus | Native focus | Via plugins | Via input/parser support |
| System daemon replacement | Yes | Yes | Usually no | Usually no |
| Rich routing/filtering | Yes | Yes | Yes | Yes, lighter model |
| Structured event pipelines | Yes | Yes | Strong | Strong |
| Plugins/integrations | Broad | Broad | Very broad | Broad |
| Resource profile | Moderate | Often efficient | Heavier Ruby runtime | Lightweight |
| Common placement | host/relay/server | host/relay/server | aggregator/collector | node/edge/sidecar |

### 13.1 When syslog-ng is a good choice

- replacing or extending a system syslog daemon;
- receiving logs from network appliances that speak syslog;
- building centralized syslog relays and servers;
- routing by facility/severity/host/program;
- TLS forwarding between syslog endpoints;
- normalizing or rewriting syslog fields before storage or forwarding.

### 13.2 When Fluentd may be the better fit

- a pipeline is primarily structured application events rather than classic syslog;
- you need a particular Fluentd plugin/integration;
- tag-based routing is already standard in the platform;
- you are building a broader event-collection layer rather than a syslog service.

### 13.3 When Fluent Bit may be the better fit

- you need a smaller agent on many nodes or containers;
- edge resource usage matters more than having a larger processing framework locally.

### 13.4 syslog-ng vs rsyslog

There is no universal winner. Both can be high-performance, reliable syslog daemons with advanced processing. The decision often depends on existing configuration, team knowledge, packaging, required modules, and operational history.

---

# Part B - Practical lab

## 14. Lab architecture

```text
                 manual toolbox messages
                         |
                         v
              +---------------------+
              |      syslog-ng      |
 UDP 514 ---->|                     |----> files under ./output/main
 TCP 1514 --->|  student config     |
              |                     |----> TCP 1601 + disk buffer
              +---------------------+              |
                    ^      ^      ^                 v
                    |      |      |          +---------------+
                    |      |      +----------|   collector   |
                    |      |                 | fixed config  |
                    |      |                 +---------------+
                    |      |                         |
             traffic-web traffic-auth          alerts.log
                    |
               traffic-batch

Optional:
 RFC5424 UDP 8514 ------> syslog-ng
 RFC5424 TLS 6514 ------> syslog-ng
```

The traffic containers generate realistic-looking messages from separate Docker source IPs. That lets you test `${SOURCEIP}` without additional virtual machines.

---

## 15. Start the stack

You need Docker Engine or Docker Desktop with Compose v2 and a text editor.

Check Docker:

```bash
docker version
docker compose version
```

From the directory containing `docker-compose.yml`:

```bash
docker compose up -d --build syslog-ng collector
```

Check containers:

```bash
docker compose ps
```

Check syslog-ng startup:

```bash
docker compose logs --tail=40 syslog-ng
```

The starter configuration only handles syslog-ng's own internal messages. The network sources are your first task.

Open:

```text
syslog-ng/conf/syslog-ng.conf
```

### Configuration workflow for every task

After editing:

1. validate syntax;
2. restart syslog-ng;
3. inspect startup logs;
4. send a controlled test message;
5. inspect the expected output;
6. only then move on.

Validation:

```bash
docker compose run --rm --no-deps syslog-ng --no-caps -s
```

Restart:

```bash
docker compose restart syslog-ng
```

Logs:

```bash
docker compose logs --tail=60 syslog-ng
```

A syntax-valid configuration can still be logically wrong. The test message is part of the configuration process, not an optional final check.

---

# Task 1 - Build the first network pipeline

## Goal

Receive BSD-style syslog over:

- UDP port `514` inside the container;
- TCP port `1514` inside the container, with up to 200 connections.

Write both sources to:

```text
/var/log/lab/all.log
```

Use a template that includes at least:

```text
reception timestamp
SOURCEIP
HOST
FACILITY
LEVEL
PROGRAM
PID
MESSAGE
```

## What you need to write

You need:

- two `source` objects;
- one `template`;
- one file `destination`;
- one `log` path that connects both sources to the destination.

### Hint 1 - a UDP source

```conf
source s_bsd_udp {
    network(transport(udp) port(514));
};
```

Write the TCP source yourself. Add:

```text
transport(tcp)
port(1514)
max-connections(200)
```

### Hint 2 - template syntax

The structure is:

```conf
template t_name {
    template("...macros here...\n");
};
```

Useful macros are listed in Section 6.

### Hint 3 - file destination

Start from:

```conf
destination d_all {
    file(
        "/var/log/lab/all.log"
        create-dirs(yes)
        perm(0644)
        template(t_main)
    );
};
```

You still need to define `t_main` and connect the sources to the destination.

## Test 1 - UDP

```bash
docker compose run --rm toolbox send-bsd \
  --transport udp \
  --facility daemon \
  --severity debug \
  --host app01 \
  --program sshd \
  --pid 3179 \
  --message "This is a test"
```

## Test 2 - TCP

```bash
docker compose run --rm toolbox send-bsd \
  --transport tcp \
  --facility authpriv \
  --severity notice \
  --host auth01 \
  --program sshd \
  --message "login failure for user test"
```

Inspect:

```bash
docker compose exec syslog-ng tail -n 10 /var/log/lab/all.log
```

or open:

```text
output/main/all.log
```

## Checkpoint

You should see both messages. Your output must make it possible to distinguish:

- `SOURCEIP` from `HOST`;
- facility from severity;
- program from message text.

## Questions

1. Why is the Docker source IP different from `app01` or `auth01`?
2. What PRI value did the first test use? Confirm it from the toolbox output.
3. If the UDP packet were lost before reaching syslog-ng, which part of this configuration would retry it?

---

# Task 2 - Recreate traditional facility routing

This task is adapted from the supplied syslog-ng framework exercise. In the original host-based task, syslog-ng replaces a local rsyslog daemon. In this Docker lab, do not stop or change your host logging service. We simulate the same routing rules using network messages.

## Goal

Route messages as follows:

| Condition | Destination |
|---|---|
| facility `mail` | `/var/log/lab/maillog` |
| facility `cron` | `/var/log/lab/cron` |
| facility `authpriv` | `/var/log/lab/secure` |
| `info` or more severe, excluding the three facilities above | `/var/log/lab/messages` |

Keep the Task 1 `all.log` path as a general observation file.

## What you need to write

- four filters;
- four file destinations;
- four log paths.

You may reuse `t_main` from Task 1.

### Hint 1 - one facility filter

```conf
filter f_mail {
    facility(mail);
};
```

Create the `cron` and `authpriv` versions yourself.

### Hint 2 - severity range

"info or more severe" is:

```conf
level(info..emerg)
```

Your general filter must also exclude `mail`, `cron`, and `authpriv`.

The Boolean shape is:

```text
severity condition AND NOT (facility A OR facility B OR facility C)
```

### Hint 3 - connect filter to destination

```conf
log {
    source(...);
    source(...);
    filter(...);
    destination(...);
};
```

Both UDP and TCP messages should be eligible.

## Test set

Send a mail message:

```bash
docker compose run --rm toolbox send-bsd \
  --transport udp --facility mail --severity info \
  --host mail01 --program postfix --message "queued message LAB001"
```

Send an auth message:

```bash
docker compose run --rm toolbox send-bsd \
  --transport tcp --facility authpriv --severity notice \
  --host auth01 --program sshd --message "failed password for student"
```

Send a cron message:

```bash
docker compose run --rm toolbox send-bsd \
  --transport udp --facility cron --severity info \
  --host batch01 --program cron --message "nightly job completed"
```

Send a normal daemon info message:

```bash
docker compose run --rm toolbox send-bsd \
  --transport tcp --facility daemon --severity info \
  --host api01 --program api --message "service started"
```

Send a daemon debug message:

```bash
docker compose run --rm toolbox send-bsd \
  --transport tcp --facility daemon --severity debug \
  --host api01 --program api --message "debug details"
```

Inspect:

```bash
docker compose exec syslog-ng sh -c \
  'for f in maillog cron secure messages; do echo "--- $f"; tail -n 5 /var/log/lab/$f 2>/dev/null || true; done'
```

## Checkpoint

- mail appears in `maillog`;
- cron appears in `cron`;
- authpriv appears in `secure`;
- daemon info appears in `messages`;
- daemon debug does **not** appear in `messages`;
- all five messages can still appear in `all.log` because that broad observation path remains.

## Questions

1. Why is `debug` excluded by `level(info..emerg)`?
2. Why explicitly exclude mail/cron/authpriv from the general filter if they already have dedicated log paths?
3. Is duplicate storage always wrong? Give one case where keeping both `all.log` and specialized files is useful.

---

# Task 3 - Detect Firefox traffic and rewrite the program field

This task is also adapted from the supplied framework exercise.

A simulated Apache access-log line arrives inside a syslog message with `PROGRAM=apache`. If it represents a Firefox browser, you will:

1. detect it;
2. rewrite `PROGRAM` to `firefox`;
3. write it to a date-based file.

## Goal

Firefox events should be written to a file such as:

```text
/var/log/lab/firefox-20261014.log
```

An Internet Explorer sample must not be written there.

## Step 1 - inspect the two messages before writing the filter

Firefox:

```bash
docker compose run --rm toolbox apache --browser firefox
```

IE sample:

```bash
docker compose run --rm toolbox apache --browser ie
```

Inspect `all.log` and identify:

- `PROGRAM`;
- the browser string inside `${MESSAGE}`.

## Step 2 - write the filter

You need both conditions:

```text
PROGRAM is exactly apache
AND
MESSAGE contains Firefox
```

Useful pieces:

```conf
program('^apache$')
message('Firefox')
```

Combine them in one filter object.

## Step 3 - rewrite `PROGRAM`

The rewrite syntax is:

```conf
rewrite r_name {
    set("new-value", value("PROGRAM"));
};
```

Set it to:

```text
firefox
```

## Step 4 - dynamic destination

You can use reception-date macros in a file name:

```text
${R_YEAR}
${R_MONTH}
${R_DAY}
```

Create a destination whose file path begins with:

```text
/var/log/lab/firefox-
```

Use a short template that clearly prints the rewritten `${PROGRAM}`.

## Step 5 - log path order

The path should be:

```text
source -> filter -> rewrite -> destination
```

## Test

Send one Firefox and one IE event again.

List matching files:

```bash
docker compose exec syslog-ng sh -c 'ls -l /var/log/lab/firefox-* 2>/dev/null || true'
```

Read the file:

```bash
docker compose exec syslog-ng sh -c 'tail -n 10 /var/log/lab/firefox-* 2>/dev/null || true'
```

## Checkpoint

- Firefox message appears in the date-based file;
- the output says program `firefox`, not `apache`;
- IE sample does not appear there.

## Questions

1. Why filter before rewriting instead of rewriting every Apache message?
2. Would the same event still appear as `apache` in `all.log`? Test it. Why can two log paths see different versions of the same incoming message?
3. What is the operational difference between changing the program field and merely changing the output file name?

---

# Task 4 - Simulate multiple remote hosts and organize logs by sender IP

The supplied framework exercise asks you to receive remote messages and store them in directories by sender IP. The Docker stack gives you three independent traffic containers so this can be tested on one machine.

## Goal

Create a destination that writes to:

```text
/var/log/lab/by-ip/${SOURCEIP}/events.log
```

Use the main template from Task 1.

The destination must create missing directories.

## Hint

A file destination may contain macros in the path:

```conf
file(
    "/var/log/lab/by-ip/${SOURCEIP}/events.log"
    create-dirs(yes)
    ...
)
```

You need a log path from both BSD network sources to this destination.

## Start simulated traffic

```bash
docker compose --profile traffic up -d traffic-web traffic-auth traffic-batch
```

Watch the generators briefly:

```bash
docker compose logs --tail=10 traffic-web traffic-auth traffic-batch
```

Inspect created directories:

```bash
docker compose exec syslog-ng sh -c \
  'find /var/log/lab/by-ip -maxdepth 2 -type f -name events.log -print'
```

Read a few lines from every sender:

```bash
docker compose exec syslog-ng sh -c \
  'for f in /var/log/lab/by-ip/*/events.log; do echo "--- $f"; tail -n 3 "$f"; done'
```

Stop background traffic when you have enough data:

```bash
docker compose stop traffic-web traffic-auth traffic-batch
```

## Checkpoint

You should have multiple sender-IP directories. The message hosts should include names such as:

```text
web01
auth01
batch01
mail01
```

but the directory names are Docker IP addresses.

## Questions

1. Why is `${SOURCEIP}` useful when `${HOST}` already exists?
2. Which one is more directly controlled by the network peer, and which one is commonly supplied inside the message?
3. What happens to IP-based organization if a relay sits between all senders and this server?

---

# Task 5 - Forward critical/fatal events and survive a downstream outage

This task combines two ideas from the reference material:

- messages containing `critical` or `fatal` should be forwarded as `user.alert`;
- a disk buffer should hold messages while a TCP destination is unavailable.

The `collector` container is a second syslog-ng instance with a fixed configuration. It listens on TCP port `1601` inside the Docker network and writes:

```text
output/collector/alerts.log
```

## Goal

On the main syslog-ng instance:

1. match messages whose `${MESSAGE}` contains `critical` or `fatal`, case-insensitive;
2. rewrite facility to `user`;
3. rewrite severity to `alert`;
4. forward over TCP to `collector:1601`;
5. enable a reliable disk buffer;
6. enable flow-control on the log path.

## Hint 1 - content filter

Useful syntax:

```conf
match('critical|fatal' value("MESSAGE") flags(ignore-case))
```

Put it inside a named filter.

## Hint 2 - priority rewrite

A rewrite can contain both:

```conf
set-facility("user");
set-severity("alert");
```

## Hint 3 - network destination

Start from the shape:

```conf
destination d_alert_collector {
    network(
        "collector"
        transport(tcp)
        port(1601)
        ...
    );
};
```

## Hint 4 - current disk-buffer syntax

Inside the network destination add:

```conf
disk-buffer(
    reliable(yes)
    capacity-bytes(1048576)
    flow-control-window-bytes(131072)
    dir("/var/lib/syslog-ng/buffer")
)
```

The supplied older slide example uses `disk-buf-size()`. Current syslog-ng 4.12 documentation uses `capacity-bytes()` and byte-based flow-control window settings for reliable buffers.

## Hint 5 - flow-control

Add this to the completed `log` path:

```conf
flags(flow-control);
```

## Test A - healthy destination

Make sure collector is running:

```bash
docker compose start collector
```

Send one matching message:

```bash
docker compose run --rm toolbox send-bsd \
  --transport tcp --facility daemon --severity err \
  --host batch01 --program batchd \
  --message "critical export failure"
```

Inspect:

```bash
docker compose exec collector tail -n 10 /var/log/collector/alerts.log
```

The collector should see `facility=user` and `level=alert` because the main server rewrote the priority before forwarding.

## Test B - break the destination

Stop the collector:

```bash
docker compose stop collector
```

Send a burst:

```bash
docker compose run --rm toolbox burst \
  --transport tcp \
  --count 25 \
  --message "critical buffered failure sequence={n}"
```

Inspect the main server's state directory:

```bash
docker compose exec syslog-ng sh -c \
  'find /var/lib/syslog-ng -maxdepth 3 -type f -ls'
```

You can also inspect metrics:

```bash
docker compose exec syslog-ng syslog-ng-ctl stats | tail -n 40
```

The exact counter names can differ with active objects and statistics level, so do not grade the exercise by one hard-coded metric name.

## Test C - recover

Restart the collector:

```bash
docker compose start collector
```

Wait a few seconds and inspect:

```bash
docker compose exec collector tail -n 40 /var/log/collector/alerts.log
```

The starter global option uses `time-reopen(1)` so this classroom recovery happens quickly. Production defaults and tuning may differ.

## Checkpoint

- matching messages are forwarded;
- their forwarded priority is `user.alert`;
- messages sent while the collector is down appear after it returns;
- nonmatching normal messages are not forwarded to `alerts.log`.

## Questions

1. Why does the disk-buffer exercise use TCP rather than UDP?
2. What does `reliable(yes)` protect against?
3. Why is "reliable disk buffer" not the same statement as "exactly once"?
4. What is the purpose of flow-control if a disk buffer already exists?

---

# Optional Task 6 - RFC5424 and TLS

This task extends the supplied remote-IETF exercise. The package already contains a lab CA and server credentials under `certs/`.

## Goal

Add:

- RFC5424/IETF syslog over UDP port `8514`;
- RFC5424/IETF syslog over TLS port `6514`;
- one destination `/var/log/lab/ietf.log` containing reception time, host, facility, severity, program, `MSGID`, `SDATA`, and message text.

## UDP source hint

```conf
source s_ietf_udp {
    syslog(transport(udp) port(8514));
};
```

## TLS source ingredients

You need:

```text
syslog(...)
transport(tls)
port(6514)
peer-verify(optional-untrusted)
key-file("/etc/syslog-ng/lab-certs/server.key")
cert-file("/etc/syslog-ng/lab-certs/server.crt")
```

Assemble them into a source object. The reference presentation shows the same trust model: the server presents a certificate, while client certificates are not required.

## Destination hint

`${SDATA}` and `${MSGID}` are useful for observing RFC5424 structure.

## Test UDP

```bash
docker compose run --rm toolbox send-ietf \
  --transport udp \
  --facility local0 \
  --severity info \
  --host api01 \
  --program api \
  --msgid LOGIN42 \
  --sd '[event@32473 user="alice" result="ok"]' \
  --message "login completed"
```

## Test TLS

```bash
docker compose run --rm toolbox send-ietf \
  --transport tls \
  --facility local0 \
  --severity warning \
  --host api01 \
  --program api \
  --msgid DB17 \
  --sd '[db@32473 cluster="lab" node="1"]' \
  --message "database latency high"
```

Inspect:

```bash
docker compose exec syslog-ng tail -n 20 /var/log/lab/ietf.log
```

## Checkpoint

Both messages are accepted, and the structured data is visible in the output.

## Questions

1. What does TLS add that plain TCP does not?
2. In this lab the server does not require a client certificate. What identity is therefore authenticated?
3. Why are the distributed private key and certificate unacceptable for a real deployment?

---

# 16. Practical comparison after doing both labs

Answer these from what you actually configured rather than from the earlier comparison table.

1. In Fluentd, what did the tag do? What is the closest routing equivalent you used in syslog-ng?
2. Which syslog-ng features felt more natural for classic facility/severity routing?
3. Which Fluentd concepts felt more natural for structured application events?
4. Both systems support buffering. What was configured differently?
5. If you had 500 Linux servers and network appliances sending classic syslog, where could syslog-ng fit?
6. If those same servers also run container workloads emitting JSON application logs, would one collector necessarily be the best answer for every source?

---

# 17. Troubleshooting

## Configuration fails validation

Run:

```bash
docker compose run --rm --no-deps syslog-ng -s
```

Common causes:

- missing semicolon after an object or option;
- missing closing `}` or `);`;
- a `log` path references an object name you misspelled;
- an option was placed in the wrong object;
- parentheses are correct individually but not nested correctly.

Edit one section at a time and validate before adding the next.

## Container starts and immediately stops

Inspect:

```bash
docker compose logs syslog-ng
```

The official image runs syslog-ng in the foreground, so startup/configuration errors appear in the container log.

## Message is in `all.log` but not the specialized file

This usually means reception is working but your filter or specialized log path is wrong.

Check:

1. facility/severity in `all.log`;
2. filter spelling;
3. Boolean expression;
4. destination path;
5. that the correct source is included in the specialized log path.

## No message anywhere

Check the source and transport first.

```bash
docker compose run --rm toolbox probe --transport tcp --port 1514
```

Then check:

```bash
docker compose logs --tail=80 syslog-ng
```

For UDP, remember that successful sending does not prove successful reception.

## Dynamic directory was not created

Confirm:

```conf
create-dirs(yes)
```

and check the destination path and permissions.

## Collector does not receive alerts after restart

Check main syslog-ng logs:

```bash
docker compose logs --tail=100 syslog-ng
```

Check collector logs:

```bash
docker compose logs --tail=100 collector
```

Confirm the destination host is the Docker service name:

```text
collector
```

not `localhost`. Inside the main syslog-ng container, `localhost` means the main container itself.

## TLS send fails

First confirm the TLS source is configured and syslog-ng restarted successfully.

Then test with:

```bash
docker compose run --rm toolbox send-ietf --transport tls --message "tls test"
```

The toolbox verifies the lab certificate by default. For diagnosis only, you can try:

```bash
docker compose run --rm toolbox send-ietf --transport tls --insecure --message "tls test"
```

If insecure mode works but verified mode does not, the problem is certificate verification rather than basic TCP reachability.

---

# 18. Cleanup

Stop traffic if it is running:

```bash
docker compose stop traffic-web traffic-auth traffic-batch
```

Remove the stack and named state volume:

```bash
docker compose --profile traffic down -v --remove-orphans
```

The generated files under `output/` are bind-mounted host files and remain until deleted.

---

# 19. References

The lab is based on the two supplied course presentations plus current syslog-ng documentation.

Provided material:

- Risto Vaarandi, *Cyber Defense Monitoring Solutions - 5. Syslog-ng framework*, version 2025-10-21. The practical tasks on the final slides are adapted into Tasks 2-6.
- *ICS0020 Logging and Monitoring - Lecture 6 - syslog-ng*. Its syslog-ng fundamentals, TLS, templates, filters, and earlier Fluentd material are used to connect this lab with the previous session.

Current upstream documentation used for the lab configuration:

- https://github.com/syslog-ng/syslog-ng
- https://github.com/syslog-ng/syslog-ng/releases/tag/syslog-ng-4.12.0
- https://hub.docker.com/r/balabit/syslog-ng/tags
- https://syslog-ng.github.io/admin-guide/
- https://syslog-ng.github.io/admin-guide/050_The_configuration_file/001_Configuration_syntax.html
- https://syslog-ng.github.io/admin-guide/110_Template_and_rewrite/000_Customize_message_format/001_Templates_and_macros.html
- https://syslog-ng.github.io/admin-guide/080_Log/030_Filters/005_Filter_functions/README.html
- https://syslog-ng.github.io/admin-guide/110_Template_and_rewrite/001_Modifying_messages/README.html
- https://syslog-ng.github.io/admin-guide/080_Log/010_Flow_control/README.html
- https://syslog-ng.github.io/admin-guide/070_Destinations/150_Network/000_Network_destination_options.html

The lab pins syslog-ng `4.12.0`. If you run it with a later image, verify configuration syntax against that version's documentation rather than assuming all examples are unchanged.
