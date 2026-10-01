import asyncio
import io
import os
import socket
import sqlite3
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest import mock

import aiohttp
from PIL import Image
from yarl import URL

from src.AddFavData import AddFavData, FavoritesFetchError
from src.AppConfig import AppConfig
from src.ComicInfo import ComicInfo
from src.Checker import Checker
from src.Database import Database
from src.DownloadWebGallery import DownloadStatus, DownloadWebGallery
from src.EhClient import EhClient
from src.LANraragi import LANraragi
import src.Utils as utils_mod
from src.Utils import (
    clear_old_file,
    collect_gid_cbz_groups,
    gallery_basename,
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


def jpeg_bytes():
    buffer = io.BytesIO()
    Image.effect_noise((64, 64), 64).convert("RGB").save(buffer, "JPEG")
    return buffer.getvalue()


def serve_once(testcase, body, content_length):
    """Serve `body` with the given Content-Length on 127.0.0.1, then close the connection."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    testcase.addCleanup(server.close)

    def handle():
        conn, _ = server.accept()
        with conn:
            conn.recv(65536)
            conn.sendall(
                f"HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\nContent-Length: {content_length}\r\n"
                f"Connection: close\r\n\r\n".encode() + body
            )

    threading.Thread(target=handle, daemon=True).start()
    return f"http://127.0.0.1:{server.getsockname()[1]}/h/1.jpg"


GALLERY_PAGE = """
<table><tr><td class="gdt1">Length:</td><td class="gdt2">2 pages</td></tr></table>
<table class="ptb"><tr><td>&lt;</td><td>1</td><td>&gt;</td></tr></table>
<div id="gdt"><a href="https://exhentai.org/s/aaa/1-1"></a><a href="https://exhentai.org/s/bbb/1-2"></a></div>
"""


def favorites_page(*galleries, next_gid=None):
    """Minimal EH favorites page. `galleries` are (gid, token, fav_name) tuples."""
    rows = "".join(
        f'<tr><td><div id="posted_{gid}" title="{fav_name}">2026-01-01 00:00</div>'
        f'<a href="https://exhentai.org/g/{gid}/{token}/">g</a></td></tr>'
        for gid, token, fav_name in galleries
    )
    nav = f'<a id="dnext" href="https://exhentai.org/favorites.php?next={next_gid}">next</a>' if next_gid else ""
    return f'<div class="ido"><form id="favform"><table class="itg">{rows}</table></form>{nav}</div>'.encode()


LOGIN_PAGE = b"<html><body><p>Please log in to view your favorites.</p></body></html>"
NO_HITS_PAGE = b'<div class="ido"><p>No hits found</p></div>'


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

    def test_move_path_with_collision_keeps_capped_names_within_filesystem_limit(self):
        name = gallery_basename(1485407, "あ" * 100, "-1280x") + ".cbz"  # what a download is stored as
        dest_dir = self.root / "data" / "del"
        os.makedirs(dest_dir, exist_ok=True)
        (dest_dir / name).write_bytes(b"existing")

        moved = []
        with mock.patch.object(utils_mod.time, "strftime", return_value="20240101000000"):
            for attempt in range(3):  # same-name collision, then timestamp collisions that add _1, _2
                src_file = self.root / "data" / "gallery" / name
                src_file.write_bytes(f"payload {attempt}".encode())
                moved.append(Path(move_path_with_collision(str(src_file), str(dest_dir))))

        self.assertEqual(len({p.name for p in moved}), 3)  # every file kept, none overwritten
        for path in moved:
            self.assertLessEqual(len(path.name.encode("utf-8")), 255, path.name)
            self.assertTrue(path.name.startswith("1485407-"))
            self.assertTrue(path.name.endswith(".cbz"))
        self.assertEqual(sorted(p.read_bytes() for p in moved), [b"payload 0", b"payload 1", b"payload 2"])

    def seed_sync_favorites(self, *gids):
        with self.database.connection() as co:
            for gid in gids:
                co.execute("INSERT INTO fav_category(gid, token, fav_id, del_flag) VALUES (?,?,0,0)", (gid, "t"))
            co.commit()

    def sync_flags(self):
        Checker(self.config, self.database).sync_local_to_sqlite_cbz(cover=True)
        with self.database.connection() as co:
            return co.execute("SELECT gid, original_flag, web_1280x_flag FROM fav_category ORDER BY gid").fetchall()

    def test_sync_flags_ignore_leftovers_that_are_not_cbz_files(self):
        gallery = Path(self.config.gallery_path)
        self.seed_sync_favorites(888)
        (gallery / "888-t.cbz-tmp").mkdir()  # update_meta_info leftover
        (gallery / "888-t.cbz.bak").write_bytes(b"x")
        (gallery / "888-folder.cbz").mkdir()  # a directory that happens to end in .cbz

        self.assertEqual(self.sync_flags(), [(888, 0, 0)])  # was (888, 1, 0): counted as downloaded

    def test_sync_flags_treat_uppercase_1280x_as_the_web_version(self):
        gallery = Path(self.config.gallery_path)
        self.seed_sync_favorites(777, 778, 779)
        (gallery / "777-t-1280X.cbz").write_bytes(b"x")
        (gallery / "778-t-1280x.cbz").write_bytes(b"x")
        (gallery / "779-t.cbz").write_bytes(b"x")

        self.assertEqual(self.sync_flags(), [(777, 0, 1), (778, 0, 1), (779, 1, 0)])

    def test_checker_clear_old_file_only_moves_real_cbz_files(self):
        gallery = self.seed_outdated_gallery_for_checker()
        (gallery / "100-Old.cbz.bak").write_bytes(b"backup")
        (gallery / "100-Old-folder.cbz").mkdir()

        Checker(self.config, self.database).clear_old_file()

        self.assertEqual(sorted(p.name for p in gallery.iterdir()), ["100-Old-folder.cbz", "100-Old.cbz.bak", "200-New-1280x.cbz"])
        self.assertEqual(sorted(p.name for p in Path(self.config.del_path).iterdir()), ["100-Old-1280x.cbz"])

    def seed_outdated_gallery_for_checker(self):
        gallery = Path(self.config.gallery_path)
        with self.database.connection() as co:
            co.execute("INSERT INTO eh_data(gid, token, title, current_gid, current_token) VALUES (100,'a','Old',200,'b')")
            co.execute("INSERT INTO eh_data(gid, token, title, current_gid, current_token) VALUES (200,'b','New',200,'b')")
            co.execute("INSERT INTO fav_category(gid, token, fav_id, web_1280x_flag) VALUES (200,'b',0,1)")
            co.commit()
        (gallery / "100-Old-1280x.cbz").write_bytes(b"old")
        (gallery / "200-New-1280x.cbz").write_bytes(b"new")
        return gallery

    def test_rename_cbz_file_shortens_long_names_and_normalizes_1280x(self):
        gallery = Path(self.config.gallery_path)
        long_name = "123-" + "x" * 100 + ".cbz"
        (gallery / long_name).write_bytes(b"long")
        (gallery / "124-short-1280X.cbz").write_bytes(b"upper")

        utils_mod.rename_cbz_file(str(gallery))

        names = sorted(p.name for p in gallery.iterdir())
        self.assertEqual(names, ["123-" + "x" * 76 + ".cbz", "124-short-1280x.cbz"])

    def test_rename_cbz_file_never_overwrites_a_different_file(self):
        gallery = Path(self.config.gallery_path)
        # Both names are cut to the same 80 characters, so the second rename would land on the first.
        original = gallery / ("123-" + "x" * 100 + " (original scan).cbz")
        decensored = gallery / ("123-" + "x" * 100 + " (decensored).cbz")
        original.write_bytes(b"A-original")
        decensored.write_bytes(b"B-decensored")

        utils_mod.rename_cbz_file(str(gallery))

        contents = sorted(p.read_bytes() for p in gallery.iterdir())
        self.assertEqual(contents, [b"A-original", b"B-decensored"])  # one of them was destroyed before the fix

    def test_rename_cbz_file_keeps_both_files_when_only_the_1280x_case_differs(self):
        gallery = Path(self.config.gallery_path)
        (gallery / "124-t-1280X.cbz").write_bytes(b"UPPER")
        (gallery / "124-t-1280x.cbz").write_bytes(b"lower")

        utils_mod.rename_cbz_file(str(gallery))

        self.assertEqual(sorted(p.read_bytes() for p in gallery.iterdir()), [b"UPPER", b"lower"])

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

    def make_cbz(self, name="56853-t-1280x.cbz", pages=5):
        pages_dir = self.root / "pages"
        pages_dir.mkdir(exist_ok=True)
        for index in range(1, pages + 1):
            (pages_dir / f"{index:08d}.jpg").write_bytes(os.urandom(2000))
        cbz = Path(self.config.gallery_path) / name
        utils_mod.create_cbz(str(pages_dir), str(cbz))
        return cbz

    def seed_comicinfo_row(self, gid=56853):
        with self.database.connection() as co:
            co.execute(
                "INSERT INTO eh_data(gid, token, title, title_jpn, category, posted) VALUES (?,?,?,?,?,?)",
                (gid, "tok", "Title", "", "Manga", 1704067200),
            )
            co.commit()

    def test_update_meta_info_keeps_cbz_intact_when_rewrite_fails(self):
        self.seed_comicinfo_row()
        cbz = self.make_cbz()
        original = cbz.read_bytes()
        real_write, calls = zipfile.ZipFile.write, {"count": 0}

        def fail_on_second_page(zip_file, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError(28, "No space left on device")
            return real_write(zip_file, *args, **kwargs)

        with mock.patch.object(zipfile.ZipFile, "write", fail_on_second_page), \
                mock.patch("src.ComicInfo.logger") as log:
            ComicInfo(self.config, self.database).update_meta_info()  # reports the failure and moves on

        self.assertIn("No space left on device", log.error.call_args.args[0])

        self.assertEqual(cbz.read_bytes(), original)  # was truncated to 1 member before the fix
        self.assertEqual(sorted(p.name for p in cbz.parent.iterdir()), [cbz.name])  # no temp files left behind

    def test_update_meta_info_rewrites_cbz_with_comicinfo_and_leaves_no_temp_files(self):
        self.seed_comicinfo_row()
        cbz = self.make_cbz()

        ComicInfo(self.config, self.database).update_meta_info()

        with zipfile.ZipFile(cbz) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(len(archive.namelist()), 6)  # 5 pages + ComicInfo.xml
            self.assertEqual(ET.fromstring(archive.read("ComicInfo.xml")).findtext("Title"), "Title")
        self.assertEqual(sorted(p.name for p in cbz.parent.iterdir()), [cbz.name])

    def test_update_meta_info_failure_on_one_cbz_does_not_stop_the_others(self):
        self.seed_comicinfo_row(56853)
        self.seed_comicinfo_row(56854)
        broken = Path(self.config.gallery_path) / "56853-t-1280x.cbz"
        broken.write_bytes(b"not a zip file")
        good = self.make_cbz("56854-t-1280x.cbz")

        ComicInfo(self.config, self.database).update_meta_info()

        self.assertEqual(broken.read_bytes(), b"not a zip file")
        with zipfile.ZipFile(good) as archive:
            self.assertIn("ComicInfo.xml", archive.namelist())

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

    def test_gallery_basename_fits_filesystem_limit_and_can_be_created(self):
        title = "あ" * 100  # 300 UTF-8 bytes, like the longest real titles
        name = gallery_basename(1485407, title, "-1280x")

        self.assertLessEqual(len((name + ".cbz").encode("utf-8")), 255)
        self.assertTrue(name.startswith("1485407-"))
        self.assertTrue(name.endswith("-1280x"))
        (self.root / "temp").mkdir()
        (self.root / "temp" / name).mkdir()  # raised OSError: File name too long before the fix
        (self.root / "temp" / ("temp_" + name + ".cbz")).write_bytes(b"x")

    def test_gallery_basename_never_cuts_a_character_in_half(self):
        for width in (1, 2, 3, 4):  # 1-4 byte UTF-8 characters
            char = {1: "a", 2: "é", 3: "あ", 4: "😀"}[width]
            name = gallery_basename(7, char * 400, "-1280x")
            name.encode("utf-8").decode("utf-8")  # raises on a split character
            self.assertLessEqual(len(name.encode("utf-8")), 240, width)
            self.assertTrue(set(name[len("7-"):-len("-1280x")]) <= {char}, width)

    def test_gallery_basename_leaves_normal_titles_unchanged(self):
        self.assertEqual(
            gallery_basename(123, 'A: "Title" <1>?', "-1280x"), "123-A Title 1-1280x"
        )
        self.assertEqual(gallery_basename(123, "シスター完全敗北。", ""), "123-シスター完全敗北。")

    def test_download_paths_use_capped_name(self):
        download = DownloadWebGallery(self.config, self.database, mock.Mock(), mock.Mock(), 1485407, "tok", "あ" * 100)

        self.assertLessEqual(len(os.path.basename(download.filepath_tmp).encode("utf-8")), 255)
        self.assertLessEqual(len((os.path.basename(download.filepath_end) + ".cbz").encode("utf-8")), 255)
        os.makedirs(download.filepath_tmp)


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

    async def test_watch_round_skips_cleanup_when_favorites_cannot_be_fetched(self):
        self.seed_downloaded_favorites([101, 102])
        before = self.snapshot_favorites()
        quota = mock.Mock(get_limits=mock.AsyncMock(return_value=(0, 5000)))
        client = mock.Mock(fetch_data=mock.AsyncMock(side_effect=[
            b'<div id="favsel"></div>',  # update_category
            LOGIN_PAGE,                  # post_fav_data
        ]))
        watch = Watch(self.config, self.database, client, quota)

        class StopWatch(Exception):
            pass

        async def stop_after_skip(seconds):
            raise StopWatch()

        # src.Watch.asyncio and src.AddFavData.asyncio are the same module object, so patch sleep once.
        # The first sleep reached is the one-hour wait after the skipped round, which stops the loop.
        with mock.patch("src.Watch.asyncio.sleep", side_effect=stop_after_skip):
            with self.assertRaises(StopWatch):
                await asyncio.wait_for(watch.apply(1), timeout=5)

        self.assertEqual(self.snapshot_favorites(), before)
        self.assertEqual(client.fetch_data.await_count, 2)

    def seed_outdated_gallery(self, new_version_downloaded=False):
        """Old gid 100 is downloaded; its newer version 200 is favorited. Returns the gallery dir."""
        gallery = Path(self.config.gallery_path)
        gallery.mkdir(parents=True, exist_ok=True)
        Path(self.config.del_path).mkdir(parents=True, exist_ok=True)
        with self.database.connection() as co:
            co.execute("INSERT OR REPLACE INTO fav_name(fav_id, fav_name) VALUES (0, 'Favorites 0')")
            co.execute("INSERT INTO eh_data(gid, token, title, current_gid, current_token) VALUES (100,'a','Old',200,'b')")
            co.execute("INSERT INTO eh_data(gid, token, title, current_gid, current_token) VALUES (200,'b','New',200,'b')")
            co.execute("INSERT INTO fav_category(gid, token, fav_id, del_flag, web_1280x_flag) VALUES (100,'a',0,1,1)")
            co.execute("INSERT INTO fav_category(gid, token, fav_id, del_flag, web_1280x_flag) VALUES (200,'b',0,0,?)",
                       (1 if new_version_downloaded else 0,))
            co.commit()
        (gallery / "100-Old-1280x.cbz").write_bytes(b"only copy of the old version")
        if new_version_downloaded:
            (gallery / "200-New-1280x.cbz").write_bytes(b"new version")
        return gallery

    def gallery_and_del(self):
        return (sorted(p.name for p in Path(self.config.gallery_path).iterdir()),
                sorted(p.name for p in Path(self.config.del_path).iterdir()))

    async def run_watch_round_until_sleep(self, download_status):
        """One Watch.apply round whose downloads end with `download_status` and whose favorites fetch is mocked."""
        pages = iter([b'<div id="favsel"></div>', favorites_page((100, "a", "Favorites 0"), (200, "b", "Favorites 0"))])
        client = mock.Mock(fetch_data=mock.AsyncMock(side_effect=lambda *a, **k: next(pages)))
        quota = mock.Mock(get_limits=mock.AsyncMock(return_value=(0, 5000)))
        download = mock.Mock(apply=mock.AsyncMock(return_value=download_status))

        class StopWatch(Exception):
            pass

        async def stop(seconds):
            if seconds == 60 * 60:
                raise StopWatch()

        with mock.patch("src.Watch.DownloadWebGallery", return_value=download), \
                mock.patch("src.Watch.asyncio.sleep", side_effect=stop), \
                mock.patch.object(AddFavData, "update_meta_data", new_callable=mock.AsyncMock):
            with self.assertRaises(StopWatch):
                await asyncio.wait_for(Watch(self.config, self.database, client, quota).apply(3), timeout=5)

    async def test_watch_keeps_old_version_when_new_version_download_fails(self):
        self.seed_outdated_gallery()

        await self.run_watch_round_until_sleep(DownloadStatus.RETRYABLE_FAILURE)

        self.assertEqual(self.gallery_and_del(), (["100-Old-1280x.cbz"], []))
        with self.database.connection() as co:
            self.assertEqual(co.execute("SELECT COUNT(*) FROM fav_category WHERE gid=100").fetchone()[0], 1)

    async def test_watch_keeps_old_version_when_new_version_is_copyright_blocked(self):
        self.seed_outdated_gallery()

        await self.run_watch_round_until_sleep(DownloadStatus.COPYRIGHT_BLOCKED)

        self.assertEqual(self.gallery_and_del(), (["100-Old-1280x.cbz"], []))

    def test_checker_clear_old_file_keeps_old_version_until_current_one_is_downloaded(self):
        gallery = self.seed_outdated_gallery(new_version_downloaded=False)
        checker = Checker(self.config, self.database)

        checker.clear_old_file()
        self.assertEqual(self.gallery_and_del(), (["100-Old-1280x.cbz"], []))

        with self.database.connection() as co:
            co.execute("UPDATE fav_category SET web_1280x_flag=1 WHERE gid=200")
            co.commit()
        (gallery / "200-New-1280x.cbz").write_bytes(b"new version")
        checker.clear_old_file()
        self.assertEqual(self.gallery_and_del(), (["200-New-1280x.cbz"], ["100-Old-1280x.cbz"]))

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

    def seed_lanraragi_gallery(self, gid=56853, title="English", title_jpn="Japanese title"):
        with self.database.connection() as co:
            co.execute(
                "INSERT INTO eh_data(gid, token, title, title_jpn, category, posted) VALUES (?,?,?,?,?,?)",
                (gid, "tok", title, title_jpn, "Manga", "1704067200"),
            )
            co.commit()

    async def run_lanraragi(self, archives, put_status=200, put_body=None, get_status=200, prefer_japanese=True):
        """Run LANraragi.lan_update_tags against a fake LRR. Returns (puts, log, outcome)."""
        puts = []
        put_body = {"success": 1} if put_body is None else put_body

        class FakeResponse:
            def __init__(self, status, body):
                self.status, self._body = status, body

            async def json(self, content_type=None):
                return self._body

            async def read(self):
                return b"{}"

            def raise_for_status(self):
                if self.status >= 400:
                    info = aiohttp.RequestInfo(URL("http://lan.invalid/api/archives"), "GET", {}, URL("http://lan.invalid/api/archives"))
                    raise aiohttp.ClientResponseError(info, (), status=self.status)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

        class FakeSession:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            def get(self, url):
                return FakeResponse(get_status, archives)

            def put(self, url, data=None):
                puts.append((url.rstrip("/").split("/")[-2], data))
                return FakeResponse(put_status, put_body)

        self.config.prefer_japanese_title = prefer_japanese
        with mock.patch("src.LANraragi.aiohttp.ClientSession", FakeSession), \
                mock.patch("src.LANraragi.logger") as log:
            outcome = None
            try:
                await LANraragi(self.config, self.database, watch_status=True).lan_update_tags()
            except BaseException as exc:  # SystemExit must be reported, not allowed to end the test run
                outcome = exc
        return puts, log, outcome

    async def test_lanraragi_skips_archives_it_cannot_match_and_keeps_going(self):
        self.seed_lanraragi_gallery(56853)
        self.seed_lanraragi_gallery(138202)
        archives = [
            {"arcid": "a1", "title": "56853-Known", "tags": "", "pagecount": 5},
            {"arcid": "a2", "title": "[Artist] Foreign comic not from this tool", "tags": "", "pagecount": 9},
            {"arcid": "a3", "title": "138202-Known too", "tags": "", "pagecount": 7},
        ]

        puts, _, outcome = await self.run_lanraragi(archives)

        self.assertIsNone(outcome)  # was SystemExit(1)
        self.assertEqual([arcid for arcid, _ in puts], ["a1", "a3"])

    async def test_lanraragi_empty_library_returns_without_exiting(self):
        puts, _, outcome = await self.run_lanraragi([])

        self.assertIsNone(outcome)
        self.assertEqual(puts, [])

    async def test_lanraragi_error_response_is_reported_not_iterated(self):
        error_object = {"operation": "", "error": "This API is protected.", "success": 0}

        puts, log, outcome = await self.run_lanraragi(error_object)

        self.assertIsNone(outcome)  # was TypeError: string indices must be integers
        self.assertEqual(puts, [])
        log.error.assert_called()

    async def test_lanraragi_http_error_is_reported_not_raised(self):
        puts, log, outcome = await self.run_lanraragi([], get_status=500)

        self.assertIsNone(outcome)
        log.error.assert_called()

    async def test_lanraragi_reports_rejected_metadata_updates(self):
        self.seed_lanraragi_gallery(56853)
        archives = [{"arcid": "a1", "title": "56853-Known", "tags": "", "pagecount": 5}]

        _, log, _ = await self.run_lanraragi(archives, put_status=401, put_body={"success": 0, "error": "bad key"})

        messages = " ".join(str(call.args[0]) for call in log.warning.call_args_list + log.error.call_args_list)
        self.assertIn("a1", messages)
        self.assertNotIn("[OK]", " ".join(str(call.args[0]) for call in log.info.call_args_list))

    async def test_lanraragi_handles_missing_pagecount(self):
        self.seed_lanraragi_gallery(56853)
        archives = [{"arcid": "a1", "title": "56853-Known", "tags": "", "pagecount": None}]

        puts, _, outcome = await self.run_lanraragi(archives)

        self.assertIsNone(outcome)  # was TypeError: int() argument must be ... not 'NoneType'
        self.assertEqual(len(puts), 1)
        self.assertNotIn("pages:None", puts[0][1]["tags"])

    async def test_lanraragi_title_follows_prefer_japanese_title(self):
        self.seed_lanraragi_gallery(56853, title="English title", title_jpn="日本語のタイトル")
        archives = [{"arcid": "a1", "title": "56853-Known", "tags": "", "pagecount": 5}]

        english, _, _ = await self.run_lanraragi(archives, prefer_japanese=False)
        japanese, _, _ = await self.run_lanraragi(archives, prefer_japanese=True)

        self.assertEqual(english[0][1]["title"], "English title")
        self.assertEqual(japanese[0][1]["title"], "日本語のタイトル")

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

    async def test_download_image_retry_delay_releases_slot(self):
        semaphore = asyncio.Semaphore(1)
        pages = iter([b"<title>503 Backend fetch failed</title>", self.make_image_page("https://abc.hath.network/h/1.jpg")])

        async def fake_fetch(url, tqdm_file_path=None):
            return True if tqdm_file_path is not None else next(pages)

        slot_held_while_sleeping = []

        async def fake_sleep(_):
            slot_held_while_sleeping.append(semaphore.locked())

        download = self.make_download(mock.Mock(fetch_data=fake_fetch))
        with mock.patch("src.DownloadWebGallery.asyncio.sleep", side_effect=fake_sleep):
            result = await asyncio.wait_for(
                download.download_image(semaphore, "https://exhentai.org/s/aaa/1-1", "00000001"), timeout=2
            )

        self.assertTrue(result)
        self.assertEqual(slot_held_while_sleeping, [False])

    async def test_fetch_file_rejects_truncated_image(self):
        image = jpeg_bytes()
        url = serve_once(self, image[: len(image) // 2], len(image))
        target = self.root / "00000001.jpg"

        result = await EhClient(self.config).fetch_file_blocking(url, str(target))

        self.assertEqual(result, "reload_image")
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob("temp_*")), [])

    async def test_fetch_file_ignores_environment_proxy_when_proxy_disabled(self):
        image = jpeg_bytes()
        url = serve_once(self, image, len(image))
        target = self.root / "00000001.jpg"
        dead_proxy = "http://127.0.0.1:9"
        proxy_env = {"http_proxy": dead_proxy, "HTTP_PROXY": dead_proxy, "no_proxy": "", "NO_PROXY": ""}

        with mock.patch.dict(os.environ, proxy_env):
            result = await EhClient(self.config).fetch_file_blocking(url, str(target))

        self.assertIs(result, True)
        self.assertEqual(target.read_bytes(), image)

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


    def seed_downloaded_favorites(self, gids, fav_id=0):
        gallery = Path(self.config.gallery_path)
        gallery.mkdir(parents=True, exist_ok=True)
        with self.database.connection() as co:
            co.execute("INSERT OR REPLACE INTO fav_name(fav_id, fav_name) VALUES (0, 'Favorites 0')")
            for gid in gids:
                co.execute(
                    "INSERT INTO eh_data(gid, token, title, current_gid, current_token) VALUES (?,?,?,?,?)",
                    (gid, "t", "T", gid, "t"),
                )
                co.execute(
                    "INSERT INTO fav_category(gid, token, fav_id, del_flag, original_flag, web_1280x_flag) "
                    "VALUES (?,?,?,0,0,1)",
                    (gid, "t", fav_id),
                )
                (gallery / f"{gid}-T-1280x.cbz").write_bytes(b"cbz")
            co.commit()

    def snapshot_favorites(self):
        with self.database.connection() as co:
            rows = co.execute("SELECT gid, del_flag FROM fav_category ORDER BY gid").fetchall()
        return rows, sorted(p.name for p in Path(self.config.gallery_path).iterdir())

    async def sync_favorites(self, *pages):
        """Run the Watch sequence post_fav_data -> clear_del_flag against canned pages."""
        pages = iter(pages)

        async def fake_fetch(url, **kwargs):
            page = next(pages)
            if isinstance(page, Exception):
                raise page
            return page

        add_fav = AddFavData(self.config, self.database, mock.Mock(fetch_data=fake_fetch))
        with mock.patch("src.AddFavData.asyncio.sleep", new_callable=mock.AsyncMock):
            await add_fav.post_fav_data()
            await add_fav.clear_del_flag()

    async def test_favorites_sync_keeps_files_when_page_is_not_a_favorites_list(self):
        self.seed_downloaded_favorites([101, 102, 103])
        before = self.snapshot_favorites()

        with self.assertRaises(FavoritesFetchError):
            await self.sync_favorites(LOGIN_PAGE)

        self.assertEqual(self.snapshot_favorites(), before)

    async def test_favorites_sync_keeps_files_on_no_hits_page(self):
        # EH answers an empty search with a page that has no #favform, so the page check stops it.
        self.seed_downloaded_favorites([101, 102])
        before = self.snapshot_favorites()

        with self.assertRaises(FavoritesFetchError):
            await self.sync_favorites(NO_HITS_PAGE)

        self.assertEqual(self.snapshot_favorites(), before)

    async def test_favorites_sync_refuses_empty_list_while_local_favorites_exist(self):
        # A favorites page that parses but lists nothing must not flag every local gallery as removed.
        self.seed_downloaded_favorites([101, 102])
        before = self.snapshot_favorites()

        with self.assertRaisesRegex(FavoritesFetchError, "empty but 2 galleries"):
            await self.sync_favorites(favorites_page())

        self.assertEqual(self.snapshot_favorites(), before)

    async def test_favorites_sync_accepts_empty_list_when_nothing_is_recorded_locally(self):
        os.makedirs(self.config.gallery_path)  # Watch creates it at the start of every round

        await self.sync_favorites(favorites_page())

        self.assertEqual(self.snapshot_favorites(), ([], []))

    async def test_favorites_sync_is_atomic_when_a_later_page_fails(self):
        self.seed_downloaded_favorites([101, 102, 103])
        before = self.snapshot_favorites()
        first_page = favorites_page((101, "t", "Favorites 0"), next_gid=101)

        with self.assertRaises(RuntimeError):
            await self.sync_favorites(first_page, RuntimeError("connection lost"))

        self.assertEqual(self.snapshot_favorites(), before)

    async def test_favorites_sync_removes_only_galleries_missing_from_favorites(self):
        self.seed_downloaded_favorites([101, 102, 103])
        page = favorites_page((101, "t", "Favorites 0"), (103, "t", "Favorites 0"))

        await self.sync_favorites(page)

        rows, files = self.snapshot_favorites()
        self.assertEqual(rows, [(101, 0), (103, 0)])
        self.assertEqual(files, ["101-T-1280x.cbz", "103-T-1280x.cbz"])
        self.assertEqual([p.name for p in Path(self.config.del_path).iterdir()], ["102-T-1280x.cbz"])

    async def test_post_eh_api_decodes_html_entities_in_titles(self):
        async def fake_api(url, json):
            return {"gmetadata": [{
                "gid": 413243, "token": "t", "category": "Doujinshi", "thumb": "", "uploader": "u",
                "posted": "1", "filecount": "5", "filesize": 1, "expunged": False, "rating": "4.5", "tags": [],
                "title": "Victim Girls 10 - It&#039;s Training Cats &amp; Dogs. &lt;DL&gt; &quot;x&quot;",
                "title_jpn": "ガールズ&amp;パンツァー &#x3042;",
            }]}

        add_fav = AddFavData(self.config, self.database, mock.Mock(fetch_data=fake_api))
        with mock.patch("src.AddFavData.asyncio.sleep", new_callable=mock.AsyncMock):
            data = await add_fav.post_eh_api({"method": "gdata", "gidlist": [[413243, "t"]], "namespace": 1})

        title, title_jpn = data[0]["data"][2], data[0]["data"][3]
        self.assertEqual(title, 'Victim Girls 10 - It\'s Training Cats & Dogs. <DL> "x"')
        self.assertEqual(title_jpn, "ガールズ&パンツァー あ")

    async def test_post_eh_api_leaves_plain_titles_untouched(self):
        async def fake_api(url, json):
            return {"gmetadata": [{
                "gid": 1, "token": "t", "category": "Manga", "thumb": "", "uploader": "u", "posted": "1",
                "filecount": "1", "filesize": 1, "expunged": False, "rating": "4", "tags": [],
                "title": "[Artist] Title 100% (R&D) a&b ;x", "title_jpn": "",
            }]}

        add_fav = AddFavData(self.config, self.database, mock.Mock(fetch_data=fake_api))
        with mock.patch("src.AddFavData.asyncio.sleep", new_callable=mock.AsyncMock):
            data = await add_fav.post_eh_api({"method": "gdata", "gidlist": [[1, "t"]], "namespace": 1})

        self.assertEqual(data[0]["data"][2], "[Artist] Title 100% (R&D) a&b ;x")

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
