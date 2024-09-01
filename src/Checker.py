import os.path
import sqlite3
import sys
import zipfile

from loguru import logger

from .Config import Config


class Checker(Config):
    def __init__(self):
        super().__init__()

    def check_gid_in_local_zip(self):
        """
        检查本地目录下的重复gid (Only Zip)
        Repeat the gid in the local directory (Only Zip)
        """
        gid_list_original = []
        gid_list_1280x = []

        folder = input(f"Please enter the file directory.\n")
        if folder == "":
            print("Cancel")
            sys.exit(1)

        for i in os.listdir(folder):
            if i.find('-') == -1 or not os.path.isfile(os.path.join(folder, i)):
                continue

            if i.find('-1280x.zip') != -1:
                gid_list_1280x.append(int(str(i).split('-')[0]))
            else:
                gid_list_original.append(int(str(i).split('-')[0]))

        gid_list_1280x.sort()
        gid_list_original.sort()
        logger.info(f'gid_list_1280x count: {len(gid_list_1280x)}')
        logger.info(f'gid_list_original count: {len(gid_list_original)}')

        count = 1
        repeat_list = []
        while count < len(gid_list_original):
            if gid_list_original[count - 1] == gid_list_original[count]:
                repeat_list.append(gid_list_original[count])
            count += 1
        if len(repeat_list) != 0:
            logger.error(f'(gid_list_original) Duplicate gid, Please Check: {repeat_list}')
        else:
            logger.info("(gid_list_original) OK")

        count = 1
        repeat_list = []
        while count < len(gid_list_1280x):
            if gid_list_1280x[count - 1] == gid_list_1280x[count]:
                repeat_list.append(gid_list_1280x[count])
            count += 1
        if len(repeat_list) != 0:
            logger.error(f'(gid_list_1280x) Duplicate gid, Please Check: {repeat_list}')
        else:
            logger.info("(gid_list_1280x) OK")

    def sync_local_to_sqlite_zip(self, cover=False):
        """
        cover: 默认不覆盖, True代表重置 fav_category 表 original_flag 和 web_1280x_flag 字段值, 以本地数据位准
        根据本地文件重新设置 fav_category 的 original_flag 和 web_1280x_flag 字段
        """

        gid_list_original = []
        gid_list_1280x = []

        folder = self.data_path
        # folder = input(f"Please enter the file directory.\n")
        # if folder == "":
        #     print("Cancel")
        #     sys.exit(1)

        for i in os.listdir(folder):
            if i.find('-') == -1 or not os.path.isfile(os.path.join(folder, i)):
                continue

            if i.find('-1280x.zip') != -1:
                gid_list_1280x.append(int(str(i).split('-')[0]))
            else:
                gid_list_original.append(int(str(i).split('-')[0]))

        gid_list_1280x.sort()
        gid_list_original.sort()
        logger.info(f'gid_list_1280x count: {len(gid_list_1280x)}')
        logger.info(f'gid_list_original count: {len(gid_list_original)}')

        # enter = input(f"Please press Enter to confirm.\n")
        #
        # if enter != "":
        #     print("Cancel")
        #     sys.exit(1)

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
        """
        检测到压缩包损坏
        """
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
