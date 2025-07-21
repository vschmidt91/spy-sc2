import glob

import click
from loguru import logger
from sc2.protocol import ProtocolError
from tqdm.asyncio import tqdm

from spy_sc2.observation_writer import ObservationWriter
from spy_sc2.replay import Replay
from spy_sc2.utils import CommandWithConfigFile, async_command


@click.command(cls=CommandWithConfigFile("config"))
@click.option("--config", type=click.File("rb"))
@click.argument("replay-glob", type=str)
@click.option("--battlenet-cache", type=click.Path(exists=True, file_okay=False))
@click.option("--game-step", type=int, default=1)
@click.option("--fullscreen", type=bool, default=False)
@click.option("--realtime", type=bool, default=False)
@async_command
async def main(
    config,
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

        with open(replay_path, "rb") as f:
            replay_data = f.read()

        metadata = Replay(replay_data)

        if battlenet_cache:
            metadata.update_battle_net_cache(battlenet_cache)

        with ObservationWriter(dataset_file) as writer:
            for player_id in [1, 2]:
                observations = metadata.read_observations(
                    player_id,
                    game_step=game_step,
                    fullscreen=fullscreen,
                    realtime=realtime,
                )
                try:
                    async for observation in tqdm(
                        observations, desc=f"{replay_path=}, {player_id=}", total=metadata.game_loops // game_step
                    ):
                        writer.write_observation(observation, player=player_id)
                except ProtocolError as error:
                    logger.error(f"Replay ended unexpectedly with {error=}")
                    break


if __name__ == "__main__":
    main()
