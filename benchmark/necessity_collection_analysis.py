"""Rebuild public outcomes from immutable private native receipts, without sends."""
from collections import Counter,defaultdict
from copy import deepcopy
import hashlib
import json

from benchmark.necessity_collection_plan import packet_for
from benchmark.necessity_collection_runner import validate_amendment,study_id,route_for
from benchmark.necessity_structural_native import run_episode
from benchmark.necessity_native import canonical
from benchmark.necessity_oracle import DEFAULT_WEIGHTS,loss


class ReceiptReader:
    def __init__(self,conn):
        self.conn,self.used = conn,[]
    def reserve(self,call_id,study,payload):
        row = self.conn.execute("SELECT study,payload,state,response FROM calls WHERE id=?",(call_id,)).fetchone()
        if row is None:
            raise RuntimeError("receipt_missing")
        if row[0] != study or row[1] != canonical(payload):
            raise ValueError("stored request identity/payload mismatch")
        self.used.append({"call_id":call_id,"state":row[2],
                          "payload_sha256":hashlib.sha256(row[1].encode()).hexdigest(),
                          "raw_response_sha256":hashlib.sha256(row[3].encode()).hexdigest() if row[3] else None})
        if row[2] != "received" or row[3] is None:
            raise RuntimeError("receipt_unresolved")
        return json.loads(row[3])
    def receive(self,*args):
        raise AssertionError("reanalysis cannot receive or send")
    def hold(self,*args):
        raise AssertionError("reanalysis cannot mutate ledger")


def analyze(manifest,extension,report,conn):
    validate_amendment(manifest,extension)
    study = study_id(manifest,extension)
    if report["study_id"] != study or report["manifest_sha256"] != manifest["manifest_sha256"] or (
            report["amendment_sha256"] != extension["amendment_sha256"]):
        raise ValueError("report identity mismatch")
    planned = manifest["episodes"]
    records = report["records"]
    if len(records) > len(planned) or [r["episode_id"] for r in records] != [r["episode_id"] for r in planned[:len(records)]]:
        raise ValueError("report is not the frozen collection prefix")
    verified,receipts = [],[]
    grouped = defaultdict(Counter)
    paired = defaultdict(dict)
    for index,row in enumerate(planned):
        group = (row["model"],row["split"],row["template"],row["arm"])
        grouped[group]["planned"] += 1
        if index >= len(records):
            grouped[group]["not_attempted"] += 1
            continue
        exported = records[index]["result"]
        env,public = packet_for(row["template"],row["world_index"],row["arm"],row["message_id"])
        reader = ReceiptReader(conn)
        try:
            rebuilt = run_episode(env,route_for(manifest,row),public,row["episode_id"],study,reader,
                                  lambda payload:(_ for _ in ()).throw(AssertionError("network forbidden")))
        except RuntimeError:
            # Missing/reserved/held receipt cannot justify a completed outcome.
            if exported["status"] != "collection_stopped" or exported["outcome"] is not None or exported["events"] != env.events:
                raise ValueError("stopped partial trace mismatch") from None
            rebuilt = {"status":"collection_stopped","outcome":None,"events":env.events}
        else:
            for key in ("status","events","outcome"):
                if rebuilt[key] != exported[key]:
                    raise ValueError("exported result differs from native receipts")
            if rebuilt["status"] == "technical_unknown" and rebuilt["reason"] != exported["reason"]:
                raise ValueError("technical category mismatch")
            if rebuilt["status"] == "completed":
                if rebuilt["action_origins"] != exported["action_origins"] or (
                        rebuilt["operator_prefix_event_count"] != exported["operator_prefix_event_count"]):
                    raise ValueError("action attribution mismatch")
        if [a["call_id"] for a in exported["attempts"]] != [a["call_id"] for a in reader.used]:
            raise ValueError("exported request identifiers mismatch")
        receipts.extend(reader.used)
        status = rebuilt["status"]
        grouped[group][status] += 1
        record = {"episode_id":row["episode_id"],"status":status,"outcome":rebuilt["outcome"]}
        if status == "technical_unknown":
            record["reason"] = rebuilt["reason"]
            grouped[group]["technical_reason/"+rebuilt["reason"]] += 1
        elif status == "collection_stopped":
            record["reported_stop_category"] = exported["stop_category"]
            record["category_independently_verified"] = False
            # Missing admission rows cannot prove a historical budget rejection;
            # distinguish owner-exported categories from ledger-supported evidence.
            if reader.used and reader.used[-1]["state"] == "held":
                stored = conn.execute("SELECT error FROM calls WHERE id=?",(reader.used[-1]["call_id"],)).fetchone()
                record["ledger_error_category"] = stored[0]
                record["category_independently_verified"] = (
                    exported["stop_category"] == "transport_unknown" and stored[0] == "transport_unknown")
        if status == "completed":
            record["weighted_loss"] = loss(rebuilt["outcome"],DEFAULT_WEIGHTS)
            record["termination"] = ("normal_text" if rebuilt["action_origins"][-1]["origin"] == "normal_text"
                                     else "explicit_finish" if rebuilt["events"][-1]["tool"] == "finish"
                                     else "max_calls")
            pair = (row["model"],row["template"],row["world_index"],row["message_id"],row["repetition"])
            paired[pair][row["arm"]] = record
        verified.append(record)
    differences = []
    planned_pairs = len(planned)//2
    for identity,arms in sorted(paired.items()):
        if set(arms) != {"baseline","deadline_planning"}:
            continue
        baseline,planning = arms["baseline"],arms["deadline_planning"]
        differences.append({"model":identity[0],"template":identity[1],"world_index":identity[2],
                            "message_id":identity[3],"repetition":identity[4],
                            "planning_minus_baseline":{k:planning["outcome"][k]-baseline["outcome"][k] for k in DEFAULT_WEIGHTS},
                            "weighted_difference":planning["weighted_loss"]-baseline["weighted_loss"]})
    return {"study_id":study,"verified_episode_records":len(verified),
            "planned_episodes":len(planned),"not_attempted":len(planned)-len(records),
            "verified_native_receipts":len(receipts),"records":verified,"receipt_hashes":receipts,
            "strata":[{"model":k[0],"split":k[1],"template":k[2],"arm":k[3],**dict(v)} for k,v in sorted(grouped.items())],
            "planned_pairs":planned_pairs,"complete_pairs":len(differences),
            "incomplete_pairs":planned_pairs-len(differences),"paired_differences":differences,
            "limits":["Descriptive finite-suite paired outcomes; no population confidence intervals or model ranking.",
                      "Unknown and unattempted episodes have no invented settled score.",
                      "Reanalysis validates stored receipt identity, not cryptographic provider checkpoint identity."]}
