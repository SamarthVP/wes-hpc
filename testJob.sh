#!/bin/sh
export PATH=$PATH:/home/svpatel/miniconda3/envs/Renv5/bin/
Rscript /home/svpatel/Script/Runs_Seurat_v3.R -i /home/svpatel/inputs/ -t MTX -r 1 -p frontend_example_mac_10x_cwl -s n -d 10 -m 0,0.2 -n 50,8000 -w Y -o N
