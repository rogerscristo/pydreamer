#!/bin/bash
source /home/rogers/anaconda3/etc/profile.d/conda.sh
conda activate dreamerv2
x=1
while [ $x -le 30 ]
do
  python train.py --configs defaults gympybulletdrones hover_aviary_dreamer --run_name gympybulletdrones_3 --resume_id 14
done