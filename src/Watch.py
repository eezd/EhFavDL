import asyncio
import os
import shutil
import zipfile

from . import Support, Checker, AddFavData, DownloadWebGallery
from .common import *


class Watch(Config):
    def __init__(self):
        super().__init__()

    def watch_move_data_path(self):
        """
        移动 data_path 目录下的 web 和 archive 文件夹下的以 gid- 开头的文件和文件夹到到 data_path 目录
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

    def clear_old_file(self, move_list):
        """
        将目标文件/文件夹 移动到 del 文件夹下

        只需传入 old_gid
        move_list: [old_gid, old_token, new_gid, new_token]
        """
        del_dir = os.path.join(self.data_path, 'del')
        os.makedirs(del_dir, exist_ok=True)
        for gid in move_list:
            for folder_name in os.listdir(self.data_path):
                folder_path = os.path.join(self.data_path, folder_name)
                if os.path.isdir(folder_path) and folder_name.startswith(f"{gid}-"):
                    dest_path = os.path.join(del_dir, folder_name)
                    if os.path.exists(dest_path):
                        timestamp = time.strftime("%Y%m%d%H%M%S")
                        dest_path = os.path.join(del_dir, f"{folder_name}_{timestamp}")
                    shutil.move(folder_path, dest_path)
                    logger.info(f"Moved: {folder_path} -> {dest_path}")

    async def apply(self):
        """
        1. 移动 data_path/web 以及 data_path/archive 的以 gid- 开头的文件和文件夹到 data_path 目录
        2. Support().create_xml() Support().directory_to_zip() Support().rename_zip_file()
        3. 执行Checker().sync_local_to_sqlite_zip(True)重置数据库下载状态
        2. 更新数据信息
        3. 开始下载
        """

        while True:
            image_limits, total_limits = await Config().get_image_limits()
            logger.info(f"Image Limits: {image_limits} / {total_limits}")
            self.watch_move_data_path()
            Checker().check_gid_in_local_cbz()
            Checker().sync_local_to_sqlite_cbz(True)

            add_fav_data = AddFavData()
            await add_fav_data.add_tags_data(True)
            if Config().tags_translation:
                await add_fav_data.translate_tags()

            update_list = await add_fav_data.apply()
            self.clear_old_file(move_list=gid for gid in update_list)
            Checker().sync_local_to_sqlite_cbz(True)

            while True:
                dl_list_status = True
                dl_list = get_web_gallery_download_list(fav_cat=self.watch_fav_ids)
                for j in dl_list:
                    download_gallery = DownloadWebGallery(gid=j[0], token=j[1], title=j[2])
                    status = await download_gallery.apply()
                    if not status:
                        dl_list_status = False
                        logger.warning(f"Download https://{Config().base_url}/g/{j[0]}/{j[1]} failed")

                # 下载失败则重新下载
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
            # 1小时后重新检查
            await asyncio.sleep(sleep_time)


def unzip_data_path(data_path):
    """
    解压 data_path 目录下的以 gid- 开头的 CBZ 文件(不会删除CBZ)
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
