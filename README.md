# WES HPC Documentation
I suggest using find and replace to replace {username} with your HPC username if you are going to use this doc.
## Current State
With the work that has been currently done, we are currently able to run a version of the CReSCENT pipeline `Script/Runs_Seurat_v3.R` (which is without minio) using WES and toil in HPC when the request is made from the same node that WES is running on. The dependancies for the pipeline are achieved by creating a conda environment with all the dependancies loaded and using that environment to run the WES server. This environment is effectively 'passed' to Torque jobs created by toil.

## Changes to the R Script
There were several changes made to the R script to accommodate the HPC environment:
- Disable parallelization due to an HPC bug where subtasks that inherit the memory limit of a job are counted as different jobs, thus multiplying the total memory requested even though that memory is not actually requested or used. This issue seems to be local to the SickKids HPC as per Javier's tests.
- Disable pdftk due to not being able to install a suitable version in the environment.
- Forced script to use UMAP over new default native R equivalent r-uwot. This is because the pipeline is tested and confirmed to work with UMAP and the change requires looking into.  

These are the changes in `Script/Runs_Seurat_v3.R`
## Environment Creation
First you must install miniconda. Here is a guide: https://docs.conda.io/en/latest/miniconda.html. Make sure the location is in your home directory
```bash
# Create the env
conda create --name testEnv
# Activate it
conda activate testEnv
# Install python 3.7.6
conda install python=3.7.6
# This should result in the following
which python
~/miniconda3/envs/testEnv/bin/python
# Install WES
pip install werkzeug==0.16.1
pip install wes-service
# Install toil and cwltool
pip install -I toil==3.24.0
pip install cwltool
# Install R and a bunch of R libraries
conda config --add channels conda-forge
conda update -n base conda
conda update --all
conda install --strict-channel-priority R=3.6
conda install hdf5
conda install -c conda-forge umap-learn
# This next one is gonna take about an hour
Rscript Script/install-base.R
# There is a limit of 10GB in your home dir, but I found that it doesn't matter until you go over ~22GB. Regardless, use the following to clear conda cache
conda clean -p
# This lets you check your space usuage easily
du -h ~ --max-depth=1
```

## Specific Toil and WES Modifications
Some changes to WES and toil code were needed to make this work. The changes are to `util.py` and `torque.py`. The changed files are given but some modifications will need to be made:
- In `util.py` line 53, change the directory to your home directory. This change was to move the tmp dirs created by WES to a location that all jobs and WES will have access to always.  

After you have made the above change, run the following two commands:
```bash
# Replace toil's torque.py with our own
cp torque.py ~/miniconda3/envs/testEnv/lib/python3.7/site-packages/toil/batchSystems/torque.py
# Replace WES's util.py with our own
cp util.py ~/miniconda3/envs/Renv5/lib/python3.7/site-packages/wes_service/util.py
```

Here is a list of all the other changes to the files for reference:
- In `torque.py` in `getJobExitCode()` the parsing torqueJobID was made to work (it didn't parse properly). The modified line is:  
  ```python
  args = ["qstat", "-f", str(torqueJobID).split('.')[0].strip(" b'n\\")]
  ```
- In `torque.py` in `getJobExitCode()` the use of stdout.readlines() was changed to work. The modified lines are:  
  ```python
  process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)  
  jobInfo=process.stdout.readlines()
  for line in jobInfo:
  ```
- In `torque.py` in `generateTorqueWrapper()` the resource limits were set manually because toil's built in method of passing resource limits for jobs does not work. This should not be a problem as the pipeline does not have a means of variably seting memory limits anyway, so all run pipelines can just use the same high memory limit. The modified lines are:
  ```python
  fh.write("#PBS -l vmem=30g,mem=30g,nodes=1:ppn=2\n")
  fh.write("cd $PBS_O_WORKDIR\n\n")
  ```

## Running Tests
We will need a pseudo tmp dir for toil and WES
```bash
mkdir ~/tmp
```
Before running the tests you must complete the Environment Creation and Specific Toil and WES Modifications sections of this doc.
### WES Pipeline Test
The most general test is if the pipeline runs through WES and toil. To do this get two ssh sessions on the same HPF node (trial and error) and do the following in the first session:
```bash
# Use the env
conda activate testEnv
# Set some env vars for toil, replace {username} with your username
# Setting -e and -o are mandatory for toil to be able to submit the job, otherwise the job fails with status -9
export TOIL_TORQUE_ARGS="-d /home/{username} -e /home/{username} -o /home/{username}"
export TOIL_TORQUE_REQS="walltime=0:15:00"
# Start the WES server, replace {username} with your username
wes-server --port=8081 --backend=wes_service.cwl_runner --opt=runner=cwltoil --opt=extra=--writeLogs=/home/{username}/ --opt=extra=--no-container --opt=extra=--batchSystem=Torque --opt=extra=--realTimeLogging --opt=extra=--logDebug --opt=extra=--workDir=/home/{username}/ --opt=extra=--tmpdir-prefix=/home/{username}/tmp/
```
Now on the other session
```bash
# Activate the env so we have wes_client library
conda activate testEnv
# Make the call to submit the workflow
python Call.py
# Check that the job has submitted
qstat -u {username}
```
If successful, the outputs will be in `~/workflows/{ID}/outdir/SEURAT/`. You can find the ID by running
```bash
curl http://127.0.0.1:8081/ga4gh/wes/v1/runs
```
Warning: This will create many unwanted files in your home directory.
### Toil Pipeline Test
This test runs the pipeline using toil but not WES. Run: 
```bash
# Use the env
conda activate testEnv
# Set some env vars for toil, replace {username} with your username
# Setting -e and -o are mandatory for toil to be able to submit the job, otherwise the job fails with status -9
export TOIL_TORQUE_ARGS="-d /home/{username} -e /home/{username} -o /home/{username}"
export TOIL_TORQUE_REQS="walltime=0:15:00"
# Run the pipeline
toil-cwl-runner --logDebug --writeLogs /home/{username}/ --realTimeLogging --batchSystem Torque --workDir /home/{username}/ --no-container --tmpdir-prefix /home/{username}/tmp/ tool.cwl job.json
# Check that the job has submitted
qstat -u {username}
```
If successful, the outputs will be in `~/SEURAT/`  
Warning: This will create many unwanted files in your home directory.
### R Script in Torque Job Test
This tests the ability for the R script to run on a compute node by sumbiting a simple job to run the R script. Before testing please edit `testJob.sh`and change the paths appropriately for your account. Once that is done run:
```bash
# Submit the job
qsub -l nodes=1:ppn=2,vmem=30g,mem=30g,walltime=0:10:00 testJob.sh
# Check that the job has submitted
qstat -u {username}
```
If successful, the outputs will be in `~/SEURAT/`
### R Script Test
This test runs the R script on its own, without toil or WES. Run:
```bash
# Run the script
Rscript /home/{username}/Script/Runs_Seurat_v3.R -i /home/{username}/inputs/ -t MTX -r 1 -p frontend_example_mac_10x_cwl -s n -d 10 -m 0,0.2 -n 50,8000 -w Y -o N
```
If successful, the outputs will be in `~/SEURAT/`
