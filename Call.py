import sys
import json
from wes_client import util
from wes_client.util import modify_jsonyaml_paths

pathToCWL = "/home/svpatel/"
pathToJob = "/home/svpatel/"
pathToInputs = "/home/svpatel/inputs/"

# open job file
inFile = open(pathToJob + "job.json", "r")
if inFile.mode == "r":
    job = inFile.read()

clientObject = util.WESClient(
    {'auth': '', 'proto': 'http', 'host': "localhost:8081"})

req = clientObject.run(
    pathToCWL + "tool.cwl", job, ['/home/svpatel/Script/Runs_Seurat_v3.R', pathToInputs + 'barcodes.tsv.gz', pathToInputs + 'features.tsv.gz', pathToInputs + 'matrix.mtx.gz'])
