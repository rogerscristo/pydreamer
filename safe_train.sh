#!/bin/bash

set -env
EXIT_CODE=0
python train.py --configs=defaults --env_config=gympybulletdrones --experiment=hover_aviary_dreamer --run_name=gympybulletdrones_2 --resume_id=42 || EXIT_CODE=$?
echo $EXIT_CODE