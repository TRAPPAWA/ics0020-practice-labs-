# Evidence directory

The lab uses **CTU-13 Scenario 6 / CTU-Malware-Capture-Botnet-47** from the Stratosphere Laboratory.

Included evidence:

- `donbot-scenario6.pcap` — public CTU bot-only PCAP captured on the infected VM interface;
- `donbot-scenario6-flows-unlabeled.csv` — prepared CTU bidirectional-flow rows involving the investigated VM, with the CTU label removed for blind analysis;
- `donbot-scenario6-flows.binetflow` — the same prepared subset retaining the original CTU label for final validation;
- `donbot-scenario6-netflow-v9.pcap` — **derived/reconstructed teaching evidence**, generated from the unlabeled CTU rows as unidirectional NetFlow v9 export records;
- `SHA256SUMS` — hashes for all four evidence files.

The NetFlow-v9 PCAP is not an original CTU router/exporter capture. It uses documentation-only TEST-NET exporter/collector addresses (`192.0.2.6` and `192.0.2.200`) and exists only so students can inspect NetFlow v9 Template/Data FlowSets in Wireshark while analyzing the same underlying scenario.

No malware executable is included. Do not replay the packet capture or contact addresses/domains from the evidence.

Primary source: Stratosphere Laboratory / CTU-13 Scenario 6. CTU-13 is published under CC BY; retain attribution when redistributing the original or derived evidence.
