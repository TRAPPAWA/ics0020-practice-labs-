.headers on
.mode column

-- Starter query file for Tasks 6-8.
-- Import the unlabeled evidence first; see STUDENT.md.

-- Example 1: protocol distribution.
SELECT proto, COUNT(*) AS flows
FROM flows
GROUP BY proto
ORDER BY flows DESC;

-- Example 2: direction relative to the investigated host.
SELECT
  CASE
    WHEN src_addr='147.32.84.165' THEN 'outbound'
    WHEN dst_addr='147.32.84.165' THEN 'inbound'
    ELSE 'other'
  END AS direction,
  COUNT(*) AS flows
FROM flows
GROUP BY direction;

-- Example 3: top outbound TCP destination ports by flow count.
SELECT dst_port,
       COUNT(*) AS flows,
       COUNT(DISTINCT dst_addr) AS distinct_destinations,
       SUM(bytes) AS total_bytes
FROM flows
WHERE src_addr='147.32.84.165'
  AND proto='tcp'
GROUP BY dst_port
ORDER BY flows DESC
LIMIT 15;

-- Example 4: use the same grouping but rank by byte volume.
SELECT dst_port,
       COUNT(*) AS flows,
       COUNT(DISTINCT dst_addr) AS distinct_destinations,
       SUM(bytes) AS total_bytes
FROM flows
WHERE src_addr='147.32.84.165'
  AND proto='tcp'
GROUP BY dst_port
ORDER BY total_bytes DESC
LIMIT 15;

-- Example 5: rank destination IP/port pairs and keep forward/reverse counters separate.
SELECT dst_addr,
       dst_port,
       COUNT(*) AS flows,
       SUM(src_packets) AS packets_out,
       SUM(dst_packets) AS packets_back,
       SUM(src_bytes) AS bytes_out,
       SUM(dst_bytes) AS bytes_back,
       SUM(bytes) AS total_bytes
FROM flows
WHERE src_addr='147.32.84.165'
GROUP BY dst_addr, dst_port
ORDER BY total_bytes DESC
LIMIT 15;

-- Task 7: write focused queries for SMTP fan-out, the repeated control pair,
-- periodicity, and inbound RDP. Put them below this line.


-- Task 8: write behavioral queries that do NOT hardcode TCP/25 or the known
-- control IP/port. Start from COUNT(*), COUNT(DISTINCT dst_addr), SUM(bytes),
-- SUM(dst_packets), and LAG(start_epoch) OVER (PARTITION BY ... ORDER BY ...).
