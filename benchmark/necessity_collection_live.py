"""Explicit live entry point with a preserved source amendment and readiness gate."""
import argparse
from contextlib import closing, contextmanager
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import urllib.request

from benchmark.necessity_native import ROOT,Ledger,canonical,CAP
from benchmark.necessity_native_pilot import load_key
from benchmark.necessity_collection_plan import normalized_hash
from benchmark.necessity_collection_runner import validate_amendment,execute,study_id
from benchmark.necessity_collection_analysis import analyze

MANIFEST = ROOT/"plans/necessity-structural-collection-manifest.json"
EXTENSION = ROOT/"plans/necessity-collector-source-amendment.json"
LIVE_EXTENSION = ROOT/"plans/necessity-live-source-amendment.json"
REPORT = ROOT/"reviews/necessity-structural-collection-results.json"
ANALYSIS = ROOT/"reviews/necessity-structural-collection-analysis.json"
SOURCES = ("benchmark/necessity_collection_live.py","benchmark/necessity_native_pilot.py")


def atomic_json(path,value):
    """Fsync completed bytes before atomically replacing the existing report."""
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    descriptor,name = tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(descriptor,"w",encoding="utf-8",newline="\n") as stream:
            json.dump(value,stream,indent=2,allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def live_amendment(manifest,extension):
    validate_amendment(manifest,extension)
    value = {"stage":"live-wiring-source-amendment-not-spending-authorization",
             "parent_manifest_sha256":manifest["manifest_sha256"],
             "collector_amendment_sha256":extension["amendment_sha256"],
             "source_sha256":{p:normalized_hash(ROOT/p) for p in SOURCES},
             "matrix_unchanged":True,"lifetime_cap_usd":str(CAP),"collection_ready":False}
    value["amendment_sha256"] = hashlib.sha256(canonical(value).encode()).hexdigest()
    return value


def validate_live(manifest,extension,live):
    if live != live_amendment(manifest,extension):
        raise ValueError("live source amendment mismatch")


def check_readiness(manifest,extension,live,readiness,budget):
    validate_live(manifest,extension,live)
    required = {
        "manifest_sha256":manifest["manifest_sha256"],
        "collector_amendment_sha256":extension["amendment_sha256"],
        "live_amendment_sha256":live["amendment_sha256"],
        "native_route_probes_complete":True,
        "prior_case_equivalence_review_complete":True,
        "hosted_provenance_limits_disclosed":True,
        "lifetime_cap_usd":str(CAP),
    }
    for key,value in required.items():
        if readiness.get(key) != value:
            raise RuntimeError("full collection readiness gate incomplete")
    # Native probe evidence must be bound to immutable records, not merely a
    # Boolean assertion. This wiring will not mint such evidence automatically.
    evidence = readiness.get("native_probe_report")
    if type(evidence) is not dict or set(evidence) != {"path","sha256"}:
        raise RuntimeError("native probe evidence missing")
    target = (ROOT/evidence["path"]).resolve()
    if not target.is_relative_to((ROOT/"reviews").resolve()) or not target.is_file():
        raise RuntimeError("native probe evidence outside reports")
    if normalized_hash(target) != evidence["sha256"]:
        raise RuntimeError("native probe evidence changed")
    probes = json.loads(target.read_text(encoding="utf-8"))
    expected_routes = {(r["model"],r["provider_tag"]) for r in manifest["route_prices"]}
    actual_routes = {(r["model"],r["provider_tag"]) for r in probes.get("routes",[]) if r.get("status") == "verified_native_interface"}
    if actual_routes != expected_routes or probes.get("manifest_sha256") != manifest["manifest_sha256"]:
        raise RuntimeError("native probe route/manifest mismatch")
    if Decimal(manifest["conditional_collection_usd"]) > Decimal(budget["remaining_accounted_usd"]):
        raise RuntimeError("prospective full matrix incompatible with remaining authorized budget")


@contextmanager
def collector_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    descriptor = os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        os.write(descriptor,str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        descriptor = None
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        path.unlink(missing_ok=True)


def transport_for(key):
    def send(payload):
        request = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
            data=canonical(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
        # No retries, redirects to different providers or external-action tools.
        with urllib.request.urlopen(request,timeout=180) as response:
            return json.load(response)
    return send


def read_inputs():
    return tuple(json.loads(p.read_text(encoding="utf-8")) for p in (MANIFEST,EXTENSION,LIVE_EXTENSION))


def collect(readiness_path):
    manifest,extension,live = read_inputs()
    readiness = json.loads(Path(readiness_path).read_text(encoding="utf-8"))
    with collector_lock(ROOT/"private/necessity-structural-collector.lock"):
        ledger = Ledger(ROOT/"private/necessity-native.sqlite",study_cap=CAP)
        try:
            check_readiness(manifest,extension,live,readiness,ledger.summary())
            if REPORT.exists():
                prior = json.loads(REPORT.read_text(encoding="utf-8"))
                if prior.get("study_id") != study_id(manifest,extension):
                    raise RuntimeError("preserve existing report from another study")
            result = execute(manifest,extension,ledger,transport_for(load_key()),lambda r:atomic_json(REPORT,r))
            atomic_json(ANALYSIS,analyze(manifest,extension,result,ledger.conn))
            return result
        finally:
            ledger.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["prepare","analyze","collect"])
    parser.add_argument("--readiness")
    args = parser.parse_args()
    if args.command == "prepare":
        if LIVE_EXTENSION.exists():
            raise RuntimeError("preserve existing live amendment; never overwrite")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        extension = json.loads(EXTENSION.read_text(encoding="utf-8"))
        atomic_json(LIVE_EXTENSION,live_amendment(manifest,extension))
        print("Live source amendment prepared. No generation request made.")
    elif args.command == "analyze":
        manifest,extension,live = read_inputs()
        validate_live(manifest,extension,live)
        with closing(sqlite3.connect((ROOT/"private/necessity-native.sqlite").resolve().as_uri()+"?mode=ro",uri=True)) as conn:
            result = analyze(manifest,extension,json.loads(REPORT.read_text(encoding="utf-8")),conn)
        atomic_json(ANALYSIS,result)
        print("Verified receipt reanalysis saved.")
    else:
        if not args.readiness:
            raise RuntimeError("explicit readiness report required")
        result = collect(args.readiness)
        print("Collection state:",result["collection_state"])

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("STOP:",type(exc).__name__,"Review saved state and readiness gates.")
        raise SystemExit(1) from None
