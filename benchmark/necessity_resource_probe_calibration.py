"""Registered sixteen-cell calibration, no model requests."""
from dataclasses import asdict
import argparse
import hashlib
import json
from pathlib import Path
from benchmark.necessity_resource_probe import ProbeContract,ProbeWorld,ProbeEnvironment,MESSAGE
from benchmark.necessity_resource_probe_verifier import verify_probe

POLICIES=("certificate_conditional","probe_conditional","always_rescue","finish_only",
          "repeat_probe","ack_as_success")


def run_policy(env,policy):
    if policy not in POLICIES:
        raise ValueError("unknown policy")
    if policy=="always_rescue":
        env.call("rescue")
    elif policy!="finish_only":
        env.call("read_certificate" if policy=="certificate_conditional" else "consume_probe")
        if policy=="repeat_probe":
            env.call("consume_probe")
        if policy!="ack_as_success":
            while not env.observe()["evidence"]:
                env.call("wait")
            if env.observe()["evidence"][-1]["need"]:
                env.call("rescue")
    env.call("finish","saved" if policy=="ack_as_success" else "unknown")
    return env.outcome()


def calibrate():
    root=Path(__file__).resolve().parents[1]
    registration=json.loads((root/"plans/necessity-resource-probe-registration.json").read_text())
    source=(root/"plans/necessity-resource-probe-protocol.txt").read_bytes().replace(b"\r\n",b"\n")
    if hashlib.sha256(source).hexdigest()!=registration["protocol_source_sha256_normalized_lf"]:
        raise ValueError("registered protocol changed")
    records=[]
    for cell in registration["base_cells"]:
        fields={k:v for k,v in cell.items() if k!="cell_id"}
        if hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(",",":")).encode()).hexdigest()!=cell["cell_id"]:
            raise ValueError("registered cell identity changed")
        contract=ProbeContract(**{k:cell[k] for k in ("reserve_capacity","deadline","probe_delay","max_calls")})
        world=ProbeWorld(cell["need"])
        for policy in POLICIES:
            env=ProbeEnvironment(world,contract)
            initial=env.observe();outcome=run_policy(env,policy)
            if verify_probe(world,contract,MESSAGE,env.events)!=outcome:
                raise AssertionError("resource-probe independent fold mismatch")
            records.append({"cell_id":cell["cell_id"],"world":asdict(world),"contract":asdict(contract),
                            "policy":policy,"initial_observation":initial,"events":env.events,"outcome":outcome})
    if any(r["outcome"]["primary_loss"] or r["outcome"]["authority_breaches"] for r in records if r["policy"]=="certificate_conditional"):
        raise AssertionError("correct control fails registered contract")
    groups={}
    for r in records:
        key=json.dumps(r["contract"],sort_keys=True)
        groups.setdefault(key,r["initial_observation"])
        if groups[key]!=r["initial_observation"]:
            raise AssertionError("initial packet leaks realized need or policy")
    names=("necessity_resource_probe.py","necessity_resource_probe_verifier.py","necessity_resource_probe_calibration.py")
    return {"stage":"offline calibration of prospectively registered model-unqueried family",
            "model_calls":0,"independent_folds":len(records),"records":records,
            "source_sha256_normalized_lf":{n:hashlib.sha256((root/"benchmark"/n).read_bytes().replace(b"\r\n",b"\n")).hexdigest() for n in names},
            "limits":["Offline controls, no new model outcomes or originality proof.","Public calibration does not establish contamination-free confirmation.","Native adapter, analysis, comparator and price freeze remain incomplete."]}


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",default="reviews/necessity-resource-probe-calibration.json")
    a=p.parse_args();Path(a.output).write_text(json.dumps(calibrate(),indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
