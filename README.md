# spy-sc2

A Starcraft II Replay Analysis Toolbox

Currently it is extracting the two player perspectives because that's what I needed, but the observer POV could also be added.
The purpose of this tool is to parse replays and output datasets in a format that is easy to use with `sklearn`, `torch` etc.
THe format of choice is Parquet using `pyarrow`.

## Prerequisites

- Docker

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
