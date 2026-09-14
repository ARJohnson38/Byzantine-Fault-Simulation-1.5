import json
import os
import time
import threading
from collections import Counter
from pathlib import Path

from flask import Flask, jsonify, request
import requests


app = Flask(__name__)

NODE_ID = os.environ.get("NODE_ID", "N1")
PEERS = json.loads(os.environ.get("PEERS_JSON", "{}"))
FAULT_CONFIG = json.loads(os.environ.get("FAULT_CONFIG", "{}"))

LOG_DIR = Path(os.environ.get("LOG_DIR", "/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

runs = {}
lock = threading.Lock()


def log_event(run_id, event, **data):
    entry = {
        "timestamp": time.time(),
        "node": NODE_ID,
        "run_id": run_id,
        "event": event,
        **data
    }

    with open(LOG_DIR / f"{run_id}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def normalize(value):
    if value in ("ATTACK", "RETREAT"):
        return value
    return "RETREAT"


def majority(values):
    normalized = [normalize(v) for v in values]
    counts = Counter(normalized)

    if counts["ATTACK"] > counts["RETREAT"]:
        return "ATTACK"

    return "RETREAT"


def send_message(destination, payload):
    url = PEERS[destination] + "/message"

    try:
        response = requests.post(url, json=payload, timeout=3)
        return response.status_code == 200
    except Exception:
        return False


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "node": NODE_ID
    })


@app.route("/message", methods=["POST"])
def message():
    payload = request.get_json(force=True)

    run_id = payload["run_id"]

    with lock:
        run = runs.get(run_id)

        if run is None:
            return jsonify({"accepted": False, "reason": "unknown_run"}), 404

        if run.get("completed"):
            log_event(
                run_id,
                "IGNORE",
                reason="late_after_decision",
                payload=payload
            )
            return jsonify({"accepted": False, "reason": "completed"})

        round_number = payload.get("round")
        sender = payload.get("sender")
        value = normalize(payload.get("value"))

        if round_number == 1:
            run["direct"][sender] = value

        elif round_number == 2:
            run["relays"][sender] = value

    log_event(
        run_id,
        "RECEIVE",
        sender=sender,
        round=round_number,
        value=value
    )

    return jsonify({"accepted": True})


def leader_value_for(destination, command):
    fault_mode = FAULT_CONFIG.get("fault_mode")

    if fault_mode == "leader_pattern":
        pattern = FAULT_CONFIG.get("pattern", {})
        return normalize(pattern.get(destination, command))

    return command


def relay_value(run, command, destination=None):
    fault_mode = FAULT_CONFIG.get("fault_mode")

    received = normalize(run["direct"].get("N1", "RETREAT"))

    if fault_mode == "relay_pattern":
        pattern = FAULT_CONFIG.get("pattern", {})

        if destination is not None:
            return normalize(pattern.get(destination, received))

        return normalize(pattern.get("default", received))

    return received

def execute_run(run_id):
    with lock:
        run = runs[run_id]

    start_time = run["start_time"]
    command = run["command"]
    mode = run["mode"]

    delay = start_time - time.time()

    if delay > 0:
        time.sleep(delay)

    log_event(
        run_id,
        "RUN_START",
        scenario=run["scenario"],
        mode=mode,
        command=command
    )

    # -------------------------
    # ROUND 1
    # -------------------------

    if NODE_ID == "N1":
        for destination in ("N2", "N3", "N4"):
            value = leader_value_for(destination, command)

            payload = {
                "run_id": run_id,
                "sender": "N1",
                "round": 1,
                "value": value
            }

            success = send_message(destination, payload)

            log_event(
                run_id,
                "SEND",
                destination=destination,
                round=1,
                value=value,
                success=success
            )

    round1_deadline = start_time + 5

    remaining = round1_deadline - time.time()

    if remaining > 0:
        time.sleep(remaining)

    # -------------------------
    # MODE A
    # -------------------------

    if mode == "direct":
        if NODE_ID == "N1":
            decision = command
        else:
            decision = normalize(run["direct"].get("N1", "RETREAT"))

        with lock:
            run["decision"] = decision
            run["completed"] = True

        log_event(
            run_id,
            "DECISION",
            decision=decision,
            mode=mode
        )

        return

    # -------------------------
    # ROUND 2
    # -------------------------

    if NODE_ID != "N1":
        fault_mode = FAULT_CONFIG.get("fault_mode")

        if fault_mode != "silent_round2":
            for destination in ("N2", "N3", "N4"):
                if destination == NODE_ID:
                    continue

                value = relay_value(run, command, destination)

                payload = {
                    "run_id": run_id,
                    "sender": NODE_ID,
                    "round": 2,
                    "value": value
                }

                success = send_message(destination, payload)

                log_event(
                    run_id,
                    "SEND",
                    destination=destination,
                    round=2,
                    value=value,
                    success=success
                )

    round2_deadline = start_time + 10

    remaining = round2_deadline - time.time()

    if remaining > 0:
        time.sleep(remaining)

    # -------------------------
    # DECISION
    # -------------------------

    if NODE_ID == "N1":
        if FAULT_CONFIG.get("fault_mode") == "leader_pattern":
            decision = "N/A"
        else:
            decision = command

    else:
        direct_value = normalize(run["direct"].get("N1", "RETREAT"))

        relay_values = []

        for follower in ("N2", "N3", "N4"):
            if follower == NODE_ID:
                continue

            relay_values.append(
                normalize(run["relays"].get(follower, "RETREAT"))
            )

        decision = majority(
            [direct_value] + relay_values
        )

    with lock:
        run["decision"] = decision
        run["completed"] = True

    log_event(
        run_id,
        "DECISION",
        decision=decision,
        direct=run["direct"],
        relays=run["relays"],
        mode=mode
    )


@app.route("/start", methods=["POST"])
def start():
    data = request.get_json(force=True)

    required = [
        "run_id",
        "scenario",
        "command",
        "mode",
        "start_time"
    ]

    for key in required:
        if key not in data:
            return jsonify({
                "accepted": False,
                "reason": f"missing_{key}"
            }), 400

    run_id = data["run_id"]

    with lock:
        if run_id in runs:
            return jsonify({
                "accepted": False,
                "reason": "run_already_exists",
                "node": NODE_ID,
                "run_id": run_id
            }), 409

    runs[run_id] = {
        "run_id": run_id,
        "scenario": data["scenario"],
        "command": normalize(data["command"]),
        "mode": data["mode"],
        "start_time": float(data["start_time"]),
        "direct": {},
        "relays": {},
        "decision": None,
        "completed": False
    }

    thread = threading.Thread(
        target=execute_run,
        args=(run_id,),
        daemon=True
    )

    thread.start()

    return jsonify({
        "accepted": True,
        "node": NODE_ID,
        "run_id": run_id
    })



@app.route("/result/<run_id>")
def result(run_id):
    with lock:
        run = runs.get(run_id)

        if run is None:
            return jsonify({
                "found": False,
                "run_id": run_id
            }), 404

        return jsonify({
            "found": True,
            "node": NODE_ID,
            "run_id": run_id,
            "scenario": run["scenario"],
            "mode": run["mode"],
            "command": run["command"],
            "direct": run["direct"],
            "relays": run["relays"],
            "decision": run["decision"],
            "completed": run["completed"]
        })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        threaded=True
    )

