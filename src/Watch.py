import asyncio
import sys

from src import DownloadWebGallery, AddFavData, DownloadArchiveGallery, LANraragi
from src.Utils import *


class Watch(Config):
    def __init__(self):
        super().__init__()

    def watch_move_data_path(self):
        """
        web 和 archive 目录下的以 gid- 开头的 CBZ 文件到 data_path 根目录

        Move the CBZ files starting with gid- from the web and archive directories to the data_path root directory.
        """
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.gallery_path, exist_ok=True)
        os.makedirs(self.web_path, exist_ok=True)
        os.makedirs(self.archive_path, exist_ok=True)
        for sub_name in os.listdir(self.web_path):
            if re.match(r'^\d+-.*\.cbz$', sub_name) and os.path.isfile(os.path.join(self.web_path, sub_name)):
                full_path = os.path.join(self.web_path, sub_name)
                dest_path = os.path.join(self.gallery_path, sub_name)
                shutil.move(full_path, dest_path)
                logger.info(f"Moved: {full_path} -> {dest_path}")
        for sub_name in os.listdir(self.archive_path):
            if re.match(r'^\d+-.*\.cbz$', sub_name) and os.path.isfile(os.path.join(self.archive_path, sub_name)):
                full_path = os.path.join(self.archive_path, sub_name)
                dest_path = os.path.join(self.gallery_path, sub_name)
                shutil.move(full_path, dest_path)
                logger.info(f"Moved: {full_path} -> {dest_path}")

    async def dl_new_gallery(self, fav_cat="", gids="", archive_status=False):
        dl_list = []
        failed_gid_list = ""
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
            elif len(dl_list) == 3 and j[0] == 1633417:
                status = False
            elif len(dl_list) == 3 and j[0] == 1633421:
                status = False
            else:
                download_gallery = DownloadWebGallery(gid=j[0], token=j[1], title=j[2])
                status = await download_gallery.apply()
            if not status:
                failed_gid_list += "," + str(j[0])
                logger.warning(f"Download https://{self.base_url}/g/{j[0]}/{j[1]} failed")

        # 下载失败重新下载 / Download failed, retrying download
        failed_gid_list = failed_gid_list[1:]
        if len(failed_gid_list) > 0:
            logger.warning(f"Download failed, retry in 30 seconds. gids = {failed_gid_list}")
            await asyncio.sleep(30)
            return await self.dl_new_gallery(gids=failed_gid_list)
        return True

    async def apply(self, method=1):
        while True:
            image_limits, total_limits = await self.get_image_limits()
            logger.info(f"Image Limits: {image_limits} / {total_limits}")
            # self.watch_move_data_path()
            # Checker().check_gid_in_local_cbz()
            # Checker().sync_local_to_sqlite_cbz(cover=True)

            # 更新 tags 信息, 用于判断是否存在新画廊
            # Update tags information to determine if a new gallery exists.
            add_fav_data = AddFavData()
            await add_fav_data.update_category()
            if method == 1:
                await add_fav_data.post_fav_data()
                await add_fav_data.update_meta_data(True)
            elif method == 2:
                await add_fav_data.post_fav_data(url_params="?f_search=&inline_set=fs_p", get_all=False)
                await add_fav_data.update_meta_data()
            elif method == 3:
                await add_fav_data.update_meta_data()

            update_list = await add_fav_data.clear_del_flag()
            fav_update_list = []
            # watch_fav_ids
            with sqlite3.connect(self.dbs_name) as co:
                if self.watch_fav_ids is not None:
                    query = "SELECT gid FROM fav_category WHERE fav_id IN ({})".format(
                        ",".join("?" * len(self.watch_fav_ids.split(",")))
                    )
                    params = self.watch_fav_ids.split(",")
                else:
                    query = "SELECT gid FROM fav_category WHERE fav_id IN (0,1,2,3,4,5,6,7,8,9)"
                    params = []
                total_gids = co.execute(query, params).fetchall()
                if total_gids is not None:
                    total_gids = {gid[0] for gid in total_gids}
                    for item in update_list:
                        if item[0] in total_gids:
                            fav_update_list.append(item)

            gids = [item[0] for item in fav_update_list]
            clear_old_file(move_list=gids)
            current_gids = [item[2] for item in fav_update_list]
            await self.dl_new_gallery(gids=str(current_gids).replace("[", "").replace("]", ""))
            self.watch_move_data_path()
            await add_fav_data.clear_del_flag()

            await self.dl_new_gallery(fav_cat=self.watch_fav_ids)
            self.watch_move_data_path()
            if self.watch_lan_status:
                await LANraragi(watch_status=True).lan_update_tags()

            if self.tags_translation:
                await add_fav_data.translate_tags()

            sleep_time = 60 * 60
            logger.info(f"Done! Wait {sleep_time} s")
            # 1小时后重新检查 / Recheck in 1 hour
            await asyncio.sleep(sleep_time)


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
