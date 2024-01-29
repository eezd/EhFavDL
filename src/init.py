import httpx
from bs4 import BeautifulSoup
import os
import yaml
import sys
from loguru import logger
import sqlite3


class Init:
    """
    读取 config.yaml, 测试网络环境.
    Read config.yaml, test network environment.
    创建数据库, 检查本地文件重复GID, 录入本地文件名到数据库
    Create a database, check for duplicate GIDs in local files,
    and enter local file names into the database

    self.dbs_name   # database file name
    self.base_url   # website
    self.hx = hx    # httpx
    self.work_path
    self.data_path
    self.connect_limit
    """

    def __init__(self, dbs_name):
        logger.info('[Loading]Start read config.yaml...')
        try:
            with open('./config.yaml', 'r', encoding='UTF-8') as file:
                config = yaml.load(file, Loader=yaml.FullLoader)

                base_url = str(config['website'])
                test_url = f"https://{base_url}"

                work_path = str(config['work_path'])
                data_path = str(config['data_path'])
                connect_limit = str(config['connect_limit'])

                httpx_cookies = {
                    "ipb_member_id": str(config['cookies']['ipb_member_id']),
                    "ipb_pass_hash": str(config['cookies']['ipb_pass_hash']),
                    "igneous": str(config['cookies']['igneous'])
                }

                proxy_status = config['proxy']['enable']
                proxy_url = config['proxy']['url']
                proxy_list = {
                    'http://': proxy_url,
                    'https://': proxy_url,
                }

                headers = {
                    "User-Agent": config['User-Agent'],
                }

        except FileNotFoundError:
            logger.error('File config.yaml not found')
            sys.exit(1)
        except Exception as e:
            logger.error(e)
            sys.exit(1)

        if not proxy_status:
            proxy_list = {}

        # 测试 Httpx 网络环境.
        # Test Httpx network environment.
        try:
            hx = httpx.Client(headers=headers, proxies=proxy_list, cookies=httpx_cookies)
            logger.info(f'[Loading] Start testing Httpx to {test_url} network connection')
            r = hx.get(test_url, timeout=10, follow_redirects=True)
            res = BeautifulSoup(r, 'html.parser')

            # 判断页面正常显示
            # Judging that the page is normal
            if len(res.get_text()) < 300 & len(res.get_text()) > 20:
                logger.error(res.get_text())
                sys.exit(1)
            elif len(res.get_text()) < 19:
                logger.error('Please check cookies')
                sys.exit(1)

            logger.info(f'[OK] Start testing Httpx to {test_url} network connection')
        except Exception as e:
            logger.error(e)
            sys.exit(1)

        self.dbs_name = dbs_name
        self.base_url = base_url
        self.hx = hx
        self.work_path = work_path
        self.data_path = data_path
        self.connect_limit = connect_limit

        logger.info('[OK] Start read config.yaml...')

    @logger.catch()
    def create_database(self):
        """
        创建数据库
        create database
        """
        try:
            logger.info('[Loading] Start Create data.db...')
            with sqlite3.connect(self.dbs_name) as co:
                co.execute('''
                CREATE TABLE IF NOT EXISTS "FAV" (
                    "GID" INTEGER PRIMARY KEY NOT NULL,
                    "TOKEN" TEXT,
                    "TITLE" TEXT,
                    "TITLE_JPN" TEXT,
                    "CATEGORY" TEXT /*分类*/,
                    "THUMB" TEXT /*封面 URL*/,
                    "UPLOADER" TEXT /*上传者*/,
                    "POSTED" TEXT /*发布时间*/,
                    "PAGES" INTEGER /*页数*/,
                    "RATING" TEXT /*评分*/,
                    "FAVORITE" INT NOT NULL /*收藏夹*/,
                    "BAN" INTEGER NOT NULL DEFAULT 0/*版权*/,
                    "STATE" INTEGER NOT NULL DEFAULT 0 /*状态, 0默认 1已下载*/,
                    "TAGS" TEXT /*标签*/
                )''')

                co.execute('''
                CREATE TABLE IF NOT EXISTS "CATEGORY" (
                  "ID" INTEGER PRIMARY KEY NOT NULL,
                  "NAME" TEXT NOT NULL
                )''')

                co.commit()
        except sqlite3.Error as e:
            logger.error(f'SQLite error occurred: {e}')
            sys.exit(1)
        except Exception as e:
            logger.error(f'Unexpected error occurred: {e}')
            sys.exit(1)
        else:
            logger.info('[OK] Start Create data.db...')

    @logger.catch()
    def check_eh_setting(self):
        """
        检查 EH 设置
        Check EH settings
        """

        logger.info('[Loading] Start Checkout EG Setting...')

        hx_res = self.hx.get(f'https://{self.base_url}/uconfig.php')
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
        logger.info('[OK] Start checkout EH Setting...')

    @logger.catch()
    def check_local_gid(self):
        """
        检查本地目录下的重复GID
        Repeat the GID in the local directory
        """
        gid_list = []
        count = 1
        repeat_list = []

        logger.info('[Loading] Start Check Local Gid...')
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
            logger.error(f'Duplicate GID, Please Check: {repeat_list}')
            sys.exit(1)

        logger.info('[OK] Start Check Local Gid...')

    @logger.catch()
    def update_local_data(self):
        """
        同步本地数据到数据库(add GID & NAME)
        Upload local data to the database
        """

        logger.info('[Loading] ...')

        downloads_dirname_list = []
        for i in os.listdir(self.data_path):
            gid = int(str(i).split('-')[0])
            downloads_dirname_list.append((gid, i))

        with sqlite3.connect(self.dbs_name) as co:
            try:
                co.execute('DELETE FROM DOWNLOAD_DIRNAME')
                co.executemany(
                    'INSERT OR REPLACE INTO DOWNLOAD_DIRNAME(GID, DIRNAME) VALUES (?, ?)',
                    downloads_dirname_list)

                co.commit()

                logger.info(f'Successfully added {len(downloads_dirname_list)} pieces of'
                            f' data data in DOWNLOAD_DIRNAME')
            except sqlite3.Error as e:
                logger.error(f'SQLite error occurred: {e}')
            except Exception as e:
                logger.error(f'Unexpected error occurred: {e}')

        logger.info('[OK] Delete DOWNLOAD_DIRNAME Table...')

    def apply(self):
        self.create_database()

        os.makedirs(self.data_path, exist_ok=True)

        self.check_local_gid()

        # self.check_eh_setting()

        # self.update_local_data()
