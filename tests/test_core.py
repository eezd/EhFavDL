import os
import gc
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.ComicInfo import ComicInfo
from src.Config import Config
from src.DownloadArchiveGallery import DownloadArchiveGallery
from src.Watch import Watch
import src.Utils as utils_mod
from src.Utils import (
    clear_old_file,
    collect_gid_cbz_groups,
    get_web_gallery_download_list,
    move_path_with_collision,
    windows_escape,
    xml_escape,
)


def build_config_file(root: Path) -> Path:
    config_path = root / "config.yaml"
    db_path = root / "data.db"
    data_path = root / "data"
    config_text = f"""
cookies:
  ipb_member_id: 1
  ipb_pass_hash: test
  igneous: test
  sk: test
  hath_perks: test

User-Agent: UnitTestAgent/1.0

proxy:
  enable: False
  url: http://127.0.0.1:7890

dbs_name: {db_path.as_posix()}
data_path: {data_path.as_posix()}
website: exhentai.org
connect_limit: 3
tags_translation: False
prefer_japanese_title: True
lan_url: http://localhost:22299/
lan_api_psw: test
watch_fav_ids: 0,1
watch_lan_status: False
"""
    config_path.write_text(config_text.strip() + "\n", encoding="utf-8")
    return config_path


class CoreBehaviorTests(unittest.TestCase):
    def setUp(self):
        Config._config_cache.clear()
        Config._session_cache.clear()
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.config_path = build_config_file(self.root)
        self.config = Config(config_path=str(self.config_path))
        self.config.create_database()
        os.makedirs(self.config.gallery_path, exist_ok=True)
        os.makedirs(self.config.del_path, exist_ok=True)
        utils_mod.self = self.config

    def tearDown(self):
        utils_mod.self = None
        gc.collect()
        self.tmp.cleanup()
        Config._config_cache.clear()
        Config._session_cache.clear()

    def test_config_loads_custom_path(self):
        self.assertEqual(self.config.base_url, "exhentai.org")
        self.assertEqual(self.config.connect_limit, 3)
        self.assertTrue(self.config.gallery_path.endswith(os.path.join("data", "gallery")))

    def test_pure_helpers(self):
        self.assertEqual(windows_escape('a<b>c:d|e?f*g"h/i\t'), "abcdefghi")
        self.assertEqual(xml_escape('a & b < c > d " e \' f'), "a &amp; b &lt; c &gt; d &quot; e &apos; f")

    def test_collect_gid_groups(self):
        (self.root / "data" / "gallery" / "100-test.cbz").write_text("x", encoding="utf-8")
        (self.root / "data" / "gallery" / "100-test-1280x.cbz").write_text("x", encoding="utf-8")
        (self.root / "data" / "gallery" / "200-test.cbz").write_text("x", encoding="utf-8")

        originals, web_1280x = collect_gid_cbz_groups(self.config.gallery_path)
        self.assertEqual(sorted(originals.keys()), ["100", "200"])
        self.assertEqual(sorted(web_1280x.keys()), ["100"])
        self.assertEqual(originals["100"], ["100-test.cbz"])
        self.assertEqual(web_1280x["100"], ["100-test-1280x.cbz"])

    def test_clear_old_file_moves_and_deletes(self):
        src_file = self.root / "data" / "gallery" / "123-sample.cbz"
        src_file.write_text("payload", encoding="utf-8")
        with sqlite3.connect(self.config.dbs_name) as co:
            co.execute(
                "INSERT INTO fav_category(gid, token, fav_id, del_flag, original_flag, web_1280x_flag) VALUES (?,?,?,?,?,?)",
                (123, "token", 1, 0, 0, 0),
            )
            co.commit()

        clear_old_file([123])

        self.assertFalse(src_file.exists())
        moved_files = list((self.root / "data" / "del").glob("123-sample.cbz*"))
        self.assertTrue(moved_files)
        with sqlite3.connect(self.config.dbs_name) as co:
            row = co.execute("SELECT COUNT(*) FROM fav_category WHERE gid = 123").fetchone()[0]
        self.assertEqual(row, 0)

    def test_download_list_uses_title_jpn_and_filters(self):
        with sqlite3.connect(self.config.dbs_name) as co:
            co.execute(
                "INSERT INTO eh_data(gid, token, title, title_jpn, copyright_flag) VALUES (?,?,?,?,?)",
                (321, "abc", "English", "Japanese", 0),
            )
            co.execute(
                "INSERT INTO fav_category(gid, token, fav_id, del_flag, original_flag, web_1280x_flag) VALUES (?,?,?,?,?,?)",
                (321, "abc", 1, 0, 0, 0),
            )
            co.commit()

        dl_list = get_web_gallery_download_list(fav_cat="1")
        self.assertEqual(dl_list, [[321, "abc", "Japanese"]])

    def test_move_path_with_collision_appends_timestamp(self):
        src_file = self.root / "data" / "gallery" / "456-sample.cbz"
        src_file.write_text("payload", encoding="utf-8")
        dest_dir = self.root / "data" / "del"
        os.makedirs(dest_dir, exist_ok=True)
        existing = dest_dir / "456-sample.cbz"
        existing.write_text("existing", encoding="utf-8")

        moved = move_path_with_collision(str(src_file), str(dest_dir))
        self.assertTrue(Path(moved).exists())
        self.assertNotEqual(Path(moved).name, "456-sample.cbz")

    def test_move_path_with_collision_adds_suffix_on_timestamp_collision(self):
        src_file = self.root / "data" / "gallery" / "457-sample.cbz"
        src_file.write_text("payload", encoding="utf-8")
        dest_dir = self.root / "data" / "del"
        os.makedirs(dest_dir, exist_ok=True)
        base_name = dest_dir / "457-sample.cbz"
        base_name.write_text("existing", encoding="utf-8")
        timestamp_name = dest_dir / "457-sample_20240101000000.cbz"
        timestamp_name.write_text("existing", encoding="utf-8")

        with mock.patch.object(utils_mod.time, "strftime", return_value="20240101000000"):
            moved = move_path_with_collision(str(src_file), str(dest_dir))

        self.assertTrue(Path(moved).exists())
        self.assertEqual(Path(moved).name, "457-sample_20240101000000_1.cbz")

    def test_comicinfo_create_xml_without_tags(self):
        with sqlite3.connect(self.config.dbs_name) as co:
            co.execute(
                "INSERT INTO eh_data(gid, token, title, title_jpn, category, posted) VALUES (?,?,?,?,?,?)",
                (777, "tok", "English", "", "category", 1704067200),
            )
            co.commit()

        output_dir = self.root / "data" / "gallery" / "777-sample"
        os.makedirs(output_dir, exist_ok=True)
        comic_info = ComicInfo.__new__(ComicInfo)
        Config.__init__(comic_info, config_path=str(self.config_path))
        comic_info.create_xml(777, str(output_dir))

        xml_file = output_dir / "ComicInfo.xml"
        self.assertTrue(xml_file.exists())
        xml_text = xml_file.read_text(encoding="utf-8")
        self.assertIn("<Title>English</Title>", xml_text)


class AsyncConfigTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        Config._config_cache.clear()
        Config._session_cache.clear()
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.config_path = build_config_file(self.root)
        self.config = Config(config_path=str(self.config_path))

    async def asyncTearDown(self):
        await Config.close_cached_sessions()
        Config._config_cache.clear()
        Config._session_cache.clear()
        self.tmp.cleanup()

    async def test_session_cache_is_loop_scoped(self):
        session_a = await self.config.get_session()
        session_b = await self.config.get_session()
        self.assertIs(session_a, session_b)
        self.assertFalse(session_a.closed)
        await Config.close_cached_sessions()
        self.assertTrue(session_a.closed)

    @mock.patch("src.Watch.get_web_gallery_download_list", return_value=[[999, "tok", "title"]])
    @mock.patch("src.Watch.asyncio.sleep", new_callable=mock.AsyncMock)
    async def test_watch_retry_preserves_archive_mode(self, mocked_sleep, mocked_get_list):
        watch = Watch.__new__(Watch)
        Config.__init__(watch, config_path=str(self.config_path))

        with mock.patch.object(DownloadArchiveGallery, "dl_gallery", new_callable=mock.AsyncMock) as mocked_dl:
            mocked_dl.side_effect = [False, True]
            await watch.dl_new_gallery(gids="999", archive_status=True)

        self.assertEqual(mocked_dl.call_count, 2)
        self.assertTrue(all(call.kwargs["original_flag"] is False for call in mocked_dl.call_args_list))
        mocked_sleep.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
