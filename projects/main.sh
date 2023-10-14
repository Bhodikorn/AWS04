#!/bin/bash
version="2.0.0"
message="====Rain Project==== 
version:$version

Welcome to the project. 
Select which task you want to run.
Or, You can provide [task] when calling this script.

Example: docker compose run --rm rain bash main.sh [task]

Task list
=========
- Clean
    This will clean 'temp' and 'log'
    [0]: clean
- Download
    [1]: download imerg
    [2]: download gsmap
- Preprocess
    [3]: preprocess imerg
    [4]: preprocess gsmap
- Label
    [5]: prepare label
    [6]: merge label
- Model
    [7]: train model
    [8]: predict
- Utility
    [9]: check download file

ctrl + D to exit

Select Task: "

# Check if there is $1 (argument) 555
if [ -z "$1" ]
then
    read -p "$message" task
else
    task=$1
fi

if [ -z "$task" ]
then
    echo "exit"
elif [ $task -eq 0 ]
then
    echo "Executing: [$task] clean"
    echo ""
    rm -r temp/*
    rm -r log/*
elif [ $task -eq 1 ] 
then
    echo "Executing: [$task] download imerg"
    echo ""
    python3 download_imerg.py
elif [ $task -eq 2 ] 
then
    echo "Executing: [$task] download gsmap"
    echo ""
    python3 download_gsmap_dat.py
elif [ $task -eq 3 ] 
then
    echo "Executing: [$task] preprocess imerg"
    echo ""
    python3 preprocess_imerg_multiband.py
elif [ $task -eq 4 ] 
then
    echo "Executing: [$task] preprocess gsmap"
    echo ""
    python3 preprocess_gsmap_dat_multiband.py
elif [ $task -eq 5 ] 
then
    echo "Executing: [$task] prepare label"
    echo ""
    python3 prepare_label.py
elif [ $task -eq 6 ] 
then
    echo "Executing: [$task] merge label"
    echo ""
    python3 merge_label.py
elif [ $task -eq 7 ] 
then
    echo "Executing: [$task] train model"
    echo ""
    python3 train_model.py
elif [ $task -eq 8 ] 
then
    echo "Executing: [$task] predict"
    echo ""
    python3 inference_parallel.py
elif [ $task -eq 9 ] 
then
    echo "Executing: [$task] check download file"
    echo ""
    python3 check_download.py
else
    echo "The numer you write is invalid"
fi