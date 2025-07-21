# spy-sc2

A Starcraft II Replay Analysis Toolbox

Currently it is extracting the two player perspectives because that's what I needed, but the observer POV could also be added.
The purpose of this tool is to parse replays and output datasets in a format that is easy to use with `sklearn`, `torch` etc.
The format of choice is Parquet using `pyarrow`.

## Prerequisites

- Docker
- StarCraft II (only for local setup)

The Docker image will download headless StarCraft II during build.

## Installation

None when using Docker.

### Local Setup

Required: 
- Python 3.11 or 3.12

Setup the environment, e.g. with:
```sh
python -m venv .venv
source .venv/bin/activate
```
or using [poetry](https://python-poetry.org/):
```sh
poetry env use 3.11
```

Install in editable mode:
```sh
pip install -e .[test]
```

## Quickstart

- Place replays in `resources/replays`
- Place map files in `resources/maps` (if needed)

Spawn one container per replay file and convert the obvservations to `.parquet` file:

```sh
scripts/analyze_replays.sh
```

## Local Start

```sh
python scripts/analyze_replay.py --config=config/debug.toml resources/replays/252bacf5e80baa2f3691f75d4d4239c8459606d42cfe2eb7123dd9bc5ef83fac.SC2Replay
```