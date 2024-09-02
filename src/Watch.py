import asyncio
import os
import shutil
import zipfile

from src import Support, Checker, DownloadWebGallery, AddFavData, DownloadArchiveGallery
from .common import *


class Watch(Config):
    def __init__(self):
        super().__init__()

    @logger.catch
    def watch_move_data_path(self):
        """
        移动 data_path 目录下的 web 和 archive 文件夹下的以 gid- 开头的文件及文件夹到到 data_path 目录
        Here is the translation:

        Move the files and folders starting with 'gid-' from the `web` and `archive` folders under the
        `data_path` directory to the `data_path` directory.
        """
        os.makedirs(self.data_path, exist_ok=True)
        for folder_name in os.listdir(self.data_path):
            if folder_name == 'web' or folder_name == 'archive':
                sub_path = os.path.join(self.data_path, folder_name)
                for sub_name in os.listdir(sub_path):
                    if re.match(r'^\d+-', sub_name):
                        full_path = os.path.join(sub_path, sub_name)
                        dest_path = os.path.join(self.data_path, sub_name)
                        shutil.move(full_path, dest_path)
                        logger.info(f"Moved: {full_path} -> {dest_path}")

    @logger.catch
    def clear_old_file(self, move_list):
        """
        将目标文件/文件夹 移动到 del 文件夹下
        Move the target file/folder to the `del` folder.

        :param move_list: [gid1, gid2, gid3]
        """
        del_dir = os.path.join(self.data_path, 'del')
        os.makedirs(del_dir, exist_ok=True)
        with sqlite3.connect(Config().dbs_name) as co:
            for gid in move_list:
                for folder_name in os.listdir(self.data_path):
                    folder_path = os.path.join(self.data_path, folder_name)
                    if folder_name.startswith(f"{gid}-"):
                        dest_path = os.path.join(del_dir, folder_name)
                        if os.path.exists(dest_path):
                            timestamp = time.strftime("%Y%m%d%H%M%S")
                            dest_path = os.path.join(del_dir, f"{folder_name}_{timestamp}")
                        shutil.move(folder_path, dest_path)
                        co.execute(
                            f"UPDATE fav_category SET original_flag = 0 , web_1280x_flag = 0 WHERE gid = {gid}")
                        co.commit()
                        logger.info(f"Moved: {folder_path} -> {dest_path}")

    @logger.catch()
    async def dl_new_gallery(self, fav_cat="", gids="", archive_status=False):
        dl_list_status = True
        dl_list = []
        if fav_cat != "":
            dl_list = get_web_gallery_download_list(fav_cat=self.watch_fav_ids)
        if gids != "":
            dl_list = get_web_gallery_download_list(gids=gids)
        if not dl_list:
            return True
        for j in dl_list:
            if archive_status:
                # 归档默认下载 Resample(1280x) 版本
                # Archive the default download Resample(1280x) version
                status = await DownloadArchiveGallery().dl_gallery(gid=j[0], token=j[1], title=j[2],
                                                                   original_flag=False)
            else:
                download_gallery = DownloadWebGallery(gid=j[0], token=j[1], title=j[2])
                status = await download_gallery.apply()
            if not status:
                dl_list_status = False
                logger.warning(f"Download https://{Config().base_url}/g/{j[0]}/{j[1]} failed")
        return dl_list_status

    @logger.catch
    async def apply(self):
        while True:
            image_limits, total_limits = await Config().get_image_limits()
            logger.info(f"Image Limits: {image_limits} / {total_limits}")
            self.watch_move_data_path()
            Checker().check_gid_in_local_cbz()
            Checker().sync_local_to_sqlite_cbz(cover=True)

            add_fav_data = AddFavData()
            # await add_fav_data.add_tags_data(True)
            if Config().tags_translation:
                await add_fav_data.translate_tags()

            # update_list = await add_fav_data.apply()
            update_list = await add_fav_data.clear_del_flag()
            gids = [item[0] for item in update_list]
            current_gids = [item[2] for item in update_list]
            self.clear_old_file(move_list=gids)
            # 下载新画廊 / Download new gallery
            while True:
                dl_list_status = await self.dl_new_gallery(gids=str(current_gids).replace("[", "").replace("]", ""),
                                                           archive_status=self.watch_archive_status)
                # 下载失败重新下载 / Download failed, retrying download
                if dl_list_status:
                    break
                else:
                    logger.warning("Download failed, retry in 120 seconds")
                    await asyncio.sleep(120)
            # 再次同步数据 / Sync data again
            Checker().sync_local_to_sqlite_cbz(True)
            # 清理数据库中del=1的字段 / Clean up fields with del=1 in the database
            await add_fav_data.clear_del_flag()

            # 下载收藏夹 / Download Favorite
            while True:
                dl_list_status = await self.dl_new_gallery(fav_cat=self.watch_fav_ids,
                                                           archive_status=self.watch_archive_status)
                # 下载失败重新下载 / Download failed, retrying download
                if dl_list_status:
                    break
                else:
                    logger.warning("Download failed, retry in 120 seconds")
                    await asyncio.sleep(120)

            self.watch_move_data_path()
            if self.watch_lan_status:
                await Support().lan_update_tags()

            sleep_time = 60 * 60
            logger.info(f"Done! Wait {sleep_time} s")
            # 1小时后重新检查 / Recheck in 1 hour
            await asyncio.sleep(sleep_time)


@logger.catch
def unzip_data_path(data_path):
    """
    解压 data_path 目录下的以 gid- 开头的 CBZ 文件(不会删除CBZ)
    Unzip CBZ files starting with gid- in the data_path directory (do not delete the CBZ files).
    """
    for folder_name in os.listdir(data_path):
        file_path = os.path.join(data_path, folder_name)
        if os.path.isfile(file_path) and folder_name.endswith('.cbz') and re.match(r'^\d+-', folder_name):
            extract_to = os.path.join(data_path, os.path.splitext(folder_name)[0])
            if os.path.exists(extract_to):
                shutil.rmtree(extract_to)
            os.makedirs(extract_to, exist_ok=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
                logger.info(f"Unzipped: {file_path} to {extract_to}")
