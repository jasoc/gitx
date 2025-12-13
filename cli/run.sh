#!/usr/bin/env bash

if [ ! -d "./venv" ]
then
    python -m venv ./venv
    source ./venv/bin/activate
    pip install -e .
else
    source ./venv/bin/activate
fi

exec gitx "$@"