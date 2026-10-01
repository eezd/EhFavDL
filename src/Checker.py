import os.path
import re
import sqlite3
import sys
import zipfile

from loguru import logger

from src.Service import Service
from src.Utils import collect_gid_cbz_groups, move_path_with_collision


class Checker(Service):
    def __init__(self, config, database):
        super().__init__(config, database)

    def check_gid_in_local_cbz(self, target_path=""):
        """
        移动目录下的重复 gid 的 CBZ 文件到 duplicate_del 文件夹
        Move CBZ files with duplicate GIDs in the directory to the `duplicate_del` folder.
        """
        if target_path == "":
            target_path = self.gallery_path

        gid_list_original, gid_list_1280x = collect_gid_cbz_groups(target_path)
        os.makedirs(self.duplicate_del_path, exist_ok=True)

        for label, gid_map in (("gid_list_original", gid_list_original), ("gid_list_1280x", gid_list_1280x)):
            for gid, name_list in gid_map.items():
                if len(name_list) <= 1:
                    continue
                name_list.sort()
                for duplicate_name in name_list[1:]:
                    old_path = os.path.join(target_path, duplicate_name)
                    new_path = move_path_with_collision(old_path, self.duplicate_del_path)
                    logger.warning(f'({label}) Duplicate gid {gid}, Move: {old_path} -> {new_path}')
        logger.info(f'gid_list_1280x count: {len(gid_list_1280x)}')
        logger.info(f'gid_list_original count: {len(gid_list_original)}')

    def sync_local_to_sqlite_cbz(self, cover=False, target_path=""):
        """
        cover=True 重置 fav_category 表 original_flag 和 web_1280x_flag 字段值, 根据本地文件重新设置
        If `cover=True`, reset the `original_flag` and `web_1280x_flag` fields in the `fav_category` table,
         and then reconfigure them based on the local files.
        """
        if target_path == "":
            target_path = self.gallery_path
        # Real *.cbz files only, and '-1280x' matched case-insensitively, like the duplicate check.
        original, web_1280x = collect_gid_cbz_groups(target_path)
        gid_list_1280x = sorted(web_1280x)
        gid_list_original = sorted(original)
        logger.info(f'gid_list_1280x count: {len(gid_list_1280x)}')
        logger.info(f'gid_list_original count: {len(gid_list_original)}')
        with sqlite3.connect(self.dbs_name) as co:
            if cover:
                co.execute('UPDATE fav_category SET original_flag=0, web_1280x_flag=0')
            if gid_list_1280x:
                co.executemany('UPDATE fav_category SET web_1280x_flag=1 WHERE gid = ?', ((data,) for data in gid_list_1280x))
            if gid_list_original:
                co.executemany('UPDATE fav_category SET original_flag=1 WHERE gid = ?', ((data,) for data in gid_list_original))
            co.commit()
            web_len = co.execute('SELECT count(*) FROM fav_category WHERE web_1280x_flag = 1').fetchone()[0]
            original_len = co.execute('SELECT count(*) FROM fav_category WHERE original_flag = 1').fetchone()[0]
            logger.info(f'Finish sync local to sqlite. web_1280x_flag: {web_len}, original_flag: {original_len}')
            logger.info(f'Finish sync local to sqlite.')
    def clear_old_file(self, target_path=""):
        """
        清理本地旧画廊文件
        Clean up old gallery files in the local directory.
        """
        if target_path == "":
            target_path = self.gallery_path
        with sqlite3.connect(self.dbs_name) as co:
            # Same matching as the duplicate check: real *.cbz files only (not .cbz-tmp, .cbz.bak or directories).
            original, web_1280x = collect_gid_cbz_groups(target_path)
            for names in (*original.values(), *web_1280x.values()):
                for i in names:
                    gid = re.match(r'^(\d+)-', i).group(1)
                    data = co.execute('SELECT gid, current_gid FROM eh_data WHERE gid = ?', (gid,)).fetchone()
                    if data is None:
                        logger.warning(f'No metadata found for local gallery: {i}')
                        continue
                    if data[0] != data[1]:
                        # Only move an old version once its current version is available locally.
                        replaced = co.execute(
                            'SELECT 1 FROM fav_category WHERE gid = ? AND (original_flag = 1 OR web_1280x_flag = 1)',
                            (data[1],),
                        ).fetchone()
                        if replaced is None:
                            logger.info(f'Keeping {i}: its current version {data[1]} is not downloaded')
                            continue
                        folder_path = os.path.join(target_path, i)
                        dest_path = move_path_with_collision(folder_path, self.del_path)
                        logger.info(f"Moved: {folder_path} -> {dest_path}")

    def check_loc_file(self):
        folder = input(f"Please enter the file directory.\n")
        if folder == "":
            print("Cancel")
            sys.exit(1)
        loc_gid = []
        status = 0
        for root, dirs, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.getsize(file_path) > 0:
                    try:
                        with zipfile.ZipFile(file_path, 'r') as zip_file:
                            bad_file = zip_file.testzip()
                            if bad_file:
                                logger.error(f"检测到压缩包损坏, 请删除文件: {file_path}")
                                logger.error(f"Detected a corrupted archive. Please delete the file.: {file_path}")
                            else:
                                file = str(file)
                                if len(file.split(".zip")) != 1:
                                    loc_gid.append(file.split("-")[0])
                    except zipfile.BadZipFile:
                        logger.error(f"检测到压缩包损坏, 请删除文件: {file_path}")
                        logger.error(f"Detected a corrupted archive. Please delete the file.: {file_path}")
                        status = 1
                    except OSError:
                        logger.error(f"检测到压缩包损坏, 请删除文件: {file_path}")
                        logger.error(f"Detected a corrupted archive. Please delete the file.: {file_path}")
                        status = 1
        if status == 1:
            sys.exit(1)
        return loc_gid
