# Student Lab - SNMP Monitoring in Docker

**Prior SNMP experience:** not required  
**Prerequisite:** basic Docker/Compose familiarity

This lab is self-contained. You do not need Net-SNMP installed on your own computer. The supplied Docker stack contains SNMP agents, an SNMP manager/toolbox, a trap receiver, and a traffic generator.

---

# Part A - Theory and preparation

## 1. Learning outcomes

By the end of the session you should be able to:

1. Explain the roles of an SNMP manager, agent, MIB, managed object, and OID.
2. Read a numeric OID and distinguish scalar objects from table entries.
3. Use `snmpget`, `snmpgetnext`, `snmpwalk`, and `snmpbulkwalk` for different retrieval tasks.
4. Explain what `SET`, traps, and informs do and when each is appropriate.
5. Explain the difference between SNMPv2c community-based access and SNMPv3 user-based security.
6. Configure a Net-SNMP agent with an OID view and read-only community access.
7. Use IF-MIB counters to measure actual network traffic generated between Docker containers.
8. Calculate an approximate traffic rate from counter deltas.
9. Capture SNMP traffic and identify why SNMPv2c should not be treated as confidential.
10. Query an SNMPv3 `authPriv` agent.
11. Configure a notification receiver and compare an unacknowledged trap with an acknowledged inform.
12. Relate SNMP monitoring to the logging pipelines used in the previous labs without treating them as the same problem.

---

## 2. SNMP is monitoring, not another log collector

The previous labs dealt mainly with event streams. An application or host generated a log record, and a collector received, filtered, transformed, stored, or forwarded it.

SNMP is built around a different model.

An SNMP manager can ask an agent for the current value of a managed object:

```text
manager -- GET request --> agent
manager <-- response ---- agent
```

The manager can also walk through many objects, set a writable value, or receive an asynchronous notification from an agent.

A useful distinction is:

```text
logs:  "this event happened"
SNMP:  "what is the current value/state?"
trap:  "this noteworthy condition happened"
```

Real monitoring systems often use several of these mechanisms together.

---

## 3. The SNMP components

The lecture introduced three main components:

- **Manager / NMS** - sends queries, receives responses, can perform writes, and receives notifications.
- **Agent** - runs on or represents a managed device and exposes management information.
- **MIB** - describes managed objects and how they are named in the OID tree.

In this lab the Docker services play those roles:

```text
                       UDP/161
                 +----------------+
                 |                v
+---------+   SNMP requests   +------------------+
| manager | ----------------> | reference-agent  |
|         | <---------------- | student-agent    |
|         |   responses       | secure-agent     |
+---------+                    +------------------+
     ^                                  |
     |                                  | HTTP traffic
     | UDP/162                          v
+---------------+                 +-------------+
| trap-receiver |                 | traffic     |
+---------------+                 +-------------+
```

The `reference-agent` is preconfigured for the first experiments. The `student-agent` is the one you configure. The `secure-agent` is preconfigured with SNMPv3 so that you can compare security on the wire.

---

## 4. MIBs and OIDs

An Object Identifier is a path in a hierarchical namespace.

For example:

```text
.1.3.6.1.2.1.1.5.0
```

is the numeric OID for `sysName.0` in the standard system group.

A simplified path is:

```text
1        iso
1.3      org
1.3.6    dod
1.3.6.1  internet
...2.1   mib-2
...1     system
...5     sysName
...0     scalar instance
```

Tables work differently. A table column is followed by an index identifying a row. For example, the interface-description column is:

```text
.1.3.6.1.2.1.2.2.1.2.<ifIndex>
```

If `eth0` has interface index `2`, its description is stored at:

```text
.1.3.6.1.2.1.2.2.1.2.2
```

### OIDs used in this lab

| Purpose | Numeric OID |
|---|---|
| `sysUpTime.0` | `.1.3.6.1.2.1.1.3.0` |
| `sysContact.0` | `.1.3.6.1.2.1.1.4.0` |
| `sysName.0` | `.1.3.6.1.2.1.1.5.0` |
| `sysLocation.0` | `.1.3.6.1.2.1.1.6.0` |
| `ifDescr` column | `.1.3.6.1.2.1.2.2.1.2` |
| `ifInOctets` column | `.1.3.6.1.2.1.2.2.1.10` |
| `ifOutOctets` column | `.1.3.6.1.2.1.2.2.1.16` |
| `ifHCInOctets` column | `.1.3.6.1.2.1.31.1.1.1.6` |
| `ifHCOutOctets` column | `.1.3.6.1.2.1.31.1.1.1.10` |

The `HC` counters are 64-bit high-capacity counters. They are preferable for traffic-rate calculations because 32-bit octet counters can wrap quickly on fast links.

---

## 5. Core SNMP operations

### 5.1 GET

Retrieve a known object instance.

```text
GET sysName.0
-> "router-a"
```

Use it when you already know the exact OID you need.

### 5.2 GETNEXT

Return the next accessible OID after the one supplied.

Conceptually:

```text
GETNEXT .1.3.6.1.2.1.1.3.0
-> next OID in the accessible tree
```

Repeated GETNEXT requests are the basis of an SNMP walk.

### 5.3 GETBULK

SNMPv2 added GETBULK to retrieve multiple successive values efficiently. Tools such as `snmpbulkwalk` can traverse a subtree with fewer request/response exchanges than a sequence of individual GETNEXT operations.

### 5.4 SET

SET changes a writable managed object. It requires write authorization and the object itself must permit writes.

This is operational control, not just observation. The lab uses an isolated write community for one safe demonstration. Do not copy that design into a real network.

### 5.5 TRAP

A trap is sent asynchronously by an agent or device to a manager/receiver.

A trap is not acknowledged by SNMP. The sender can transmit it without knowing whether the receiver actually processed it.

### 5.6 INFORM

An inform is also an asynchronous notification, but the receiver acknowledges it. The sender can retry when an acknowledgement does not arrive.

This distinction will be visible in Task 5.

---

## 6. Ports and transport

The standard ports used in this lab are:

```text
UDP/161  SNMP requests and responses
UDP/162  traps and informs
```

SNMP commonly uses UDP. Request/response behavior still exists at the SNMP application layer: a manager sends a request and expects a matching response.

---

## 7. SNMP versions

### SNMPv1

The original widely deployed version. It is still encountered on old or limited devices, but it lacks the later protocol improvements and modern security model.

### SNMPv2c

SNMPv2c adds protocol improvements including GETBULK, but access is still based on a **community string**.

A command looks like:

```bash
snmpget -v2c -c labpublic HOST OID
```

The community string should not be treated as encryption. It travels in the message and can be observed on the network.

### SNMPv3

SNMPv3 introduces a user-based security model. Common security levels are:

| Level | Authentication | Privacy/encryption |
|---|---|---|
| `noAuthNoPriv` | no | no |
| `authNoPriv` | yes | no |
| `authPriv` | yes | yes |

This lab uses `authPriv` with SHA authentication and AES privacy.

The command contains more parameters because the manager must specify the user and security algorithms:

```text
-v3 -l authPriv -u USER -a SHA -A AUTH_PASSWORD -x AES -X PRIV_PASSWORD
```

---

## 8. Access control and views in Net-SNMP

A Net-SNMP `snmpd.conf` can expose only selected parts of the MIB tree.

A view definition follows this pattern:

```conf
view VIEW_NAME included OID_SUBTREE
```

Multiple lines can add several subtrees to the same view.

Community-based read-only access can then reference that view:

```conf
rocommunity COMMUNITY SOURCE -V VIEW_NAME
```

For the lab, `SOURCE` will be `default` because Docker's private lab network is already isolated. On a real network, allowing every source would be a poor default.

The listening address follows this pattern:

```conf
agentaddress udp:161
```

The system metadata directives are:

```conf
sysName NAME
sysContact TEXT
sysLocation TEXT
```

One important Net-SNMP detail: if `sysLocation`, `sysContact`, or `sysName` is fixed in `snmpd.conf`, Net-SNMP makes that object read-only. The reference agent intentionally leaves `sysLocation` unset so the SET experiment can work.

---

# Part B - Practical work

## 9. Prepare the environment

From the lab directory:

```bash
cp -r /path/to/snmp-docker-lab snmp-lab
cd snmp-lab
```

Build the images:

```bash
docker compose build
```

Start only the services that already have complete configurations:

```bash
docker compose up -d reference-agent secure-agent manager trap-receiver
```

Check them:

```bash
docker compose ps
```

Do not start `student-agent` yet. Its configuration is intentionally incomplete.

Useful commands throughout the lab:

```bash
docker compose logs --tail=30 SERVICE
docker compose restart SERVICE
docker compose exec manager bash
```

All SNMP client commands in this handout run inside the `manager` container unless stated otherwise.

---

# Task 1 - Query an agent and navigate the OID tree

The goal is to use SNMP as a manager, not to change any configuration yet.

## 1.1 Read known scalar values

Query the agent name:

```bash
docker compose exec manager \
  snmpget -v2c -c labpublic -On reference-agent \
  .1.3.6.1.2.1.1.5.0
```

Query the uptime and contact information as well.

You need to determine the correct OIDs from the table earlier in this handout.

Record:

```text
sysName:
sysUpTime:
sysContact:
```

Why do these OIDs end in `.0`?

## 1.2 Use GETNEXT

Start with `sysUpTime.0`:

```bash
docker compose exec manager \
  snmpgetnext -v2c -c labpublic -On reference-agent \
  .1.3.6.1.2.1.1.3.0
```

Run it again using the returned OID as the next starting point.

Question: what does GETNEXT allow a manager to do when it does not already know every object instance?

## 1.3 Walk the system subtree

```bash
docker compose exec manager \
  snmpwalk -v2c -c labpublic -On reference-agent \
  .1.3.6.1.2.1.1
```

Compare this to your manual GETNEXT experiment.

## 1.4 Walk a table with GETBULK

Retrieve the interface descriptions:

```bash
docker compose exec manager \
  snmpbulkwalk -v2c -c labpublic -On reference-agent \
  .1.3.6.1.2.1.2.2.1.2
```

Find the row corresponding to `eth0`. The final number in that OID is the interface index.

Record it:

```text
reference-agent eth0 ifIndex =
```

## 1.5 Perform a controlled SET

First read `sysLocation.0`:

```bash
docker compose exec manager \
  snmpget -v2c -c labpublic -On reference-agent \
  .1.3.6.1.2.1.1.6.0
```

Now use the lab-only write community:

```bash
docker compose exec manager \
  snmpset -v2c -c labwrite -On reference-agent \
  .1.3.6.1.2.1.1.6.0 s "Docker Lab Desk"
```

Read the value again using the read-only community.

Then try the same SET with `-c labpublic` instead of `-c labwrite`.

Questions:

1. What is the difference between an object being writable in the MIB and your credentials being allowed to write it?
2. Why is a read-write SNMPv2c community dangerous outside an isolated lab?
3. Why did the reference configuration leave `sysLocation` out of `snmpd.conf`?

---

# Task 2 - Build the student agent configuration

Now you will configure your own agent.

Open:

```text
config/student-agent/snmpd.conf
```

Implement these requirements:

1. Listen on UDP port 161.
2. Report `student-agent` as `sysName`.
3. Set your own `sysContact` and `sysLocation` strings.
4. Create a view called `labview`.
5. Include these subtrees in `labview`:
   - `.1.3.6.1.2.1.1`
   - `.1.3.6.1.2.1.2`
   - `.1.3.6.1.2.1.31`
6. Give community `labpublic` read-only access to that view.

Do not copy the reference-agent file. Build the configuration from the syntax patterns in Section 8.

### Hints

You need one listening directive, three system-information directives, three `view` lines, and one `rocommunity` line.

The general shapes are:

```conf
agentaddress PROTOCOL:PORT
view NAME included OID
rocommunity COMMUNITY default -V VIEW
```

When the file is ready, start the service:

```bash
docker compose up -d student-agent
```

If it exits or restarts:

```bash
docker compose ps
docker compose logs --tail=50 student-agent
```

Do not randomly change lines until the container stays up. Read the parser error first.

## 2.1 Verify the allowed view

The following should work after your configuration is correct:

```bash
docker compose exec manager \
  snmpget -v2c -c labpublic -On student-agent \
  .1.3.6.1.2.1.1.5.0
```

```bash
docker compose exec manager \
  snmpwalk -v2c -c labpublic -On student-agent \
  .1.3.6.1.2.1.2.2.1.2
```

```bash
docker compose exec manager \
  snmpwalk -v2c -c labpublic -On student-agent \
  .1.3.6.1.2.1.31.1.1.1.10
```

Now try a subtree you did not allow:

```bash
docker compose exec manager \
  snmpwalk -v2c -c labpublic -On student-agent \
  .1.3.6.1.2.1.25
```

The host-resources subtree should not be visible through your view.

Questions:

1. Why is `.1.3.6.1.2.1.31` a separate view entry instead of being covered by `.1.3.6.1.2.1.2`?
2. If a monitoring server only needs interface counters, why might a restricted view be preferable to exposing `.1` entirely?

Checkpoint: your `student-agent` must now return system data and interface data but not the host-resources subtree.

---

# Task 3 - Measure real Docker traffic with SNMP counters

This task connects SNMP to an actual monitoring problem: bandwidth usage.

The `student-agent` container also runs a small HTTP service on port 8080. The `traffic` container can request large responses from it. Those packets cross the Docker network interface, so the SNMP interface counters should change.

## 3.1 Discover the interface index

```bash
docker compose exec manager \
  snmpwalk -v2c -c labpublic -On student-agent \
  .1.3.6.1.2.1.2.2.1.2
```

Find `eth0` and record the final OID component:

```text
student-agent eth0 ifIndex =
```

Store it in your shell if convenient:

```bash
IDX=2
```

Replace `2` with the value you actually found.

## 3.2 Read high-capacity counters

Read both 64-bit counters:

```bash
docker compose exec manager \
  snmpget -v2c -c labpublic -On student-agent \
  .1.3.6.1.2.1.31.1.1.1.6.$IDX \
  .1.3.6.1.2.1.31.1.1.1.10.$IDX
```

The first is incoming octets. The second is outgoing octets.

## 3.3 Generate traffic

In another terminal run:

```bash
docker compose run --rm traffic \
  --target http://student-agent:8080/bytes/65536 \
  --duration 20 \
  --workers 4
```

While it runs, query the counters several times.

Which direction changes more, and why?

## 3.4 Turn counters into a rate

A cumulative octet counter is not itself a bandwidth measurement. You need two samples:

```text
delta_octets = counter_after - counter_before
bits_per_second = delta_octets * 8 / elapsed_seconds
```

Open:

```text
work/poll_rate.sh
```

Complete the TODOs. The script should:

1. accept a target and `ifIndex`;
2. query `ifHCOutOctets`;
3. wait a fixed interval;
4. query it again;
5. calculate and print the approximate bit/s rate.

The useful command form is:

```bash
snmpget -v2c -c labpublic -Oqv HOST OID
```

Run the traffic generator again and execute your script from the manager container:

```bash
docker compose exec manager \
  bash /work/poll_rate.sh student-agent $IDX 5
```

Run it once while traffic is active and once while the system is idle.

Questions:

1. Why do monitoring systems store successive counter samples rather than only the current counter value?
2. What happens if a counter resets because the agent restarts?
3. Why are 64-bit interface counters preferable on fast interfaces?

---

# Task 4 - Observe SNMPv2c and SNMPv3 on the wire

You will use `tcpdump` inside the manager container. Open two host terminals.

## 4.1 Capture an SNMPv2c request

In terminal A:

```bash
docker compose exec manager \
  tcpdump -ni eth0 -s0 -A -c 2 udp port 161
```

While it waits, run in terminal B:

```bash
docker compose exec manager \
  snmpget -v2c -c labpublic -On reference-agent \
  .1.3.6.1.2.1.1.5.0
```

Inspect the capture.

You should be able to find the community string `labpublic` in the packet data.

This is the central security problem with SNMPv1/v2c community strings: the string is an access credential, but it is not protected by encryption.

## 4.2 Query the SNMPv3 agent

The lab SNMPv3 credentials are:

```text
user:          labuser
security:      authPriv
auth protocol: SHA
auth password: LabAuthPass123!
priv protocol: AES
priv password: LabPrivPass123!
```

Query the secure agent:

```bash
docker compose exec manager \
  snmpget -v3 -l authPriv \
  -u labuser \
  -a SHA -A 'LabAuthPass123!' \
  -x AES -X 'LabPrivPass123!' \
  -On secure-agent \
  .1.3.6.1.2.1.1.5.0
```

You should receive `secure-agent`.

## 4.3 Capture the SNMPv3 exchange

Repeat the same `tcpdump` command from terminal A and issue the SNMPv3 query again from terminal B.

Compare the captures.

Do not expect the whole UDP packet to become unreadable. SNMPv3 still has protocol headers, and the security name can be visible. With `authPriv`, the scoped PDU containing the managed-object request/response is protected.

Questions:

1. What sensitive information was immediately visible in the v2c capture?
2. What is different in the v3 `authPriv` capture?
3. Why is "use a long community string" not a replacement for encryption?
4. In what type of isolated network might read-only v2c still be encountered, even though v3 is preferable?

---

# Task 5 - Receive notifications and compare TRAP with INFORM

SNMP polling asks devices for state. Notifications let a device report an event without waiting for the next poll.

The supplied `trap-receiver` is running `snmptrapd`, but its authorization file is intentionally incomplete.

Open:

```text
config/trap-receiver/snmptrapd.conf
```

Add a rule that authorizes community `labtraps` for **logging**.

The syntax pattern is:

```conf
authCommunity TYPES COMMUNITY
```

Restart the receiver:

```bash
docker compose restart trap-receiver
```

Check that it remains running:

```bash
docker compose ps trap-receiver
```

## 5.1 Send a linkDown-style trap

The agent image contains a helper that sends a standards-based `linkDown` notification and includes the container's actual `eth0` interface index.

Send it from the student agent:

```bash
docker compose exec student-agent \
  /opt/lab/send-notification.sh trap trap-receiver labtraps
```

Inspect the receiver:

```bash
docker compose logs --tail=30 trap-receiver
```

and:

```bash
cat output/traps/traps.log
```

Identify:

- the notification OID;
- the interface index;
- the interface description;
- the reported interface operational state.

## 5.2 Prove that a trap is unacknowledged

The `manager` container has no process listening on UDP/162. Use it as a reachable host with no notification receiver.

Send a trap to `manager` instead of `trap-receiver`:

```bash
docker compose exec student-agent \
  /opt/lab/send-notification.sh trap manager labtraps
```

Notice that the trap command returns even though no application on `manager` acknowledged or processed it.

Now send an inform to the same unavailable notification endpoint:

```bash
docker compose exec student-agent \
  /opt/lab/send-notification.sh inform manager labtraps
```

The helper uses a short timeout/retry setting. The inform should fail after waiting for an acknowledgement.

Finally, send the inform to the real receiver:

```bash
docker compose exec student-agent \
  /opt/lab/send-notification.sh inform trap-receiver labtraps
```

It should now complete successfully and appear in the receiver output.

Questions:

1. Why can a trap be lost without the sender knowing?
2. What reliability advantage does an inform provide?
3. Why would a monitoring system still poll important state even if traps are configured?
4. What failure cases remain even when informs are used?

---

# 10. Final check

At this point you should be able to demonstrate all of the following:

- query an exact OID;
- navigate with GETNEXT and walk a subtree;
- explain GETBULK;
- perform a controlled SET and explain the authorization risk;
- write a restricted Net-SNMP view and read-only community configuration;
- discover an interface index instead of hardcoding it;
- generate traffic and observe interface counters change;
- calculate a traffic rate from two SNMP counter samples;
- show the SNMPv2c community string in a packet capture;
- query an SNMPv3 `authPriv` agent;
- receive a trap;
- demonstrate the practical difference between a trap and an inform.

---

# 11. Optional extension - build a tiny NMS script

If you finish early, create `work/inventory.sh` or `work/inventory.py`.

For both `reference-agent` and `student-agent`, collect:

- `sysName.0`;
- `sysUpTime.0`;
- `sysLocation.0`;
- the `eth0` interface index;
- `ifHCInOctets`;
- `ifHCOutOctets`.

Print one concise line per device. Then extend it to take two samples and print an outbound bit/s estimate.

Do not hardcode the interface index. Discover it from the interface table.

A monitoring system is mostly repeated state collection plus storage, interpretation, thresholds, and notification. This extension is a small version of that loop.

---

# 12. Cleanup

Stop the lab and remove named volumes:

```bash
docker compose down -v
```

If you want to return all editable files to their original student state:

```bash
./scripts/reset-lab.sh
```

---

# 13. Reference summary

Useful Net-SNMP commands:

```text
snmpget       retrieve one or more exact object instances
snmpgetnext   retrieve the next accessible object
snmpwalk      repeatedly use GETNEXT over a subtree
snmpbulkwalk  use SNMPv2/v3 GETBULK to walk efficiently
snmpset       modify writable objects when authorized
snmptrap      send an unacknowledged notification
snmpinform    send an acknowledged notification
snmptrapd     receive notifications
```

The exact command-line syntax is less important than choosing the right operation and understanding what security and reliability properties it has.
