#!/bin/bash

PROJECT_PATH=$(dirname -- "$(readlink -f -- "$0";)";)/..

rm -r $PROJECT_PATH/cli/.workspaces_debug
rm -r $PROJECT_PATH/cli/.config_debug
rm -r $PROJECT_PATH/cli/gitx.egg-info
rm -r $PROJECT_PATH/cli/venv
rm -r $PROJECT_PATH/cli/dist