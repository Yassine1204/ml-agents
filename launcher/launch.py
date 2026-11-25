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
        return [{name: kind(row[name]) for name, kind in TYPES.items()} for row in rows] #Here we read from the run_plan the settings, and send them to main where they will be bundled into separate runs
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
    behavior["network_settings"]["hidden_units"] = run["hidden_units"]
    behavior["network_settings"]["num_layers"] = run["num_layers"]
    behavior["max_steps"] = run["max_steps"]

    out_dir.mkdir(parents=True, exist_ok=True) #makes the folder where all the edited yaml files will be in
    out_path = out_dir / f"{run['run_id']}.yaml" #builds file name of the copy

    with open(out_path, "w") as f: #w just means replacing the file if it exists
        yaml.safe_dump(cfg, f, sort_keys=False) #here we write the edited version of yaml down
    
    return out_path


def build_command(run, yaml_path, exe, log_path): #Here we make the command that we earlier had to type out by hand each time.
    return [
        "mlagents-learn" , str(yaml_path),
        f"--run-id={run['run_id']}",
        f"--env={exe}",
        f"--seed={run['seed']}",
        "--env-args", "-logfile", str(log_path), #log path logs the run and we can consult it if something goes wrong to see what went wrong
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    plan_file = "launcher/run_plan.csv" #where it all starts
    machine_file = "launcher/machine.json"

    with open(machine_file) as f:
        machine = json.load(f) #stores the machine file now
    base_yaml = machine["base_yaml"] #path to the master YAML file from where will be making copies
    exe = machine["build"] #path to the executable of the Unity scene we use for runs


    
    results_dir = Path("results") #folder where results about run are saved
    logs_dir = Path("logs") #folder where logs about run are saved
    yaml_dir = Path("config/poca/runs") #folder where all the yaml versions are


    runs = read_plan(plan_file) #We get all the runs from the csv run_plan and start passing them out





    bad = 0 #counts amount of faulty runs. Should be 0
    seen = set()
    if not Path(exe).exists(): #This checks if there is a path to the Unity Executable build
        sys.exit(f"Build path isn't correct: {exe}\n");
    
    for run in runs: #Now we are just going to check each run read from the run_plan with the three checks in the check_run function
        problems = check_run(run)
        if run["run_id"] in seen:
            problems.append("run_id appears two times in the run plan.")
        seen.add(run["run_id"]) #so we can check for doubles
        

        for p in problems: #Now exposing all the errors of a particular run so we know what is gonig on
            print(f"Problem {run['run_id']}: {p}")
        bad += bool(problems)

    if bad: #if problems have been found
        sys.exit(f"\n{bad} runs are not good")
    else:
        print("Plan is oke.")

    
    #Here we start with the runs:
    started = []
    skipped = []
    failed = []

    try:
        for run in runs:
            run_id = run["run_id"]
            if(results_dir / run_id).exists(): #check if run already done. If yes we are going to ignore it
                skipped.append(run_id)
                print(f"Skip {run_id} because it already exists in the result folder")
                continue #skip this run in loop

            yaml_path = write_yaml(run, base_yaml, yaml_dir) #makes and returns the path to the special version yaml for this particular run
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_path = (logs_dir / f"{run_id}.log").resolve() #resolve gives full address, which is needed for Unity build which starts from its own folder

            command = build_command(run, yaml_path, log_path)

            print(f"{run_id}")

            if args.run: #real run
                code = subprocess.run(command).returncode #starts the run
                if code != 0:
                    failed.append(run_id)
                else:
                    started.append(run_id)
            else: #dry run just for testing
                started.append(run_id)
    
    except KeyboardInterrupt: #allows for us to stop this all if we want to
        print("\n You have interrupted the runs. Nothing else will be started")

    #The final balance sheet. We have the dry mode which says would run instead of finished
    print(f"Final result: {'finished' if args.run else 'would run'}={started} skipped{skipped} failed={failed}")


#This is the starting button to all the rest:
if __name__ == "__main__":
    main()