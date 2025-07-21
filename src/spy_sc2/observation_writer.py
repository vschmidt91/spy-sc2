from collections.abc import Iterable

import pyarrow
from pyarrow.parquet import ParquetWriter
from s2clientprotocol.sc2api_pb2 import Observation


class ObservationWriter:
    def __init__(self, path: str, batch_size: int | None = None) -> None:
        self.batch_size = batch_size
        self.unit_schema = pyarrow.schema(
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
        self.upgrade_schema = pyarrow.schema(
            [
                ("game_loop", pyarrow.int32()),
                ("player", pyarrow.int8()),
                ("upgrade", pyarrow.int32()),
            ]
        )
        self.unit_path = path + ".units.parquet"
        self.upgrade_path = path + ".upgrades.parquet"
        self.writer_options = dict(
            compression="zstd",
            compression_level=9,
            use_byte_stream_split=True,
        )

    def __enter__(self) -> "ObservationWriter":
        self.unit_writer = ParquetWriter(self.unit_path, self.unit_schema, **self.writer_options)
        self.upgrade_writer = ParquetWriter(self.upgrade_path, self.upgrade_schema, **self.writer_options)
        self.unit_records = list[dict]()
        self.upgrade_records = list[dict]()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._flush()
        self.unit_writer.close()
        self.upgrade_writer.close()

    def _flush(self) -> None:
        if self.unit_records:
            self.unit_writer.write_table(pyarrow.Table.from_pylist(self.unit_records, schema=self.unit_schema))
            self.unit_records.clear()
        if self.upgrade_records:
            self.upgrade_writer.write_table(pyarrow.Table.from_pylist(self.upgrade_records, schema=self.upgrade_schema))
            self.upgrade_records.clear()

    def write_observation(self, observation: Observation, **kwargs) -> None:
        self.unit_records.extend(self._get_unit_records(observation, game_loop=observation.game_loop, **kwargs))
        self.upgrade_records.extend(self._get_upgrade_records(observation, game_loop=observation.game_loop, **kwargs))

    def _get_unit_records(self, observation: Observation, **kwargs) -> Iterable[dict]:
        for unit in observation.raw_data.units:
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

    def _get_upgrade_records(self, observation: Observation, **kwargs) -> Iterable[dict]:
        for uprade in observation.raw_data.player.upgrade_ids:
            yield {
                "upgrade": uprade,
                **kwargs,
            }
