import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
import yaml


#This defines the limits of the settings. It's a safety net so the launcher knows what is allowed.
# It stops a run with the wrong configurations instead of wasting a couple of hours. 
RANGES = { 
    "learning_rate": (),
    "batch_size": (),
    "hidden_units": (),
    "num_layers": (),
}

BEHAVIOR = "PushBlockCollab" #name of section where settings live. now launcher knows where to write new values in YAML file


#Any column that is not in here, it will be ignored
TYPES = {
    "run_id": str, "seed": int, "learning_rate": float, "batch_size": int, "buffer_size": int, "hidden_units": int, "num_layers": int, "max_steps": int

}



#This functions reads the run_plan.csv
def read_plan(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f, skipinitialspace=true))
    try:
        return [{name: kind(row[name]) for name, kind in TYPES.items()} for row in rows]
    except (KeyError, ValueError) as err:
        sys.exit(f"There is a problem in {path}: {error!r}.")



def check_run(run):
    problems = []
    for name, (low, high) in RANGES.items():
        if not low <= run[name] <= high: #checks if values are between edges.
            problems.append(f"{name}={run[name]} is outside of {low}..{high}")

    if run["buffer_size"] != run["batch_size"] * 10: #checks if buffer size is equal to ten times the batch_size. That is how we decide the buffer_size
        problems.append(f"buffer_size {run['buffer_size']} is not batch_size times ten. It must be = {run['batch_size']*10}")

    if run["max_steps"] <= 0: #max_steps can't be negative, so this alarms us if it is
        problems.append("max_steps can't be negative man")

    return problems


def write_yaml(run, base_yaml, out_dir): #This function will take the standard YAML file and change a couple of settings we want to change
    with open(base_yaml) as f: #base_yaml is determined by machine.json
        cfg = yaml.safe_load(f)
    
    behavior = cfg["behaviors"][BEHAVIOR] #we walk down two levels here
    #The next part writes in the changes we want to the copy YAML
    behavior["hyperparameters"]["learning_rate"] = run["learning_rate"]
    behavior["hyperparameters"]["batch_size"] = run["batch_size"]
    behavior["hyperparameters"]["buffer_size"] = run["buffer_size"]
    behavior["hyperparameters"]["hidden_units"] = run["hidden_units"]
    behavior["hyperparameters"]["num_layers"] = run["num_layers"]
    behavior["max_steps"] = run["max_steps"]

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run['run_id']}.yaml"

    with open(out_path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    
    return out_path
