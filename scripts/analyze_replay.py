import asyncio
from functools import wraps
import glob

import click
from loguru import logger
from s2clientprotocol import sc2api_pb2 as sc_pb
from sc2.client import Client
from sc2.protocol import ProtocolError
from sc2.sc2process import SC2Process
from tqdm import tqdm

from spy_sc2.replay import ReplayMetadata
from spy_sc2.observation_writer import ObservationWriter
from spy_sc2.utils import update_battle_net_cache


def async_command(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper

@click.command
@click.argument("replay-glob", type=str)
# "C:\\ProgramData\\Blizzard Entertainment\\Battle.net"
# "/root/StarCraftII/Battle.net"
@click.option("--battlenet-cache", type=click.Path(exists=True, file_okay=False))
@click.option("--game-step", type=int, default=1)
@click.option("--fullscreen", type=bool, default=False)
@click.option("--realtime", type=bool, default=False)
@async_command
async def main(
    replay_glob: str,
    battlenet_cache: str,
    game_step: int,
    fullscreen: bool,
    realtime: bool,
) -> None:


    logger.disable("sc2")

    logger.info(f"{replay_glob=}")
    replay_paths = glob.glob(replay_glob)
    logger.info(f"{replay_paths=}")

    for replay_path in replay_paths:
        dataset_file = replay_path + ".parquet"

        if battlenet_cache:
            update_battle_net_cache([replay_path], battlenet_cache)

        with open(replay_path, "rb") as f:
            replay_data = f.read()

        metadata = ReplayMetadata.from_bytes(replay_data)
        logger.info(f"{metadata=}")

        ifopts = sc_pb.InterfaceOptions(
            raw=True,
            score=True,
            show_cloaked=True,
            raw_affects_selection=True,
            raw_crop_to_playable_area=False,
        )

        with ObservationWriter(dataset_file) as writer:
            for player_id in [1, 2]:
                async with SC2Process(
                    fullscreen=fullscreen, base_build=metadata.base_build, data_hash=metadata.data_version
                ) as server:
                    client = Client(server._ws)
                    client.game_step = game_step
                    await server._execute(
                        start_replay=sc_pb.RequestStartReplay(
                            replay_data=replay_data,
                            observed_player_id=player_id,
                            realtime=realtime,
                            options=ifopts,
                        )
                    )

                    game_loops = range(0, metadata.game_loops, client.game_step)
                    for _ in tqdm(game_loops, desc=f"{replay_path=}, {player_id=}"):
                        state = await client.observation()
                        writer.write_observation(state.observation.observation, player=player_id)
                        try:
                            await client.step()
                        except ProtocolError as error:
                            logger.error(f"Replay ended unexpectedly with {error=}")
                            break


if __name__ == "__main__":
    main()
