import sys

from bs4 import BeautifulSoup

from .Config import Config
from .common import *


class Checker(Config):
    def __init__(self):
        super().__init__()

    def check_local_gid(self):
        """
        检查本地目录下的重复gid
        Repeat the gid in the local directory
        """
        gid_list = []
        count = 1
        repeat_list = []

        folder = input(f"Please enter the file directory.\n")
        if folder == "":
            print("Cancel")
            sys.exit(1)

        for i in os.listdir(folder):
            if i.find('-') == -1 or os.path.isfile(os.path.join(folder, i)):
                continue

            gid_list.append(int(str(i).split('-')[0]))

        gid_list.sort()

        while count < len(gid_list):
            if gid_list[count - 1] == gid_list[count]:
                repeat_list.append(gid_list[count])
            count += 1

        if len(repeat_list) != 0:
            logger.error(f'Duplicate gid, Please Check: {repeat_list}')
            sys.exit(1)

    def check_eh_setting(self):
        """
        <<<Deprecated Method>>>

        检查 EH 设置
        Check EH settings

        Gallery Name Display >>> Default Title
        Front Page / Search Settings >>> Extended
        """
        logger.info('[Running] Start Checkout EG Setting...')

        hx_res = self.request.get(f'https://{self.base_url}/uconfig.php')
        hx_res_bs = BeautifulSoup(hx_res, 'html.parser')

        gallery_name_display = hx_res_bs.select_one('form #tl_0')
        if gallery_name_display is not None:
            gallery_name_display = gallery_name_display.get('checked')

        front_page = hx_res_bs.select_one('form #dm_2')
        if front_page is not None:
            front_page = front_page.get('checked')

        if gallery_name_display is None or front_page is None:
            logger.error(f"Please checkout https://{self.base_url}/uconfig.php")
            logger.error("Gallery Name Display >>> Default Title")
            logger.error("Front Page / Search Settings >>> Extended")
            sys.exit(1)
        logger.info('[OK] Start checkout EH Setting.')

    def update_local_to_sqlite_status(self, cover=True):
        """
        以本地文件为基准, 重新设置数据库的 status
        Reset the database status based on the local file.
        """

        logger.info(f"update_local_to_sqlite_status({cover})")

        if cover:
            logger.info("该方法会覆盖 fav 的 status 和 a_status 字段")
            logger.info("This method will overwrite the `status` and `a_status` fields of `fav`.")
            logger.info("如果不想覆盖请重新执行: update_local_to_sqlite_status(False)")
            logger.info("If you do not want to overwrite, please re-execute: `update_local_to_sqlite_status(False)`.")

        folder = input(f"Please enter the file directory.\n")
        if folder == "":
            print("Cancel")
            sys.exit(1)

        all_count = 0
        for root, dirs, files in os.walk(folder):
            for file in files:
                all_count += 1

        logger.info(f"There are a total of {all_count} files.")

        enter = input(f"Please press Enter to confirm.\n")

        if enter != "":
            print("Cancel")
            sys.exit(1)

        if cover:
            with sqlite3.connect(self.dbs_name) as co:
                co.execute(f'UPDATE fav SET status=0, a_status=0')
                co.commit()

        with sqlite3.connect(self.dbs_name) as co:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    gid = int(file.split('-')[0])
                    query = co.execute(f'SELECT gid FROM fav WHERE gid={gid}').fetchone()
                    if query is None:
                        logger.warning(f"sqlite no gid:{gid}, file:{file}")
                    else:
                        co.execute(f'UPDATE fav SET status=1, a_status=1 WHERE gid={gid}')
                        co.commit()
