#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose down -v --remove-orphans || true
rm -f output/traps/traps.log
cat > config/student-agent/snmpd.conf <<'EOC'
# Student configuration file.
# Complete this in Task 2, then start the student-agent service.
#
# Requirements:
# - listen for SNMP over UDP on port 161
# - report sysName as student-agent
# - set a contact and location of your choice
# - define a read view named labview
# - allow the view to read these three subtrees:
#     .1.3.6.1.2.1.1   system
#     .1.3.6.1.2.1.2   interfaces
#     .1.3.6.1.2.1.31  ifMIB / 64-bit interface counters
# - allow SNMPv2c read-only access with community labpublic and labview
EOC
cat > config/trap-receiver/snmptrapd.conf <<'EOC'
# Task 5: authorize the labtraps SNMPv2c community for logging.
# Hint: authCommunity TYPES COMMUNITY
EOC
cat > work/poll_rate.sh <<'EOC'
#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-student-agent}"
INDEX="${2:-2}"
INTERVAL="${3:-5}"
COMMUNITY="labpublic"
# Complete in Task 3. See STUDENT.md.
EOC
chmod +x work/poll_rate.sh
