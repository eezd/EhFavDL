import json
import os
import re
import shutil
import sqlite3
import sys
import time

from loguru import logger

from src.Config import Config


def get_web_gallery_download_list(fav_cat="", gids=""):
    dl_list = []
    with sqlite3.connect(Config().dbs_name) as co:
        _sql = ""
        if fav_cat != "":
            _sql += f"AND fc.fav_id IN ({fav_cat}) "
        if gids != "":
            _sql += f"AND eh.gid IN ({gids}) "
        if fav_cat == "" and gids == "":
            logger.warning("fav_cat AND gids both are empty.")
            sys.exit(1)
        ce = co.execute(f'''
        SELECT
                fc.gid,
                fc.token,
                eh.title,
                eh.title_jpn 
        FROM
                eh_data AS eh,
                fav_category AS fc 
        WHERE
                fc.web_1280x_flag = 0 
                AND fc.original_flag = 0
                AND fc.del_flag = 0
                AND eh.copyright_flag = 0 
                AND eh.gid = fc.gid 
                {_sql} 
        ORDER BY
                fc.gid DESC
        ''').fetchall()
        for i in ce:
            if i[3] is not None and i[3] != "":
                title = str(i[3])
                dl_list.append([i[0], i[1], title])
            else:
                title = str(i[2])
                dl_list.append([i[0], i[1], title])
    logger.info(
        f"(fav_cat = {fav_cat}) total download list:{json.dumps(dl_list, indent=4, ensure_ascii=False)}\n(len: {len(dl_list)})\n")
    return dl_list


def clear_old_file(move_list):
    """
    将目标文件/文件夹 移动到 del 文件夹下
    Move the target file/folder to the `del` folder.

    :param move_list: [gid1, gid2, gid3]
    """
    self = Config()
    del_dir = os.path.join(self.data_path, 'del')
    os.makedirs(del_dir, exist_ok=True)
    with sqlite3.connect(self.dbs_name) as co:
        for gid in move_list:
            for folder_name in os.listdir(self.data_path):
                folder_path = os.path.join(self.data_path, folder_name)
                if folder_name.startswith(f"{gid}-"):
                    dest_path = os.path.join(del_dir, folder_name)
                    if os.path.exists(dest_path):
                        timestamp = time.strftime("%Y%m%d%H%M%S")
                        dest_path = os.path.join(del_dir, f"{folder_name}_{timestamp}")
                    shutil.move(folder_path, dest_path)
                    co.execute(f'''DELETE FROM fav_category WHERE gid = {gid} ''')
                    co.commit()
                    logger.info(f"Moved: {folder_path} -> {dest_path}")


def get_time():
    """
    获取当前时间戳

    Get the current timestamp
    :return:
        int(time)
    """
    return int(round(time.time()))


def remove_duplicates_2d_array(arr):
    seen = []
    result = []
    for sub_array in arr:
        if sub_array not in seen:
            result.append(sub_array)
            seen.append(sub_array)
    return result


def xml_escape(title):
    # XML
    title = str(title).replace("&", r"&amp;").replace("<", r"&lt;").replace(">", "&gt;").replace('"', "&quot;").replace(
        "'", "&apos;")
    return title


def windows_escape(title):
    return re.sub(r'''[\\/:*?"<>|]''', '', title)
