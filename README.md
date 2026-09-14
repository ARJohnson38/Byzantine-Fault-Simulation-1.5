# Byzantine Fault Simulation with Docker

## CCIS 473 -- Election and Mutual Exclusion

**Student:** Ashley Johnson\
**Assignment:** Byzantine Fault Simulation with Docker\
**Date:** September 2026

## Project Overview

This project demonstrates Byzantine fault behavior in a distributed
system using Python, Docker, and HTTP communication. Four logical nodes
exchange `ATTACK` and `RETREAT` commands and execute a two-round
OM(1)-style relay protocol.

-   **N1** -- Leader / commander
-   **N2** -- Follower
-   **N3** -- Follower
-   **N4** -- Follower

Five runs were selected for each of five scenarios, producing a final
data set of 25 relay-mode runs.

## Network and Docker Configuration

Each Docker container listens internally on port `8000`.

  Node   Host used in documented testing     Published Port
  ------ --------------------------------- ----------------
  N1     Computer A                                    5001
  N2     Computer A                                    5002
  N3     Computer B                                    5003
  N4     Computer B                                    5004

The completed testing documented in the report used two physical
computers. The assignment specification calls for at least three
separate physical computers, so this execution demonstrates
cross-computer communication but does not by itself satisfy the
three-physical-computer requirement.

## Operating Modes

### Mode A -- Direct Baseline

N1 sends its command directly to the followers.

### Mode B -- Two-Round Relay

1.  N1 sends `ATTACK` or `RETREAT` to each follower.
2.  Followers relay the value received from N1.
3.  Honest followers evaluate the direct and relay values using the
    implemented majority/default rules.
4.  Missing or invalid values default to `RETREAT`.

## Test Scenarios

**Scenario A -- All Honest:** All nodes follow the protocol normally.

**Scenario B -- Byzantine Leader:** N1 is faulty and can send different
commands to different followers.

**Scenario C -- False Relay:** N4 is faulty and can send false or
conflicting information during Round 2.

**Scenario D -- Silent Round 2:** N4 does not send its Round-2 relay
message.

**Scenario E -- Two Byzantine Nodes:** N1 and N4 are both faulty. This
exceeds the one-fault assumption, so agreement is not guaranteed.

## Final Selected Runs

``` text
Scenario A: A-01, A-02, A-03-R2, A-04, A-05
Scenario B: B-01, B-02, B-03-R2, B-04, B-05-R2
Scenario C: C-01-R2, C-02-R6, C-03, C-04, C-05-R6
Scenario D: D-01, D-02, D-03, D-04, D-05
Scenario E: E-01, E-02, E-03, E-04, E-05
```

Retry identifiers are retained because troubleshooting attempts were
preserved rather than overwritten.

## Results

Final results are stored in:

``` text
results/final_runs.csv
results/decision_table.csv
```

Raw JSONL logs are preserved separately for N1, N2, N3, and N4.
Troubleshooting and retry logs were retained, so the total number of log
files is greater than 25.

The written report discusses both expected outcomes and anomalous runs
rather than treating every completed execution as a successful agreement
run.

## Suggested Repository Structure

``` text
Byzantine_Docker_Assignment/
├── README.md
├── Dockerfile
├── src/
│   └── node.py
├── config/
│   ├── peers.json
│   ├── local_faults.example.json
│   └── run_plan.csv
├── results/
│   ├── final_runs.csv
│   └── decision_table.csv
├── logs/
│   ├── N1/
│   ├── N2/
│   ├── N3/
│   └── N4/
├── report/
│   └── CCIS_473_Byzantine_Fault_Simulation_Report.docx
└── video/
    └── README-or-video-link.txt
```

Do not publish passwords, credentials, tokens, or other sensitive
information.

## Build and Health Check

Build the image:

``` powershell
docker build --no-cache -t byzantine-node .
```

Example health check:

``` powershell
(Invoke-WebRequest -UseBasicParsing "http://localhost:5001/health").Content
```

A healthy node returns a response similar to:

``` json
{"node":"N1","status":"ok"}
```

For cross-computer nodes, use the destination computer's LAN address and
published port instead of `localhost`.

## Evidence

Assignment evidence includes raw JSONL logs, the final run CSV, decision
table CSV, screenshots, written report, demonstration video, source
code, and Docker configuration.

## Demonstration Video

**Video link:** [Lab
1.5.mp4](https://1drv.ms/v/c/74837dc9b967c4d3/IQD4Xv3BIqkCQL6V-oBsDk9LAWhT_-n-VWLNYhBYsBLc9uY?e=c1WOsj)

## Troubleshooting

Testing required troubleshooting of Docker environment-variable
formatting, PowerShell JSON quoting, Windows Firewall rules, Python
indentation, the Flask `/start` route, container rebuilds, cross-host
communication, and message timing.

## Conclusion

This project demonstrates distributed consensus behavior under honest
operation, a Byzantine commander, a faulty relay, a silent relay, and
multiple Byzantine faults. It also provides practical experience with
Docker networking, HTTP communication, fault injection, persistent
logging, and distributed-system analysis.
