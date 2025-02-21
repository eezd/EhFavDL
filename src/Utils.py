import base64
import json
import os
import re
import shutil
import sqlite3
import sys
import time
import zipfile

from loguru import logger
from tqdm import tqdm

from src.Config import Config

self = Config()


def get_web_gallery_download_list(fav_cat="", gids=""):
    dl_list = []
    with sqlite3.connect(self.dbs_name) as co:
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
    del_dir = self.del_path
    os.makedirs(del_dir, exist_ok=True)
    with sqlite3.connect(self.dbs_name) as co:
        for gid in move_list:
            for folder_name in os.listdir(self.gallery_path):
                folder_path = os.path.join(self.gallery_path, folder_name)
                if folder_name.startswith(f"{gid}-"):
                    dest_path = os.path.join(del_dir, folder_name)
                    if os.path.exists(dest_path):
                        timestamp = time.strftime("%Y%m%d%H%M%S")
                        dest_path = os.path.join(del_dir, f"{folder_name}_{timestamp}")
                    shutil.move(folder_path, dest_path)
                    co.execute(f'''DELETE FROM fav_category WHERE gid = {gid} ''')
                    co.commit()
                    logger.info(f"Moved: {folder_path} -> {dest_path}")


def create_cbz(src_path, target_path=""):
    """
    创建一个 CBZ 文件, 默认在当前位置创建
    Create a CBZ file, defaulting to the current location.
    """
    if target_path == "":
        target_path = src_path + ".cbz"
    elif not target_path.endswith(".cbz"):
        target_path = target_path + ".cbz"
    with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_STORED) as cbz:
        for root, _, files in os.walk(src_path):
            for file in files:
                file_path = os.path.join(root, file)
                # 使用os.path.relpath()获取文件相对于目录的路径
                # Using os.path.relpath() to get the file path relative to a directory.
                cbz.write(file_path, os.path.relpath(file_path, src_path))
    logger.info(f'Create CBZ: {target_path}')


def directory_to_cbz(target_path=""):
    """
    转换 gid- 文件夹为CBZ文件
    Convert the "gid-" folders under self.gallery_path to CBZ files
    """
    logger.info(f'Create CBZ ...')
    if target_path == "":
        target_path = self.gallery_path
    path_list = []
    for i in os.listdir(target_path):
        if not re.match(r'^\d+-', i) or os.path.isfile(os.path.join(target_path, i)):
            continue
        path_list.append(os.path.join(target_path, i))
    logger.info(f'Total {len(path_list)}...')
    with tqdm(total=len(path_list)) as progress_bar:
        for i in path_list:
            create_cbz(src_path=i)
            progress_bar.update(1)
    logger.info(f'[OK] Create CBZ')


def rename_cbz_file(target_path=""):
    """
    重命名  (gid-name.cbz) OR (gid-name-1280x.cbz)  CBZ文件
    Rename the CBZ file (gid-name.cbz) OR (gid-name-1280x.cbz).

    限制文件名称最长 80位 并且转化为 base64 不超过196位
    Limit the file name to a maximum of 80 characters and ensure that its base64 encoding does not exceed 196 characters.
    """
    if target_path == "":
        target_path = self.gallery_path
    for i in os.listdir(target_path):
        if not re.match(r'^\d+-', i) or os.path.isdir(os.path.join(target_path, i)):
            continue
        if not i.endswith(".cbz"):
            continue
        new_i = i.replace(".cbz", "")
        # -1280x
        web_1280x_flag = False
        if new_i.find("-1280X") != -1 or new_i.find("-1280x") != -1:
            new_i = new_i.replace("-1280x", "")
            new_i = new_i.replace("-1280X", "")
            web_1280x_flag = True
        base64_max_len = 196
        if len(str(base64.b64encode(new_i.encode('utf-8')))) > base64_max_len or len(new_i) > 80:
            while len(str(base64.b64encode(new_i.encode('utf-8')))) > base64_max_len:
                new_i = new_i[:-1]
            if len(new_i) > 80:
                new_i = new_i[:80]
            new_name = new_i + (".cbz" if not web_1280x_flag else "-1280x.cbz")
            shutil.move(os.path.join(target_path, i), os.path.join(target_path, new_name))
            logger.info(F"\nold_name: {i} \n new_name: {new_name} \n")
        elif web_1280x_flag and "-1280X" in i:
            new_name = i.replace("-1280X", "-1280x")
            shutil.move(os.path.join(target_path, i), os.path.join(target_path, new_name))
            logger.info(F"\nold_name: {i} \n new_name: {new_name} \n")


def rename_gid_name(target_path=""):
    """
    根据 gid 重命名名称, 默认使用 title_jpn
    Rename the name based on gid, defaulting to title_jpn.
    """
    if target_path == "":
        target_path = self.gallery_path

    with sqlite3.connect(self.dbs_name) as co:
        for item in os.listdir(target_path):
            if not re.match(r'^\d+-', item):
                continue
            web_str = ""
            if item.find("-1280x") != -1:
                web_str = "-1280x"
            gid = re.match(r'^(\d+)-', item).group(1)
            co_title = co.execute(f'''SELECT title,title_jpn FROM eh_data WHERE gid="{gid}"''').fetchone()
            if co_title is not None:
                if co_title[1] is not None and co_title[1] != "":
                    title = str(co_title[1])
                else:
                    title = str(co_title[0])
                title = windows_escape(title)
                old_path = os.path.join(target_path, item)
                if os.path.isfile(old_path):
                    ext = os.path.splitext(item)[1]
                    new_name = f"{gid}-{title}{web_str}{ext}"
                else:
                    new_name = f"{gid}-{title}{web_str}"
                new_path = os.path.join(target_path, new_name)
                if not os.path.exists(new_path):
                    logger.warning(f'rename: {old_path} -> {new_path}')
                    shutil.move(old_path, new_path)
                else:
                    logger.warning(f'Skipping rename, target already exists: {new_path}')


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
    return re.sub(r'''[\\/:*?"<>|\t]''', '', title)
