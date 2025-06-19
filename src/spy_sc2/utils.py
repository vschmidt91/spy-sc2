import binascii
import os
import urllib

import mpyq
from s2protocol import versions as s2versions

DEPOT_URL_TEMPLATE = "https://eu-s2-depot.classic.blizzard.com/{hash}.{type}"

def mkdirs(*paths):
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)
            
def update_battle_net_cache(replays, bnet_base):
    """Download the battle.net cache files needed by replays."""

    downloaded = 0
    failed = set()
    for replay_path in replays:
        try:
            archive = mpyq.MPQArchive(replay_path)
        except ValueError:
            print("Failed to parse replay:", replay_path)
            continue
        extracted = archive.extract()
        contents = archive.header["user_data_header"]["content"]
        header = s2versions.latest().decode_replay_header(contents)
        base_build = header["m_version"]["m_baseBuild"]
        prot = s2versions.build(base_build)

        details_bytes = extracted.get(b"replay.details") or extracted.get(b"replay.details.backup")
        details = prot.decode_replay_details(details_bytes)

        for map_handle in details["m_cacheHandles"]:
            # server = map_handle[4:8].decode("utf-8").strip("\x00 ")
            map_hash = binascii.b2a_hex(map_handle[8:]).decode("utf8")
            file_type = map_handle[0:4].decode("utf8")

            cache_path = os.path.join(bnet_base, "Cache", map_hash[0:2], map_hash[2:4], f"{map_hash}.{file_type}")

            url = DEPOT_URL_TEMPLATE.format(hash=map_hash, type=file_type)
            if not os.path.exists(cache_path) and url not in failed:
                mkdirs(os.path.dirname(cache_path))
                print(url)
                try:
                    urllib.request.urlretrieve(url, cache_path)
                except urllib.error.HTTPError as e:
                    print("Download failed:", e)
                    failed.add(url)
                else:
                    downloaded += 1
    return downloaded
