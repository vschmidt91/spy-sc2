# spy-sc2

A Starcraft II Replay Analysis Toolbox

## Prerequisites

- Docker
- Poetry

StarCraft II installation is not required, the headless game will be downloaded during build.

## Installation

None.

## Quickstart

- Place replays in `resources/replays`
- Place map files in `resources/maps` (if needed)

Spawn one container per replay file and convert the obvservations to `.parquet` file:

```sh
./scripts/analyze_replays.sh
```