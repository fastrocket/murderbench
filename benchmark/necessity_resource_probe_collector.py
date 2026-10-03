"""Injected prospective collector; no credentials, network entry point or retries."""
from copy import deepcopy
import hashlib
import json
from benchmark.necessity_resource_probe_plan import ROOT, validate, digest
from benchmark.necessity_resource_probe import ProbeWorld, ProbeContract, ProbeEnvironment
from benchmark.necessity_resource_probe_native import public_packet, run_episode
from benchmark.necessity_resource_probe_analysis import diagnose
from benchmark.necessity_native import canonical


def validate_analysis(manifest, amendment):
    validate(manifest)
    contents = deepcopy(amendment)
    expected = contents.pop("amendment_sha256")
    if hashlib.sha256(canonical(contents).encode()).hexdigest() != expected:
        raise ValueError("analysis amendment changed")
    if amendment["parent_manifest_sha256"] != manifest["manifest_sha256"]:
        raise ValueError("analysis parent mismatch")
    paths = {"benchmark/necessity_resource_probe_analysis.py", "plans/necessity-resource-probe-prefix-analysis.txt"}
    if set(amendment["source_sha256_normalized_lf"]) != paths:
        raise ValueError("analysis source set mismatch")
    for path, expected in amendment["source_sha256_normalized_lf"].items():
        if digest(ROOT/path) != expected:
            raise ValueError("analysis source changed")


def freeze(manifest, analysis):
    validate_analysis(manifest, analysis)
    result = {"stage":"prospective_collector_amendment_no_authorization",
              "parent_manifest_sha256":manifest["manifest_sha256"],
              "analysis_amendment_sha256":analysis["amendment_sha256"],
              "collector_source_sha256_normalized_lf":digest(ROOT/"benchmark/necessity_resource_probe_collector.py"),
              "collection_ready":False}
    result["amendment_sha256"] = hashlib.sha256(canonical(result).encode()).hexdigest()
    return result


def execute(manifest, analysis, amendment, ledger, transport, save, episode_limit=None):
    """Caller establishes live readiness separately; injected tests grant no budget."""
    if freeze(manifest, analysis) != amendment:
        raise ValueError("collector freeze changed")
    if episode_limit is not None and (type(episode_limit) is not int or episode_limit < 1):
        raise ValueError("positive episode limit required")
    registration = json.loads((ROOT/"plans/necessity-resource-probe-registration.json").read_text())
    cells = {c["cell_id"]:c for c in registration["base_cells"]}
    routes = {p["model"]:p for p in manifest["route_prices"]}
    study = hashlib.sha256((manifest["manifest_sha256"]+"/"+amendment["amendment_sha256"]).encode()).hexdigest()
    report = {"study_id":study, "manifest_sha256":manifest["manifest_sha256"],
              "amendment_sha256":amendment["amendment_sha256"], "records":[],
              "planned_episodes":len(manifest["episodes"]), "collection_state":"running"}
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
        cell = cells[row["cell_id"]]
        contract = ProbeContract(**{k:cell[k] for k in ("reserve_capacity", "deadline", "probe_delay", "max_calls")})
        env = ProbeEnvironment(ProbeWorld(cell["need"]), contract)
        packet = public_packet(env)
        if hashlib.sha256(canonical(packet).encode()).hexdigest() != row["public_packet_sha256"]:
            raise ValueError("frozen packet mismatch")
        price = routes[row["model"]]
        route = {"model":row["model"], "provider":row["provider_tag"], "provider_name":price["provider_name"]}
        try:
            result = run_episode(env, route, packet, row["episode_id"], study, ledger, transport)
        except BaseException as exc:
            attempts = []
            for index in range(row["max_calls"]):
                call_id = hashlib.sha256((study+"/"+row["episode_id"]+"/"+str(index)).encode()).hexdigest()
                stored = ledger.conn.execute("SELECT state FROM calls WHERE id=?", (call_id,)).fetchone()
                if stored:
                    attempts.append({"call_id":call_id, "ledger_state":stored[0]})
            result = {"status":"collection_stopped", "exception_type":type(exc).__name__,
                      "events":env.events, "outcome":None, "attempts":attempts}
            report["records"].append({"episode_id":row["episode_id"], "result":result})
            report["collection_state"] = "stopped"
            persist()
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            return report
        report["records"].append({"episode_id":row["episode_id"], "result":result})
        if result["status"] != "completed":
            report["collection_state"] = "technical_stop"
            persist()
            return report
        try:
            diagnosis = diagnose(contract, env._message, result["events"])
        except (ValueError, RuntimeError, AssertionError):
            report["collection_state"] = "analysis_stop"
            persist()
            return report
        report["records"][-1]["diagnosis"] = diagnosis
        persist()
    report["collection_state"] = "finished"
    persist()
    return report
