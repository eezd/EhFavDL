import os
import re
import shutil
import sqlite3
import time

from loguru import logger


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


def sync_local_dir_name(data_path, dbs_name):
    """
    根据 GID 重命名文件夹名字
    """
    for i in os.listdir(data_path):
        if i.find('-') == -1 or os.path.isfile(os.path.join(data_path, i)):
            continue

        gid = i.split("-")[0]
        with sqlite3.connect(dbs_name) as co:
            co = co.execute(f'SELECT TITLE_JPN FROM FAV WHERE GID="{gid}"')
            db_pages = co.fetchone()
            if db_pages is not None:
                title = db_pages[0]
                ole_path = os.path.join(data_path, i)
                new_path = os.path.join(data_path, f"{gid}-{windows_escape(title)}")
                shutil.move(ole_path, new_path)
            else:
                logger.warning(f"找不到该GID: {gid}")
                continue
