#!/usr/bin/env bash

if [ ! -d "./venv" ]
then
    python -m venv ./venv
fi
source ./venv/bin/activate

python -m pip install build
python -m build --wheel --outdir dist/ .