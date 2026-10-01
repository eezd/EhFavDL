import asyncio
import os
import re
import shutil
import zipfile

from loguru import logger

from src.AddFavData import AddFavData, FavoritesFetchError
from src.Checker import Checker
from src.DownloadWebGallery import DownloadStatus, DownloadWebGallery
from src.LANraragi import LANraragi
from src.Utils import clear_old_file, get_web_gallery_download_list, rename_cbz_file

MAX_DOWNLOAD_ROUNDS = 3


class Watch:
    def __init__(self, config, database, eh_client, quota):
        self.config = config
        self.database = database
        self.eh_client = eh_client
        self.quota = quota

    def watch_move_data_path(self):
        os.makedirs(self.config.data_path, exist_ok=True)
        os.makedirs(self.config.gallery_path, exist_ok=True)
        os.makedirs(self.config.web_path, exist_ok=True)
        for sub_name in os.listdir(self.config.web_path):
            if re.match(r"^\d+-.*\.cbz$", sub_name) and os.path.isfile(os.path.join(self.config.web_path, sub_name)):
                full_path = os.path.join(self.config.web_path, sub_name)
                dest_path = os.path.join(self.config.gallery_path, sub_name)
                shutil.move(full_path, dest_path)
                logger.info(f"Moved: {full_path} -> {dest_path}")

    async def dl_new_gallery(self, fav_cat=None, gids=None):
        """Download galleries selected by fav_cat or gids; retry failures up to MAX_DOWNLOAD_ROUNDS."""
        if not fav_cat and not gids:
            return True
        dl_list = get_web_gallery_download_list(self.database, fav_cat=fav_cat or "", gids=gids or "")
        for round_no in range(1, MAX_DOWNLOAD_ROUNDS + 1):
            failed = []
            for gid, token, title in dl_list:
                status = await DownloadWebGallery(
                    self.config, self.database, self.eh_client, self.quota, gid, token, title
                ).apply()
                if status is DownloadStatus.COPYRIGHT_BLOCKED:
                    logger.warning(
                        f"Skipping retry for copyright-blocked gallery: "
                        f"https://{self.config.base_url}/g/{gid}/{token}"
                    )
                    continue
                if status is not DownloadStatus.SUCCESS:
                    failed.append((gid, token, title))
                    logger.warning(f"Download https://{self.config.base_url}/g/{gid}/{token} failed")
            if not failed:
                return True
            dl_list = failed
            if round_no < MAX_DOWNLOAD_ROUNDS:
                logger.warning(f"Download failed, retry in 30 seconds. gids = {[gid for gid, _, _ in failed]}")
                await asyncio.sleep(30)
        logger.warning(f"Giving up after {MAX_DOWNLOAD_ROUNDS} rounds. gids = {[gid for gid, _, _ in failed]}")
        return False

    async def apply(self, method=1):
        while True:
            image_limits, total_limits = await self.quota.get_limits()
            logger.info(f"Image Limits: {image_limits} / {total_limits}")
            self.watch_move_data_path()
            checker = Checker(self.config, self.database)
            checker.check_gid_in_local_cbz()
            checker.sync_local_to_sqlite_cbz(cover=True)

            add_fav_data = AddFavData(self.config, self.database, self.eh_client)
            await add_fav_data.update_category()
            try:
                if method == 1:
                    await add_fav_data.post_fav_data()
                    await add_fav_data.update_meta_data(True)
                elif method == 2:
                    await add_fav_data.post_fav_data(url_params="?f_search=&inline_set=fs_p", get_all=False)
                    await add_fav_data.update_meta_data()
                elif method == 3:
                    await add_fav_data.update_meta_data()
            except FavoritesFetchError as exc:
                # Nothing was written, but cleaning up from a failed fetch could move downloaded files away.
                logger.error(f"Skipping this round, local galleries are untouched: {exc}")
                await asyncio.sleep(60 * 60)
                continue

            update_list = await add_fav_data.clear_del_flag()
            with self.database.connection() as co:
                if self.config.watch_fav_ids is not None:
                    watch_fav_ids = [value.strip() for value in self.config.watch_fav_ids.split(",") if value.strip()]
                    if watch_fav_ids:
                        placeholders = ",".join(["?"] * len(watch_fav_ids))
                        query = f"SELECT gid FROM fav_category WHERE fav_id IN ({placeholders})"
                        params = watch_fav_ids
                    else:
                        query = "SELECT gid FROM fav_category WHERE fav_id IN (?,?,?,?,?,?,?,?,?,?)"
                        params = list(range(10))
                else:
                    query = "SELECT gid FROM fav_category WHERE fav_id IN (?,?,?,?,?,?,?,?,?,?)"
                    params = list(range(10))
                total_gids = {gid[0] for gid in co.execute(query, params).fetchall()}
            fav_update_list = [item for item in update_list if item[0] in total_gids]

            gids = [item[0] for item in fav_update_list]
            clear_old_file(self.database, self.config.gallery_path, self.config.del_path, gids)
            current_gids = [item[2] for item in fav_update_list]
            await self.dl_new_gallery(gids=",".join(map(str, current_gids)))
            self.watch_move_data_path()
            await add_fav_data.clear_del_flag()

            await self.dl_new_gallery(fav_cat=self.config.watch_fav_ids)
            self.watch_move_data_path()
            if self.config.watch_lan_status:
                rename_cbz_file(self.config.gallery_path)
                await LANraragi(self.config, self.database, watch_status=True).lan_update_tags()
            if self.config.tags_translation:
                await add_fav_data.translate_tags()
            await add_fav_data.clear_del_flag()
            checker.clear_old_file()

            sleep_time = 60 * 60
            logger.info(f"Done! Wait {sleep_time} s")
            await asyncio.sleep(sleep_time)


def unzip_data_path(data_path):
    for folder_name in os.listdir(data_path):
        file_path = os.path.join(data_path, folder_name)
        if os.path.isfile(file_path) and folder_name.endswith(".cbz") and re.match(r"^\d+-", folder_name):
            extract_to = os.path.join(data_path, os.path.splitext(folder_name)[0])
            if os.path.exists(extract_to):
                shutil.rmtree(extract_to)
            os.makedirs(extract_to, exist_ok=True)
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(extract_to)
                logger.info(f"Unzipped: {file_path} to {extract_to}")
