"""Receipt-preserving structural collector; transport and readiness are injected.

No network or credential access at import or CLI. The existing USD50 shared
ledger remains authoritative. A separate source amendment precedes live use.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from benchmark.necessity_collection_plan import validate,packet_for,normalized_hash
from benchmark.necessity_structural_native import run_episode
from benchmark.necessity_native import ROOT,canonical

RUNNER_SOURCES = ("benchmark/necessity_collection_runner.py",
                  "benchmark/necessity_collection_analysis.py")


def amendment(manifest,root=ROOT):
    validate(manifest,root)
    value = {"stage":"collector-source-amendment-not-spending-authorization",
             "parent_manifest_sha256":manifest["manifest_sha256"],
             "source_sha256":{p:normalized_hash(root/p) for p in RUNNER_SOURCES},
             "matrix_unchanged":True,"new_model_calls":0,"collection_ready":False}
    value["amendment_sha256"] = hashlib.sha256(canonical(value).encode()).hexdigest()
    return value


def validate_amendment(manifest,extension,root=ROOT):
    validate(manifest,root)
    value = deepcopy(extension)
    expected = value.pop("amendment_sha256")
    if hashlib.sha256(canonical(value).encode()).hexdigest() != expected:
        raise ValueError("collector amendment changed")
    if extension["parent_manifest_sha256"] != manifest["manifest_sha256"]:
        raise ValueError("collector amendment parent mismatch")
    if set(extension["source_sha256"]) != set(RUNNER_SOURCES):
        raise ValueError("collector source set mismatch")
    for path,digest in extension["source_sha256"].items():
        if normalized_hash(root/path) != digest:
            raise ValueError("collector source changed")


def study_id(manifest,extension):
    return hashlib.sha256((manifest["manifest_sha256"]+"/"+extension["amendment_sha256"]).encode()).hexdigest()


def route_for(manifest,row):
    price = next(p for p in manifest["route_prices"] if p["model"] == row["model"])
    if price["provider_tag"] != row["provider_tag"]:
        raise ValueError("episode route mismatch")
    return {"model":row["model"],"provider":row["provider_tag"],"provider_name":price["provider_name"]}


def execute(manifest,extension,ledger,transport,save,episode_limit=None):
    """Collect in frozen order. Caller must establish live readiness externally.

    This library also supports offline injected transports. It grants no funding
    and never changes ledger caps. Every save is a public-safe structured report;
    raw API reasoning and text remain only in the caller's private ledger.
    Exceptions stop the entire run, preserving a partial trace without grading it.
    Reruns use identical ledger IDs and cannot resend unresolved requests.
    """
    validate_amendment(manifest,extension)
    if episode_limit is not None and (type(episode_limit) is not int or episode_limit < 1):
        raise ValueError("positive episode limit required")
    study = study_id(manifest,extension)
    report = {"study_id":study,"manifest_sha256":manifest["manifest_sha256"],
              "amendment_sha256":extension["amendment_sha256"],
              "planned_episodes":len(manifest["episodes"]),"records":[],
              "collection_state":"running","not_attempted":len(manifest["episodes"])}
    def persist():
        report["not_attempted"] = report["planned_episodes"]-len(report["records"])
        report["budget"] = ledger.summary()
        save(deepcopy(report))
    persist()
    for row in manifest["episodes"]:
        if episode_limit is not None and len(report["records"]) >= episode_limit:
            report["collection_state"] = "episode_limit_stop"
            persist()
            return report
        env,public = packet_for(row["template"],row["world_index"],row["arm"],row["message_id"])
        if hashlib.sha256(canonical(public).encode()).hexdigest() != row["public_packet_sha256"]:
            raise ValueError("episode packet changed before request")
        try:
            result = run_episode(env,route_for(manifest,row),public,row["episode_id"],study,ledger,transport)
        except BaseException as exc:
            # The private ledger has already preserved any sent payload/receipt.
            # Never stringify exceptions, which could contain sensitive content.
            attempts = []
            for index in range(row["max_calls"]):
                call_id = hashlib.sha256((study+"/"+row["episode_id"]+"/"+str(index)).encode()).hexdigest()
                stored = ledger.conn.execute("SELECT state FROM calls WHERE id=?",(call_id,)).fetchone()
                if stored is not None:
                    attempts.append({"call_id":call_id,"ledger_state":stored[0]})
            category = {
                "budget admission rejected before request":"budget_stop",
                "input byte gate exceeded before request":"input_gate",
                "receipt saved; cost unresolved":"billing_unresolved",
                "unexpected cost exceeds reservation; collection stopped":"billing_over_reservation",
                "unresolved request: review manually; never retry automatically":"unresolved_prior_request",
                "unresolved reservation blocks this study; retain its cost in other studies":"unresolved_study_hold",
            }.get(str(exc),"collection_error")
            if any(a["ledger_state"] == "held" for a in attempts):
                error = ledger.conn.execute("SELECT error FROM calls WHERE id=?",(attempts[-1]["call_id"],)).fetchone()
                if error and error[0] == "transport_unknown":
                    category = "transport_unknown"
            result = {"status":"collection_stopped","exception_type":type(exc).__name__,"stop_category":category,
                      "attempts":attempts,"events":env.events,"outcome":None}
            report["records"].append({"episode_id":row["episode_id"],"result":result})
            report["collection_state"] = "stopped"
            persist()
            if isinstance(exc,(KeyboardInterrupt,SystemExit)):
                raise
            return report
        report["records"].append({"episode_id":row["episode_id"],"result":result})
        if result["status"] != "completed":
            report["collection_state"] = "technical_stop"
            persist()
            return report
        persist()
    report["collection_state"] = "finished"
    persist()
    return report
