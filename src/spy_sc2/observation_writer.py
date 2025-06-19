import pandas as pd
from s2clientprotocol.sc2api_pb2 import Observation
import pyarrow
from pyarrow.parquet import ParquetWriter

from collections.abc import Iterable


class ObservationWriter:
    def __init__(self, path: str) -> None:
        self.schema = pyarrow.schema(
            [
                ("game_loop", pyarrow.int32()),
                ("player", pyarrow.int8()),
                ("owner", pyarrow.int8()),
                ("tag", pyarrow.int64()),
                ("unit_type", pyarrow.int32()),
                ("x", pyarrow.float32()),
                ("y", pyarrow.float32()),
                ("health", pyarrow.float32()),
                ("shield", pyarrow.float32()),
            ]
        )
        self.path = path

    def __enter__(self) -> "ObservationWriter":
        self.writer = ParquetWriter(self.path, self.schema)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.writer.close()

    def write_observation(self, observation: Observation, **kwargs) -> None:
        records = self._get_records(observation, game_loop=observation.game_loop, **kwargs)
        table = pyarrow.table(pd.DataFrame.from_records(records), schema=self.schema)
        self.writer.write_table(table)

    def _get_records(self, observation: Observation, **kwargs) -> Iterable[dict]:
        for unit in observation.raw_data.units:
            if unit.owner in {1, 2}:
                yield {
                    "owner": unit.owner,
                    "tag": unit.tag,
                    "unit_type": unit.unit_type,
                    "x": unit.pos.x,
                    "y": unit.pos.y,
                    "health": unit.health,
                    "shield": unit.shield,
                    **kwargs,
                }