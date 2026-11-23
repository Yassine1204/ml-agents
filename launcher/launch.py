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