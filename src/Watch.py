import asyncio
import zipfile

from src import Checker, DownloadWebGallery, AddFavData, DownloadArchiveGallery
from .common import *


class Watch(Config):
    def __init__(self):
        super().__init__()

    @logger.catch
    def watch_move_data_path(self):
        """
        web 和 archive 目录下的以 gid- 开头的 CBZ 文件到 data_path 根目录

        Move the CBZ files starting with gid- from the web and archive directories to the data_path root directory.
        """
        os.makedirs(self.data_path, exist_ok=True)
        for folder_name in os.listdir(self.data_path):
            if folder_name == 'web' or folder_name == 'archive':
                sub_path = os.path.join(self.data_path, folder_name)
                for sub_name in os.listdir(sub_path):
                    if re.match(r'^\d+-.*\.cbz$', sub_name) and os.path.isfile(os.path.join(sub_path, sub_name)):
                        full_path = os.path.join(sub_path, sub_name)
                        dest_path = os.path.join(self.data_path, sub_name)
                        shutil.move(full_path, dest_path)
                        logger.info(f"Moved: {full_path} -> {dest_path}")

    @logger.catch()
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

    @logger.catch
    async def apply(self):
        while True:
            image_limits, total_limits = await self.get_image_limits()
            logger.info(f"Image Limits: {image_limits} / {total_limits}")
            self.watch_move_data_path()
            Checker().check_gid_in_local_cbz()
            Checker().sync_local_to_sqlite_cbz(cover=True)

            # 更新 tags 信息, 用于判断是否存在新画廊
            # Update tags information to determine if a new gallery exists.
            add_fav_data = AddFavData()
            await add_fav_data.add_tags_data(True)
            if self.tags_translation:
                await add_fav_data.translate_tags()

            # 清理旧画廊并下载新画廊 / Clean up old galleries and download new galleries.
            update_list = await add_fav_data.apply()
            # update_list = await add_fav_data.clear_del_flag()
            gids = [item[0] for item in update_list]
            clear_old_file(move_list=gids)
            current_gids = [item[2] for item in update_list]
            await self.dl_new_gallery(gids=str(current_gids).replace("[", "").replace("]", ""),
                                      archive_status=self.watch_archive_status)
            self.watch_move_data_path()
            await add_fav_data.clear_del_flag()

            await self.dl_new_gallery(fav_cat=self.watch_fav_ids, archive_status=self.watch_archive_status)
            self.watch_move_data_path()
            if self.watch_lan_status:
                await Support(watch_status=True).lan_update_tags()

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
