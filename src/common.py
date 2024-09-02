import json
import re
import sqlite3
import time

from loguru import logger

from src.Config import Config


def get_web_gallery_download_list(fav_cat):
    dl_list = []
    with sqlite3.connect(Config().dbs_name) as co:
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
            AND eh.copyright_flag = 0 
            AND eh.gid = fc.gid 
            AND fc.fav_id IN ({fav_cat}) 
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
