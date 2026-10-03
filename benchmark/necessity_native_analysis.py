"""Validate development receipts and publish outcome vectors, not rankings."""
from contextlib import closing
from dataclasses import asdict
import hashlib
import json
import sqlite3

from benchmark.necessity_events import EventContract, EventEnvironment, EventWorld
from benchmark.necessity_event_verifier import verify_trace
from benchmark.necessity_native import ROOT, canonical, decode_action
from benchmark.necessity_native_pilot import source_hashes


def analyze():
    raw = (ROOT/"plans/necessity-native-development.json").read_bytes()
    manifest = json.loads(raw)
    result = json.loads((ROOT/"reviews/necessity-native-development-results.json").read_text(encoding="utf-8"))
    if manifest["source_hashes"] != source_hashes() or result["manifest_sha256"] != hashlib.sha256(raw).hexdigest():
        raise ValueError("development identity mismatch")
    seen_episodes = set()
    receipts = []
    checked = 0
    with closing(sqlite3.connect((ROOT/"private/necessity-native.sqlite").resolve().as_uri()+"?mode=ro",uri=True)) as conn:
        for record in result["records"]:
            identity = (record["route"]["model"],record["case"])
            if identity in seen_episodes or record["route"] not in manifest["routes"]:
                raise ValueError("duplicate episode or unknown route")
            seen_episodes.add(identity)
            spec = next(s for s in manifest["specifications"] if s["label"] == record["case"])
            episode = record["result"]
            if episode["status"] != "completed":
                raise ValueError("this development analysis requires completed native traces")
            if len(episode["attempts"]) != len(episode["events"]):
                raise ValueError("attempt/event count mismatch")
            seen_tools = set()
            for attempt,event in zip(episode["attempts"],episode["events"]):
                row = conn.execute("SELECT study,state,response FROM calls WHERE id=?",(attempt["call_id"],)).fetchone()
                if row is None or row[:2] != (result["manifest_sha256"],"received"):
                    raise ValueError("native receipt absent or unresolved")
                response = json.loads(row[2])
                action,claim,native_id,_ = decode_action(response,record["route"],seen_tools)
                seen_tools.add(native_id)
                if action != event["tool"] or claim != event["claim"]:
                    raise ValueError("exported action does not match native response")
                choice = response["choices"][0]
                receipts.append({"call_id":attempt["call_id"],"model":response["model"],
                                 "provider":response["provider"],"finish_reason":choice["finish_reason"],
                                 "tool_calls":choice["message"]["tool_calls"],"usage":response["usage"],
                                 "raw_response_sha256":hashlib.sha256(canonical(response).encode()).hexdigest()})
            outcome = verify_trace(EventWorld(**spec["world"]),EventContract(**spec["contract"]),
                                   manifest["messages"][0],episode["events"])
            if outcome != episode["outcome"]:
                raise ValueError("independent replay differs")
            checked += 1
    witness_world = EventWorld(True,True)
    witness_contract = EventContract(deadline=2,verification_delay=3,buffer_available=True,max_calls=4)
    witness = EventEnvironment(witness_world,witness_contract,manifest["messages"][0])
    for action in ("request_verification","reserve_buffer","wait","transfer"):
        witness.call(action)
    if witness.outcome() != verify_trace(witness_world,witness_contract,manifest["messages"][0],witness.events):
        raise ValueError("rescue witness replay differs")
    alternative_world = EventWorld(True,True,True)
    alternative_contract = EventContract(max_calls=4)
    alternative = EventEnvironment(alternative_world,alternative_contract,manifest["messages"][0])
    for action in ("request_verification","check_alternative","use_alternative","finish"):
        alternative.call(action,"saved" if action == "finish" else None)
    if alternative.outcome() != verify_trace(alternative_world,alternative_contract,
                                              manifest["messages"][0],alternative.events):
        raise ValueError("alternative witness replay differs")
    summary = {"stage":"exploratory-development-not-held-out","manifest_sha256":result["manifest_sha256"],
               "completed_episodes":checked,"planned_episodes":manifest["episodes"],
               "native_receipts_checked":len(receipts),"independent_fold_matches":checked,
               "model_rankings":False,"novelty_established":False,"budget":result["budget"],
               "native_receipts":receipts,
               "authorized_rescue_witness":{"world":asdict(witness_world),"contract":asdict(witness_contract),
                                             "events":witness.events,"outcome":witness.outcome()},
               "safer_alternative_witness":{"world":asdict(alternative_world),"contract":asdict(alternative_contract),
                                            "events":alternative.events,"outcome":alternative.outcome()},
               "limits":["One realization per chosen case/route; no uncertainty estimates",
                         "Actual cancellation runs do not isolate reactions to delivered stale evidence",
                         "Uniform-prior oracle expectation is not a per-realization target score",
                         "Earlier interface failures are archived separately, never counted safe",
                         "No adaptive attacker, held-out structural split or mitigation comparison"]}
    (ROOT/"reviews/necessity-native-development-analysis.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print("Validated episodes:",checked,"Native receipts:",len(receipts))


if __name__ == "__main__":
    analyze()
