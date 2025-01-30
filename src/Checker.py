import os.path

from src.Utils import *


class Checker(Config):
    def __init__(self):
        super().__init__()

    def check_gid_in_local_cbz(self, target_path=""):
        """
        移动目录下的重复 gid 的 CBZ 文件到 duplicate_del 文件夹
        Move CBZ files with duplicate GIDs in the directory to the `duplicate_del` folder.
        """
        gid_list_original = []
        gid_list_1280x = []

        if target_path == "":
            target_path = self.gallery_path

        for i in os.listdir(target_path):
            if not re.match(r'^\d+-.*\.cbz', i):
                continue
            if i.find('-1280x') != -1:
                gid_list_1280x.append(i)
            else:
                gid_list_original.append(i)

        gid_list_1280x.sort()
        gid_list_original.sort()

        count = 1
        while count < len(gid_list_original):
            g1 = re.match(r'^(\d+)-', gid_list_original[count - 1]).group(1)
            g2 = re.match(r'^(\d+)-', gid_list_original[count]).group(1)
            if g1 == g2:
                os.makedirs(self.duplicate_del_path, exist_ok=True)
                front_name = gid_list_original[count - 1]
                back_name = gid_list_original[count]
                if len(front_name) > len(back_name):
                    old_path = os.path.join(target_path, front_name)
                    new_path = os.path.join(self.duplicate_del_path, front_name)
                else:
                    old_path = os.path.join(target_path, back_name)
                    new_path = os.path.join(self.duplicate_del_path, back_name)
                logger.warning(f'(gid_list_original) Duplicate gid, Move: {old_path} -> {new_path}')
                shutil.move(old_path, new_path)
            count += 1

        count = 1
        while count < len(gid_list_1280x):
            g1 = re.match(r'^(\d+)-', gid_list_1280x[count - 1]).group(1)
            g2 = re.match(r'^(\d+)-', gid_list_1280x[count]).group(1)
            if g1 == g2:
                os.makedirs(self.duplicate_del_path, exist_ok=True)
                front_name = gid_list_1280x[count - 1]
                back_name = gid_list_1280x[count]
                if len(front_name) > len(back_name):
                    old_path = os.path.join(target_path, front_name)
                    new_path = os.path.join(self.duplicate_del_path, front_name)
                else:
                    old_path = os.path.join(target_path, back_name)
                    new_path = os.path.join(self.duplicate_del_path, back_name)
                logger.warning(f'(gid_list_1280x) Duplicate gid, Move: {old_path} -> {new_path}')
                shutil.move(old_path, new_path)
            count += 1
        gid_list_1280x = []
        gid_list_original = []
        for i in os.listdir(target_path):
            if not re.match(r'^\d+-.*\.cbz', i):
                continue
            if i.find('-1280x') != -1:
                gid_list_1280x.append(i)
            else:
                gid_list_original.append(i)
        logger.info(f'gid_list_1280x count: {len(gid_list_1280x)}')
        logger.info(f'gid_list_original count: {len(gid_list_original)}')

    def sync_local_to_sqlite_cbz(self, cover=False, target_path=""):
        """
        cover=True 重置 fav_category 表 original_flag 和 web_1280x_flag 字段值, 根据本地文件重新设置
        If `cover=True`, reset the `original_flag` and `web_1280x_flag` fields in the `fav_category` table,
         and then reconfigure them based on the local files.
        """
        gid_list_original = []
        gid_list_1280x = []
        if target_path == "":
            target_path = self.gallery_path
        for i in os.listdir(target_path):
            if not re.match(r'^\d+-.*\.cbz', i):
                continue
            if i.find('-1280x') != -1:
                gid_list_1280x.append(re.match(r'^(\d+)-', i).group(1))
            else:
                gid_list_original.append(re.match(r'^(\d+)-', i).group(1))
        gid_list_1280x.sort()
        gid_list_original.sort()
        logger.info(f'gid_list_1280x count: {len(gid_list_1280x)}')
        logger.info(f'gid_list_original count: {len(gid_list_original)}')
        if cover:
            with sqlite3.connect(self.dbs_name) as co:
                co.execute(f'UPDATE fav_category SET original_flag=0, web_1280x_flag=0')
                co.commit()
        with sqlite3.connect(self.dbs_name) as co:
            for data in gid_list_1280x:
                co.execute(f'UPDATE fav_category SET web_1280x_flag=1 WHERE gid = ?', (data,))
                co.commit()
            for data2 in gid_list_original:
                co.execute(f'UPDATE fav_category SET original_flag=1 WHERE gid = ?', (data2,))
                co.commit()
            web_len = co.execute('SELECT count(*) FROM fav_category WHERE web_1280x_flag = 1').fetchone()[0]
            original_len = co.execute('SELECT count(*) FROM fav_category WHERE original_flag = 1').fetchone()[0]
            logger.info(f'Finish sync local to sqlite. web_1280x_flag: {web_len}, original_flag: {original_len}')
            logger.info(f'Finish sync local to sqlite.')

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
                    except OSError as e:
                        logger.error(f"检测到压缩包损坏, 请删除文件: {file_path}")
                        logger.error(f"Detected a corrupted archive. Please delete the file.: {file_path}")
                        status = 1
        if status == 1:
            sys.exit(1)
        return loc_gid
