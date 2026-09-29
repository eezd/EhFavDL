import asyncio
import xml.etree.ElementTree as ET
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.AddFavData import AddFavData
from src.AppConfig import AppConfig
from src.ComicInfo import ComicInfo
from src.Checker import Checker
from src.Database import Database
from src.DownloadWebGallery import DownloadStatus, DownloadWebGallery
from src.EhClient import EhClient
import src.Utils as utils_mod
from src.Utils import (
    clear_old_file,
    collect_gid_cbz_groups,
    get_web_gallery_download_list,
    move_path_with_collision,
    windows_escape,
)
from src.Watch import Watch


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


GALLERY_PAGE = """
<table><tr><td class="gdt1">Length:</td><td class="gdt2">2 pages</td></tr></table>
<table class="ptb"><tr><td>&lt;</td><td>1</td><td>&gt;</td></tr></table>
<div id="gdt"><a href="https://exhentai.org/s/aaa/1-1"></a><a href="https://exhentai.org/s/bbb/1-2"></a></div>
"""


class CoreBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.config_path = build_config_file(self.root)
        self.config = AppConfig.load(str(self.config_path))
        self.database = Database(self.config.dbs_name)
        self.database.initialize()
        os.makedirs(self.config.gallery_path, exist_ok=True)
        os.makedirs(self.config.del_path, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_config_loads_custom_path(self):
        self.assertEqual(self.config.base_url, "exhentai.org")
        self.assertEqual(self.config.connect_limit, 3)
        self.assertTrue(self.config.gallery_path.endswith(os.path.join("data", "gallery")))

    def test_pure_helpers(self):
        self.assertEqual(windows_escape('a<b>c:d|e?f*g"h/i\t'), "abcdefghi")

    def test_config_parses_string_booleans_and_list_ids(self):
        config_text = self.config_path.read_text(encoding="utf-8")
        config_text = config_text.replace("enable: False", "enable: 'false'")
        config_text = config_text.replace("tags_translation: False", "tags_translation: 'false'")
        config_text = config_text.replace("watch_fav_ids: 0,1", "watch_fav_ids:\n  - 0\n  - 1")
        self.config_path.write_text(config_text, encoding="utf-8")

        config = AppConfig.load(str(self.config_path))

        self.assertFalse(config.proxy_status)
        self.assertFalse(config.tags_translation)
        self.assertEqual(config.watch_fav_ids, "0,1")


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

        clear_old_file(self.database, self.config.gallery_path, self.config.del_path, [123])

        self.assertFalse(src_file.exists())
        moved_files = list((self.root / "data" / "del").glob("123-sample.cbz*"))
        self.assertTrue(moved_files)
        with sqlite3.connect(self.config.dbs_name) as co:
            row = co.execute("SELECT COUNT(*) FROM fav_category WHERE gid = 123").fetchone()[0]
        self.assertEqual(row, 0)

    def test_checker_skips_local_gallery_without_metadata(self):
        orphan = self.root / "data" / "gallery" / "999-orphan.cbz"
        orphan.write_text("payload", encoding="utf-8")

        Checker(self.config, self.database).clear_old_file()

        self.assertTrue(orphan.exists())

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

        dl_list = get_web_gallery_download_list(self.database, fav_cat="1")
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
        comic_info = ComicInfo(self.config, self.database)
        comic_info.create_xml(777, str(output_dir))

        xml_file = output_dir / "ComicInfo.xml"
        self.assertTrue(xml_file.exists())
        xml_text = xml_file.read_text(encoding="utf-8")
        self.assertIn("<Title>English</Title>", xml_text)

    def test_comicinfo_escapes_special_characters(self):
        with sqlite3.connect(self.config.dbs_name) as co:
            co.execute(
                "INSERT INTO eh_data(gid, token, title, title_jpn, category, posted) VALUES (?,?,?,?,?,?)",
                (778, "tok", "A & B <C>", "", "Non-H & <x>", 1704067200),
            )
            co.executemany("INSERT INTO tag_list(tid, tag) VALUES (?,?)", [(1, "artist:x&y"), (2, "female:a<b")])
            co.executemany("INSERT INTO gid_tid(gid, tid) VALUES (?,?)", [(778, 1), (778, 2)])
            co.commit()

        output_dir = self.root / "data" / "gallery" / "778-sample"
        os.makedirs(output_dir, exist_ok=True)
        ComicInfo(self.config, self.database).create_xml(778, str(output_dir))

        xml_file = output_dir / "ComicInfo.xml"
        self.assertTrue(xml_file.read_text(encoding="utf-8").startswith("<?xml"))
        root = ET.parse(xml_file).getroot()
        self.assertNotIn("encoding", root.attrib)
        self.assertEqual(root.findtext("Title"), "A & B <C>")
        self.assertEqual(root.findtext("Genre"), "Non-H & <x>")
        self.assertEqual(set(root.findtext("Tags").split(", ")), {"artist:x&y", "female:a<b"})
        self.assertEqual(root.findtext("Writer"), "x&y")
        self.assertEqual(root.findtext("Web"), "exhentai.org/g/778/tok")


class AsyncInfrastructureTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.config_path = build_config_file(self.root)
        self.config = AppConfig.load(str(self.config_path))
        self.database = Database(self.config.dbs_name)
        self.database.initialize()

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def test_eh_client_reuses_and_closes_session(self):
        client = EhClient(self.config)
        session_a = await client.get_session()
        session_b = await client.get_session()

        self.assertIs(session_a, session_b)
        self.assertFalse(session_a.closed)

        await client.close()

        self.assertTrue(session_a.closed)

    async def run_watch_download(self, apply_results, **kwargs):
        watch = Watch(self.config, self.database, mock.Mock(), mock.Mock())
        download = mock.Mock(apply=mock.AsyncMock(side_effect=apply_results))
        with mock.patch(
            "src.Watch.get_web_gallery_download_list", return_value=[[999, "tok", "title"]]
        ) as get_download_list, mock.patch(
            "src.Watch.DownloadWebGallery", return_value=download
        ), mock.patch("src.Watch.asyncio.sleep", new_callable=mock.AsyncMock) as sleep:
            result = await asyncio.wait_for(watch.dl_new_gallery(**kwargs), timeout=5)
        return result, download.apply, sleep, get_download_list

    async def test_watch_retries_failed_gallery(self):
        result, apply, sleep, _ = await self.run_watch_download(
            [DownloadStatus.RETRYABLE_FAILURE, DownloadStatus.SUCCESS], gids="999"
        )

        self.assertTrue(result)
        self.assertEqual(apply.await_count, 2)
        sleep.assert_awaited_once_with(30)

    async def test_watch_gives_up_after_max_rounds(self):
        result, apply, sleep, _ = await self.run_watch_download(
            [DownloadStatus.RETRYABLE_FAILURE] * 10, gids="999"
        )

        self.assertFalse(result)
        self.assertEqual(apply.await_count, 3)
        self.assertEqual(sleep.await_count, 2)

    async def test_watch_does_not_retry_copyright_blocked_gallery(self):
        result, apply, sleep, _ = await self.run_watch_download(
            [DownloadStatus.COPYRIGHT_BLOCKED], gids="999"
        )

        self.assertTrue(result)
        self.assertEqual(apply.await_count, 1)
        sleep.assert_not_awaited()

    async def test_watch_retries_only_retryable_failures(self):
        watch = Watch(self.config, self.database, mock.Mock(), mock.Mock())
        outcomes = {
            100: [DownloadStatus.COPYRIGHT_BLOCKED],
            200: [DownloadStatus.RETRYABLE_FAILURE, DownloadStatus.SUCCESS],
        }
        calls = {gid: 0 for gid in outcomes}

        def make_download(_, __, ___, ____, gid, _____, ______):
            async def apply():
                outcome = outcomes[gid][calls[gid]]
                calls[gid] += 1
                return outcome

            return mock.Mock(apply=mock.AsyncMock(side_effect=apply))

        with mock.patch(
            "src.Watch.get_web_gallery_download_list",
            return_value=[[100, "a", "copyright"], [200, "b", "retry"]],
        ), mock.patch("src.Watch.DownloadWebGallery", side_effect=make_download), mock.patch(
            "src.Watch.asyncio.sleep", new_callable=mock.AsyncMock
        ) as sleep:
            result = await asyncio.wait_for(watch.dl_new_gallery(gids="100,200"), timeout=5)

        self.assertTrue(result)
        self.assertEqual(calls, {100: 1, 200: 2})
        sleep.assert_awaited_once_with(30)


    async def test_watch_skips_when_no_targets(self):
        result, apply, _, get_download_list = await self.run_watch_download([], fav_cat=None)

        self.assertTrue(result)
        get_download_list.assert_not_called()
        apply.assert_not_awaited()

    def make_download(self, eh_client=None, quota=None):
        return DownloadWebGallery(
            self.config, self.database, eh_client or mock.Mock(), quota or mock.Mock(), 1, "tok", "title"
        )

    def make_image_page(self, image_url):
        return (
            f'<img id="img" src="{image_url}">'
            f'<a id="loadfail" onclick="return nl(\'51413-1\')">reload</a>'
        ).encode()

    async def run_download_image(self, page_urls):
        requested = []
        pages = iter(page_urls)

        async def fake_fetch(url, tqdm_file_path=None):
            requested.append(url)
            if tqdm_file_path is not None:
                return True
            return self.make_image_page(next(pages))

        quota = mock.Mock(wait_until_available=mock.AsyncMock(return_value=(0, 5000)))
        download = self.make_download(mock.Mock(fetch_data=fake_fetch), quota)
        result = await asyncio.wait_for(
            download.download_image(asyncio.Semaphore(1), "https://exhentai.org/s/aaa/1-1", "00000001"),
            timeout=2,
        )
        return result, requested, quota.wait_until_available

    async def test_download_image_quota_wait_does_not_deadlock(self):
        quota_page = "https://exhentai.org/img/509.gif"
        image = "https://abc.hath.network/h/1.jpg"

        result, requested, wait = await self.run_download_image([quota_page, image])

        self.assertTrue(result)
        wait.assert_awaited_once()
        self.assertEqual(
            requested,
            ["https://exhentai.org/s/aaa/1-1", "https://exhentai.org/s/aaa/1-1?nl=51413-1", image],
        )

    async def test_download_image_gives_up_when_quota_never_recovers(self):
        result, _, wait = await self.run_download_image(["https://exhentai.org/img/509.gif"] * 10)

        self.assertFalse(result)
        self.assertEqual(wait.await_count, 3)

    async def test_get_image_url_copyright_detection(self):
        pages = {
            "copyright": '<div class="d"><p>This gallery is unavailable due to a copyright claim by X.</p></div>',
            "removed": '<div class="d"><p>This gallery has been removed or is unavailable.</p></div>',
        }
        for kind, html in pages.items():
            client = mock.Mock(fetch_data=mock.AsyncMock(return_value=html.encode()))
            result = await self.make_download(client).get_image_url()
            self.assertEqual(result, "copyright" if kind == "copyright" else [], kind)

        client = mock.Mock(fetch_data=mock.AsyncMock(return_value=GALLERY_PAGE.encode()))
        result = await self.make_download(client).get_image_url()
        self.assertEqual(
            result,
            [["https://exhentai.org/s/aaa/1-1", "00000001"], ["https://exhentai.org/s/bbb/1-2", "00000002"]],
        )

    async def test_apply_returns_copyright_status_and_persists_flag(self):
        with self.database.connection() as co:
            co.execute(
                "INSERT INTO eh_data(gid, token, title) VALUES (?,?,?)",
                (1, "tok", "title"),
            )
            co.commit()

        client = mock.Mock(
            fetch_data=mock.AsyncMock(
                return_value=b'<div class="d"><p>This gallery is unavailable due to a copyright claim by X.</p></div>'
            )
        )
        quota = mock.Mock(wait_until_available=mock.AsyncMock(return_value=(0, 5000)))
        result = await self.make_download(client, quota).apply()

        self.assertIs(result, DownloadStatus.COPYRIGHT_BLOCKED)
        self.assertEqual(client.fetch_data.await_count, 1)
        with self.database.connection() as co:
            flag = co.execute(
                "SELECT copyright_flag FROM eh_data WHERE gid = 1"
            ).fetchone()[0]
        self.assertEqual(flag, 1)


    async def test_update_meta_data_retries_only_failed_and_terminates(self):
        with self.database.connection() as co:
            co.executemany(
                "INSERT INTO eh_data(gid, token, title) VALUES (?,?,?)",
                [(1, "a", "Old A"), (2, "b", "Old B"), (3, "c", "Old C")],
            )
            co.commit()

        calls = []
        failures = {1: 1, 3: 99}

        async def fake_api(url, json):
            calls.append([gid for gid, _ in json["gidlist"]])
            items = []
            for gid, token in json["gidlist"]:
                if failures.get(gid, 0) > 0:
                    failures[gid] -= 1
                    items.append({"gid": gid, "error": "Key missing, or incorrect key provided."})
                    continue
                items.append({
                    "gid": gid, "token": token, "title": f"New {gid}", "title_jpn": "", "category": "Manga",
                    "thumb": "", "uploader": "u", "posted": "1704067200", "filecount": "5", "filesize": 1,
                    "expunged": False, "rating": "4.5", "tags": ["artist:x"] if gid == 1 else [],
                })
            return {"gmetadata": items}

        add_fav = AddFavData(self.config, self.database, mock.Mock(fetch_data=fake_api))
        with mock.patch("src.AddFavData.asyncio.sleep", new_callable=mock.AsyncMock):
            await asyncio.wait_for(add_fav.update_meta_data(get_all=True), timeout=5)

        self.assertEqual(calls, [[1, 2, 3], [1, 3], [3]])
        with self.database.connection() as co:
            titles = dict(co.execute("SELECT gid, title FROM eh_data").fetchall())
            tag_counts = dict(co.execute("SELECT gid, COUNT(*) FROM gid_tid GROUP BY gid").fetchall())
        self.assertEqual(titles, {1: "New 1", 2: "New 2", 3: "Old C"})
        self.assertEqual(tag_counts, {1: 1})


if __name__ == "__main__":
    unittest.main()
