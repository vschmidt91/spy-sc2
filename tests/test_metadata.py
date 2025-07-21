from unittest import TestCase

from spy_sc2.replay import Replay


class TestMetadata(TestCase):
    def test_basic(self):
        with open("resources/replays/3901860_Sharkling_PhantomBot_EphemeronAIE.SC2Replay", "rb") as f:
            replay_data = f.read()
        metadata = Replay(replay_data)
        self.assertEqual(6228, metadata.game_loops)
        self.assertEqual("EphemeronAIE.SC2Map", metadata.map_name)
        self.assertEqual("B89B5D6FA7CBF6452E721311BFBC6CB2", metadata.data_version)
        self.assertEqual("Base75689", metadata.base_build)
        self.assertEqual(1, metadata.players[0]["PlayerID"])
        self.assertEqual("Zerg", metadata.players[0]["AssignedRace"])
        self.assertEqual(2, metadata.players[1]["PlayerID"])
        self.assertEqual("Zerg", metadata.players[1]["AssignedRace"])

    def test_battle_net_cache(self):
        with open(
            "resources/replays/252bacf5e80baa2f3691f75d4d4239c8459606d42cfe2eb7123dd9bc5ef83fac.SC2Replay", "rb"
        ) as f:
            replay_data = f.read()
        metadata = Replay(replay_data)
        metadata.update_battle_net_cache("C:\\ProgramData\\Blizzard Entertainment\\Battle.net")
