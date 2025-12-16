#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'
$env:COMPOSE_BAKE = 'true'
docker compose run --build --rm --remove-orphans --name gitx gitx-cli @args
