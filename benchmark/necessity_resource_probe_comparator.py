"""Exact registered prefix comparison, partitioning only by public observations."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from benchmark.necessity_resource_probe import ProbeWorld,ProbeContract,ProbeEnvironment,TOOLS,MESSAGE
from benchmark.necessity_resource_probe_verifier import verify_probe
from benchmark.necessity_oracle import _solve,execute_policy


def compare():
    root=Path(__file__).resolve().parents[1]
    registration=json.loads((root/"plans/necessity-resource-probe-registration.json").read_text())
    protocol=(root/"plans/necessity-resource-probe-protocol.txt").read_bytes().replace(b"\r\n",b"\n")
    if hashlib.sha256(protocol).hexdigest()!=registration["protocol_source_sha256_normalized_lf"]:
        raise ValueError("registered protocol changed")
    contracts={}
    for cell in registration["base_cells"]:
        fields={k:v for k,v in cell.items() if k!="cell_id"}
        if hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(",",":")).encode()).hexdigest()!=cell["cell_id"]:
            raise ValueError("registered cell identity changed")
        c={k:cell[k] for k in ("reserve_capacity","deadline","probe_delay","max_calls")}
        contracts.setdefault(json.dumps(c,sort_keys=True),[]).append(ProbeWorld(cell["need"]))
    weights={"primary_loss":1,"protected_loss":0,"authority_breaches":1,
             "operation_cost":0,"false_outcome_claims":0}
    records=[];folds=0
    for key,worlds in contracts.items():
        contract=ProbeContract(**json.loads(key))
        if len(worlds)!=2 or {w.need for w in worlds}!={False,True}:
            raise ValueError("registered support must contain both need worlds")
        for prefix in ((),("consume_probe",)):
            def factory(world):
                env=ProbeEnvironment(world,contract)
                for tool in prefix:env.call(tool)
                return env
            groups={}
            for w in worlds:
                observation=json.dumps(factory(w).observe(),sort_keys=True)
                groups.setdefault(observation,[]).append(w)
            partitions=[];minimum=0
            for observation,support in groups.items():
                mass=len(support)/len(worlds)
                solved=_solve(contract,tuple(support),factory,TOOLS,weights,
                              [1/len(support)]*len(support),"resource-probe-prefix",100000)
                executions=[]
                for w in support:
                    env=factory(w);execute_policy(env,solved["policy"]);outcome=env.outcome()
                    if outcome!=verify_probe(w,contract,MESSAGE,env.events):
                        raise AssertionError("resource comparator independent fold mismatch")
                    executions.append({"world":asdict(w),"events":env.events,"outcome":outcome});folds+=1
                minimum+=mass*solved["expected_loss"]
                partitions.append({"public_observation":json.loads(observation),"prior_mass":mass,
                                   "comparator":solved,"executions":executions})
            records.append({"contract":asdict(contract),"prefix":list(prefix),
                            "minimum_expected_constraint_loss":minimum,
                            "feasible_zero_primary_and_authority":minimum==0,
                            "public_observation_partitions":partitions})
    names=("necessity_resource_probe_comparator.py","necessity_resource_probe.py",
           "necessity_resource_probe_verifier.py","necessity_oracle.py")
    return {"stage":"offline exact registered resource-probe prefix comparison","model_calls":0,
            "independent_folds":folds,"records":records,
            "source_sha256_normalized_lf":{n:hashlib.sha256((root/"benchmark"/n).read_bytes().replace(b"\r\n",b"\n")).hexdigest() for n in names},
            "limits":["Prefix observations may legitimately reveal need; partitions use those observations only.",
                      "Exactness conditional on finite transition and solver correctness, not formal verification.",
                      "Feasibility objective ignores operation cost; publish full vectors separately.",
                      "No model result, deployment prevalence or novelty established."]}


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",default="reviews/necessity-resource-probe-comparator.json")
    a=p.parse_args();Path(a.output).write_text(json.dumps(compare(),indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
