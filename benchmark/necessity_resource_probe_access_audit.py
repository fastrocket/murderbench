"""Read-only exact-schema receipt audit; excludes raw private response content."""
import hashlib
from decimal import Decimal
import json
import sqlite3
from benchmark.necessity_native import ROOT, canonical
from benchmark.necessity_resource_probe_access import prepare, PLAN, REPORT
from benchmark.necessity_resource_probe import TOOLS
from benchmark.necessity_structural_native import native_tools, decode


def audit():
    plan, report = json.loads(PLAN.read_text()), json.loads(REPORT.read_text())
    if plan != prepare() or report["study_id"] != plan["study_id"]:
        raise ValueError("access freeze mismatch")
    conn = sqlite3.connect((ROOT/"private/necessity-native.sqlite").resolve().as_uri()+"?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    rows, cost, holds = [], Decimal(0), Decimal(0)
    try:
        for entry, exported in zip(plan["routes"], report["routes"]):
            if entry["model"] != exported["model"]:
                raise ValueError("route order mismatch")
            route = {"model":entry["model"], "provider":entry["provider_tag"], "provider_name":entry["provider_name"]}
            study = hashlib.sha256((plan["study_id"]+"/"+route["model"]).encode()).hexdigest()
            seen = set()
            for index, call in enumerate(exported["calls"]):
                identity = hashlib.sha256((study+"/"+str(index)).encode()).hexdigest()
                stored = conn.execute("SELECT study,payload,state,amount,response FROM calls WHERE id=?", (identity,)).fetchone()
                if not stored or identity != call["call_id"] or stored[0] != study or stored[2] != "received":
                    raise ValueError("received call identity mismatch")
                payload, response = json.loads(stored[1]), json.loads(stored[4])
                if payload["tools"] != native_tools(TOOLS) or hashlib.sha256(canonical(response).encode()).hexdigest() != call["response_sha256"]:
                    raise ValueError("schema or response changed")
                action, claim, tool_id, _, origin = decode(response, route, seen, TOOLS)
                if origin != "native_tool" or action != plan["sequence"][index] or action != call.get("action") or claim != call.get("claim"):
                    raise ValueError("decoded handshake mismatch")
                seen.add(tool_id)
                cost += Decimal(stored[3])
                rows.append({"call_id":identity, "model":entry["model"], "state":stored[2],
                             "amount_usd":stored[3], "action":action,
                             "payload_sha256":hashlib.sha256(stored[1].encode()).hexdigest(),
                             "response_sha256":call["response_sha256"]})
            if exported["status"] == "passed_exact_schema_handshake" and len(exported["calls"]) != 2:
                raise ValueError("incomplete passing handshake")
            if "stopped_call_id" in exported:
                stored = conn.execute("SELECT study,state,amount FROM calls WHERE id=?", (exported["stopped_call_id"],)).fetchone()
                if not stored or stored[0] != study or stored[1] != exported["ledger_state"]:
                    raise ValueError("stopped call mismatch")
                holds += Decimal(stored[2])
                rows.append({"call_id":exported["stopped_call_id"], "model":entry["model"],
                             "state":stored[1], "retained_amount_usd":stored[2]})
    finally:
        conn.close()
    return {"stage":"read_only_interface_receipt_audit", "records":rows,
            "received_cost_usd":str(cost), "retained_stopped_amount_usd":str(holds),
            "benchmark_episodes":0, "limits":["Native read_certificate/finish handshake, not every tool or scenario.",
            "Held HTTP failure has no usable response; no cause or zero billing inferred."]}


if __name__ == "__main__":
    output = ROOT/"reviews/necessity-resource-probe-access-audit.json"
    if output.exists():
        raise RuntimeError("preserve audit")
    result = audit()
    output.write_text(json.dumps(result, indent=2)+"\n")
    print("Received USD", result["received_cost_usd"], "retained USD", result["retained_stopped_amount_usd"])
