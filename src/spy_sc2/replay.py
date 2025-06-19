from collections import Counter
import contextlib
import json
from collections.abc import Mapping, Set
from dataclasses import dataclass
from io import BytesIO

from mpyq import MPQArchive
from s2clientprotocol.sc2api_pb2 import Observation
from s2protocol import versions
from sc2.data import Result

REPLAY_TYPE_ENCODING = "utf-8"


@dataclass(frozen=True, slots=True)
class ReplayUnit:
    player: int
    type: int


@dataclass(frozen=True, slots=True)
class ReplayUpgrade:
    player: int
    type: int


@dataclass(frozen=True, slots=True)
class ReplayStep:
    units: Mapping[int, ReplayUnit]
    upgrades: Set[ReplayUpgrade]

    def player_compositions(self) -> Mapping[int, Mapping[int, int]]:
        return {player: Counter(u.type for u in self.units.values() if u.player == player) for player in [0, 1, 2]}

    def player_upgrades(self) -> Mapping[int, Set[int]]:
        return {player: {u.type for u in self.upgrades if u.player == player} for player in [0, 1, 2]}

    @classmethod
    def from_observation(cls, observation: Observation) -> "ReplayStep":
        player_id = observation.player_common.player_id
        return ReplayStep(
            units={u.tag: ReplayUnit(u.owner, u.unit_type) for u in observation.raw_data.units},
            upgrades={ReplayUpgrade(player_id, u) for u in observation.raw_data.player.upgrade_ids},
        )


@dataclass(frozen=True, slots=True)
class ReplayMetadata:
    base_build: str
    data_version: str
    game_loops: int
    map: str
    player_races: Mapping[int, str]

    @classmethod
    def from_bytes(cls, replay_bytes: bytes) -> "ReplayMetadata":
        replay_io = BytesIO()
        replay_io.write(replay_bytes)
        replay_io.seek(0)
        return cls.from_archive(MPQArchive(replay_io))

    @classmethod
    def from_file(cls, replay_path: str) -> "ReplayMetadata":
        return cls.from_archive(MPQArchive(replay_path))

    @classmethod
    def from_archive(cls, archive: MPQArchive) -> "ReplayMetadata":
        header = versions.latest().decode_replay_header(archive.header["user_data_header"]["content"])
        game_loops = header["m_elapsedGameLoops"]
        metadata = json.loads(archive.extract()[b"replay.gamemetadata.json"].decode(REPLAY_TYPE_ENCODING))
        base_build = header["m_version"]["m_baseBuild"]

        protocol = versions.build(base_build)
        details_file = archive.read_file("replay.details") or archive.read_file("replay.details.backup")
        details = protocol.decode_replay_details(details_file)
        players = details["m_playerList"]
        map_name = details["m_mapFileName"].decode(REPLAY_TYPE_ENCODING)
        player_races = {1 + p["m_teamId"]: p["m_race"].decode(REPLAY_TYPE_ENCODING) for p in players}

        return cls(metadata["BaseBuild"], metadata["DataVersion"], game_loops, map_name, player_races)


@dataclass(frozen=True, slots=True)
class Replay:
    steps: Mapping[int, ReplayStep]
    game_loops: int
    map: str
    player_races: Mapping[int, str]

    @classmethod
    def from_bytes(cls, replay_bytes: bytes) -> "Replay":
        replay_io = BytesIO()
        replay_io.write(replay_bytes)
        replay_io.seek(0)
        return Replay.from_archive(MPQArchive(replay_io))

    @classmethod
    def from_file(cls, replay_path: str) -> "Replay":
        return Replay.from_archive(MPQArchive(replay_path))

    @classmethod
    def from_archive(cls, archive: MPQArchive) -> "Replay":
        header = versions.latest().decode_replay_header(archive.header["user_data_header"]["content"])
        game_loops = header["m_elapsedGameLoops"]
        base_build = header["m_version"]["m_baseBuild"]
        protocol = versions.build(base_build)
        details_file = archive.read_file("replay.details") or archive.read_file("replay.details.backup")
        details = protocol.decode_replay_details(details_file)
        players = details["m_playerList"]
        map_name = details["m_mapFileName"].decode(REPLAY_TYPE_ENCODING)
        player_races = {1 + p["m_teamId"]: p["m_race"].decode(REPLAY_TYPE_ENCODING) for p in players}

        tracker_events = list(protocol.decode_replay_tracker_events(archive.read_file("replay.tracker.events")))

        steps = dict[int, ReplayStep]()
        units = dict[int, ReplayUnit]()
        upgrades = set[ReplayUpgrade]()
        game_loop = 0

        for event in tracker_events:
            event_type = event["_event"]
            event_game_loop = event["_gameloop"]

            if event_game_loop != game_loop:
                steps[game_loop] = ReplayStep(units.copy(), upgrades.copy())
                game_loop = event_game_loop

            try:
                unit_tag = protocol.unit_tag(event["m_unitTagIndex"], event["m_unitTagRecycle"])
            except KeyError:
                unit_tag = 0

            unit_type = event.get("m_unitTypeName", b"").decode(REPLAY_TYPE_ENCODING).upper()
            player = event.get("m_upkeepPlayerId", -1)

            if event_type == "NNet.Replay.Tracker.SPlayerSetupEvent":
                pass
            elif (
                event_type == "NNet.Replay.Tracker.SUnitBornEvent" or event_type == "NNet.Replay.Tracker.SUnitInitEvent"
            ):
                if unit_type.startswith("Beacon"):
                    pass
                else:
                    units[unit_tag] = ReplayUnit(player, unit_type)
            elif event_type == "NNet.Replay.Tracker.SUnitDiedEvent":
                with contextlib.suppress(KeyError):
                    del units[unit_tag]
            elif event_type == "NNet.Replay.Tracker.SUpgradeEvent":
                upgrade_type = event["m_upgradeTypeName"].decode(REPLAY_TYPE_ENCODING).upper()
                if upgrade_type.startswith("Spray"):
                    pass
                else:
                    upgrades.add(ReplayUpgrade(event["m_playerId"], upgrade_type))
            elif event_type == "NNet.Replay.Tracker.SPlayerStatsEvent":
                pass
            elif event_type == "NNet.Replay.Tracker.SUnitTypeChangeEvent":
                units[unit_tag] = ReplayUnit(units[unit_tag].player, unit_type)
            elif (
                event_type == "NNet.Replay.Tracker.SUnitDoneEvent"
                or event_type == "NNet.Replay.Tracker.SUnitPositionsEvent"
            ):
                pass
            elif event_type == "NNet.Replay.Tracker.SUnitOwnerChangeEvent":
                units[unit_tag] = ReplayUnit(player, units[unit_tag].type)
            else:
                raise TypeError(event_type)

        return Replay(steps, game_loops, map_name, player_races)


@dataclass(frozen=True, slots=True)
class Report:
    opponent_id: str
    result: Result
    replay_observer: Replay
    replays_bot: Mapping[int, Replay]
