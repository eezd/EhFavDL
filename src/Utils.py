import base64
import json
import os
import re
import shutil
import sys
import time
import zipfile

from loguru import logger
from tqdm import tqdm



def _split_csv_values(raw_values):
    if raw_values is None or raw_values == "":
        return []
    if isinstance(raw_values, (list, tuple, set)):
        values = raw_values
    else:
        values = str(raw_values).split(",")
    return [str(value).strip() for value in values if str(value).strip()]


def collect_gid_cbz_groups(target_path):
    """
    收集目录下按 gid 分组的 CBZ 文件，分别返回原图和 1280x 版本。
    """
    gid_list_original = {}
    gid_list_1280x = {}

    for name in os.listdir(target_path):
        full_path = os.path.join(target_path, name)
        if not re.match(r'^\d+-.*\.cbz$', name) or not os.path.isfile(full_path):
            continue
        gid = re.match(r'^(\d+)-', name).group(1)
        if '-1280x' in name.lower():
            gid_list_1280x.setdefault(gid, []).append(name)
        else:
            gid_list_original.setdefault(gid, []).append(name)

    return gid_list_original, gid_list_1280x


def move_path_with_collision(old_path, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    base_name = os.path.basename(old_path)
    dest_path = os.path.join(dest_dir, base_name)
    if os.path.exists(dest_path):
        timestamp = time.strftime("%Y%m%d%H%M%S")
        root, ext = os.path.splitext(base_name)
        suffix = 0
        while True:
            suffix_part = "" if suffix == 0 else f"_{suffix}"
            tail = f"_{timestamp}{suffix_part}{ext}"
            # A name that already fills the limit would overflow once the tail is added, so shorten the root.
            root_fit = truncate_utf8(root, MAX_FILENAME_BYTES - len(tail.encode("utf-8")))
            dest_path = os.path.join(dest_dir, root_fit + tail)
            if not os.path.exists(dest_path):
                break
            suffix += 1
    shutil.move(old_path, dest_path)
    return dest_path


def get_web_gallery_download_list(database, fav_cat="", gids=""):
    dl_list = []
    with database.connection() as co:
        fav_cat_values = _split_csv_values(fav_cat)
        gid_values = _split_csv_values(gids)
        if not fav_cat_values and not gid_values:
            logger.warning("fav_cat AND gids both are empty.")
            sys.exit(1)

        sql_params = []
        sql_conditions = []
        if fav_cat_values:
            sql_conditions.append(f"fc.fav_id IN ({','.join(['?'] * len(fav_cat_values))})")
            sql_params.extend(fav_cat_values)
        if gid_values:
            sql_conditions.append(f"eh.gid IN ({','.join(['?'] * len(gid_values))})")
            sql_params.extend(gid_values)

        extra_sql = ""
        if sql_conditions:
            extra_sql = " AND " + " AND ".join(sql_conditions)

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
                {extra_sql}
        ORDER BY
                fc.gid DESC
        ''', sql_params).fetchall()
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


def clear_old_file(database, gallery_path, del_path, move_list):
    """
    将目标文件/文件夹移动到 del 文件夹下。
    Move target files/folders to the del directory.
    """
    del_dir = del_path
    os.makedirs(del_dir, exist_ok=True)
    gallery_map = {}
    for folder_name in os.listdir(gallery_path):
        match = re.match(r'^([0-9]+)-', folder_name)
        if match:
            gallery_map.setdefault(match.group(1), []).append(folder_name)

    with database.connection() as co:
        delete_targets = []
        for gid in move_list:
            for folder_name in gallery_map.get(str(gid), []):
                folder_path = os.path.join(gallery_path, folder_name)
                dest_path = move_path_with_collision(folder_path, del_dir)
                delete_targets.append((gid,))
                logger.info(f"Moved: {folder_path} -> {dest_path}")
        if delete_targets:
            co.executemany('DELETE FROM fav_category WHERE gid = ?', delete_targets)
        co.commit()


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


def directory_to_cbz(target_path):
    """Convert gid-named folders under target_path to CBZ files."""
    logger.info('Create CBZ ...')
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


def rename_cbz_file(target_path):
    """Normalize CBZ file names under target_path."""
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


def rename_gid_name(database, target_path):
    """Rename files and folders using titles stored in database."""

    with database.connection() as co:
        for item in os.listdir(target_path):
            if not re.match(r'^\d+-', item):
                continue
            web_str = ""
            if item.find("-1280x") != -1:
                web_str = "-1280x"
            gid = re.match(r'^(\d+)-', item).group(1)
            co_title = co.execute('''SELECT title,title_jpn FROM eh_data WHERE gid=?''', (gid,)).fetchone()
            if co_title is not None:
                if co_title[1] is not None and co_title[1] != "":
                    title = str(co_title[1])
                else:
                    title = str(co_title[0])
                old_path = os.path.join(target_path, item)
                ext = os.path.splitext(item)[1] if os.path.isfile(old_path) else ""
                new_name = gallery_basename(gid, title, web_str) + ext
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


def windows_escape(title):
    return re.sub(r'''[\\/:*?"<>|\t]''', '', title)


# Longest gallery name (without extension) that is still safe to create: a single file name is limited to 255 bytes.
MAX_NAME_BYTES = 240
MAX_FILENAME_BYTES = 255


def truncate_utf8(text, max_bytes):
    """Cut `text` to at most `max_bytes` UTF-8 bytes without splitting a character."""
    return text.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")


def gallery_basename(gid, title, suffix=""):
    """Return '{gid}-{title}{suffix}' with the title cut so the name fits the filesystem limit (UTF-8 bytes)."""
    prefix = f"{gid}-"
    budget = MAX_NAME_BYTES - len(prefix.encode("utf-8")) - len(suffix.encode("utf-8"))
    return prefix + truncate_utf8(windows_escape(title), budget).rstrip() + suffix
