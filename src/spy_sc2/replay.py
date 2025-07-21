import binascii
import json
import os
from collections.abc import AsyncGenerator
from io import BytesIO
from urllib.error import HTTPError
from urllib.request import urlretrieve

from loguru import logger
from mpyq import MPQArchive
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol.sc2api_pb2 import Observation
from s2protocol import versions
from sc2.client import Client
from sc2.protocol import ProtocolError
from sc2.sc2process import SC2Process

REPLAY_TYPE_ENCODING = "utf-8"


def get_depot_url(hash: str, cache_type: str) -> str:
    return f"https://eu-s2-depot.classic.blizzard.com/{hash}.{cache_type}"


class Replay:
    def __init__(self, replay_data: bytes) -> None:
        replay_io = BytesIO()
        replay_io.write(replay_data)
        replay_io.seek(0)
        archive = MPQArchive(replay_io)
        header = versions.latest().decode_replay_header(archive.header["user_data_header"]["content"])
        content = archive.extract()
        metadata = json.loads(content[b"replay.gamemetadata.json"].decode(REPLAY_TYPE_ENCODING))
        protocol = versions.build(header["m_version"]["m_baseBuild"])
        details_file = archive.read_file("replay.details") or archive.read_file("replay.details.backup")
        details = protocol.decode_replay_details(details_file)
        players = details["m_playerList"]

        self.replay_data = replay_data
        self.archive = archive
        self.cache_handles = details["m_cacheHandles"]
        self.map_name = details["m_mapFileName"].decode(REPLAY_TYPE_ENCODING)
        self.player_races = {1 + p["m_teamId"]: p["m_race"].decode(REPLAY_TYPE_ENCODING) for p in players}
        self.game_loops = header["m_elapsedGameLoops"]
        self.base_build = metadata["BaseBuild"]
        self.data_version = metadata["DataVersion"]

    async def read_observations(
        self,
        player_id: int,
        game_step=1,
        fullscreen=False,
        realtime=False,
    ) -> AsyncGenerator[Observation]:
        interface_options = sc_pb.InterfaceOptions(
            raw=True,
            score=True,
            show_cloaked=True,
            raw_affects_selection=True,
            raw_crop_to_playable_area=False,
        )
        async with SC2Process(
            fullscreen=fullscreen,
            base_build=self.base_build,
            data_hash=self.data_version,
        ) as server:
            client = Client(server._ws)
            client.game_step = game_step
            await server._execute(
                start_replay=sc_pb.RequestStartReplay(
                    replay_data=self.replay_data,
                    observed_player_id=player_id,
                    realtime=realtime,
                    disable_fog=False,
                    options=interface_options,
                )
            )
            try:
                while True:
                    state = await client.observation()
                    yield state.observation.observation
                    await client.step()
            except ProtocolError:
                pass

    def update_battle_net_cache(self, battle_net_base: str) -> None:
        """Download the battle.net cache files needed by replays."""

        for cache_handle in self.cache_handles:
            cache_handle[4:8].decode("utf-8").strip("\x00 ")
            cache_hash = binascii.b2a_hex(cache_handle[8:]).decode("utf8")
            file_type = cache_handle[0:4].decode("utf8")

            cache_path = os.path.join(
                battle_net_base,
                "Cache",
                cache_hash[0:2],
                cache_hash[2:4],
                f"{cache_hash}.{file_type}",
            )

            url = get_depot_url(cache_hash, file_type)
            if os.path.exists(cache_path):
                logger.info(f"Skipping already existing {cache_path=}")
            else:
                cache_dir = os.path.dirname(cache_path)
                if not os.path.exists(cache_dir):
                    os.makedirs(cache_dir)
                logger.info(f"Downloading {url=}")
                try:
                    urlretrieve(url, cache_path)
                except HTTPError as error:
                    logger.error(f"Download error with {error=}")
