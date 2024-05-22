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

        logger.info('[Running] Start Check Local Gid...')
        for i in os.listdir(self.data_path):
            if i.find('-') == -1 or os.path.isfile(os.path.join(self.data_path, i)):
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

        logger.info('[OK] Start Check Local Gid...')

    def get_local_data_add(self):
        """
        同步本地数据到数据库(add gid & NAME)
        Upload local data to the database
        """

        logger.info('[Running] ...')

        downloads_dirname_list = []
        for i in os.listdir(self.data_path):
            gid = int(str(i).split('-')[0])
            downloads_dirname_list.append((gid, i))

        with sqlite3.connect(self.dbs_name) as co:
            try:
                co.execute('DELETE FROM DOWNLOAD_DIRNAME')
                co.executemany(
                    'INSERT OR REPLACE INTO DOWNLOAD_DIRNAME(gid, DIRNAME) VALUES (?, ?)',
                    downloads_dirname_list)

                co.commit()

                logger.info(f'Successfully added {len(downloads_dirname_list)} pieces of'
                            f' data data in DOWNLOAD_DIRNAME')
            except sqlite3.Error as e:
                logger.error(f'SQLite error occurred: {e}')
            except Exception as e:
                logger.error(f'Unexpected error occurred: {e}')

        logger.info('[OK] Delete DOWNLOAD_DIRNAME Table...')

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
