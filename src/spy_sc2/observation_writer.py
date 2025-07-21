from collections.abc import Iterable, Sequence

import pyarrow
from pyarrow.parquet import ParquetWriter
from s2clientprotocol.sc2api_pb2 import Observation


class ObservationWriter:
    def __init__(self, path: str, include_neutrals) -> None:
        self.include_neutrals = include_neutrals
        self.stats_schema = pyarrow.schema(
            [
                ("game_loop", pyarrow.int32()),
                ("army_count", pyarrow.int16()),
                ("food_army", pyarrow.int16()),
                ("food_cap", pyarrow.int16()),
                ("food_used", pyarrow.int16()),
                ("food_workers", pyarrow.int16()),
                ("idle_worker_count", pyarrow.int16()),
                ("larva_count", pyarrow.int16()),
                ("minerals", pyarrow.int32()),
                ("player", pyarrow.int8()),
                ("vespene", pyarrow.int32()),
                ("warp_gate_count", pyarrow.int16()),
            ]
        )
        self.unit_schema = pyarrow.schema(
            [
                ("game_loop", pyarrow.int32()),
                ("player", pyarrow.int8()),
                ("owner", pyarrow.int8()),
                ("tag", pyarrow.int64()),
                ("unit_type", pyarrow.int32()),
                ("ability", pyarrow.int32()),
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
        self.stats_path = path + ".stats.parquet"
        self.unit_path = path + ".units.parquet"
        self.upgrade_path = path + ".upgrades.parquet"
        self.writer_options = dict(
            compression="zstd",
            compression_level=9,
            use_byte_stream_split=True,
        )

    def __enter__(self) -> "ObservationWriter":
        self.stats_records = list[dict]()
        self.unit_records = list[dict]()
        self.upgrade_records = list[dict]()
        return self

    def _write_records(self, records: Sequence[dict], path: str, schema: dict) -> None:
        with ParquetWriter(path, schema, **self.writer_options) as writer:
            writer.write_table(pyarrow.Table.from_pylist(records, schema=schema))

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._write_records(self.stats_records, self.stats_path, self.stats_schema)
        self._write_records(self.unit_records, self.unit_path, self.unit_schema)
        self._write_records(self.upgrade_records, self.upgrade_path, self.upgrade_schema)

    def write_observation(self, observation: Observation, **kwargs) -> None:
        kwargs["game_loop"] = observation.game_loop
        self.stats_records.extend(self._get_stats_records(observation, **kwargs))
        self.unit_records.extend(self._get_unit_records(observation, **kwargs))
        self.upgrade_records.extend(self._get_upgrade_records(observation, **kwargs))

    def _get_stats_records(self, observation: Observation, **kwargs) -> Iterable[dict]:
        yield {
            "army_count": observation.player_common.army_count,
            "food_army": observation.player_common.food_army,
            "food_cap": observation.player_common.food_cap,
            "food_used": observation.player_common.food_used,
            "food_workers": observation.player_common.food_workers,
            "idle_worker_count": observation.player_common.idle_worker_count,
            "larva_count": observation.player_common.larva_count,
            "minerals": observation.player_common.minerals,
            "player": observation.player_common.player_id,
            "vespene": observation.player_common.vespene,
            "warp_gate_count": observation.player_common.warp_gate_count,
            **kwargs,
        }

    def _get_unit_records(self, observation: Observation, **kwargs) -> Iterable[dict]:
        for unit in observation.raw_data.units:
            if not self.include_neutrals and unit.owner not in {1, 2}:
                continue
            yield {
                "owner": unit.owner,
                "tag": unit.tag,
                "unit_type": unit.unit_type,
                "ability": unit.orders[0].ability_id if unit.orders else 0,
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
