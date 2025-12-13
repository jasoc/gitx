#!/usr/bin/sh

if [ ! -d "node_modules" ]; then
    docker compose run --rm gitx-web npm install
fi

docker compose run --rm gitx-web npm start