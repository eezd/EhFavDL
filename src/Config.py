import sys

import httpx
import yaml

from .common import *


class Config:
    def __init__(self):
        try:
            with open('./config.yaml', 'r', encoding='UTF-8') as file:
                config = yaml.load(file, Loader=yaml.FullLoader)

                base_url = str(config['website'])

                work_path = str(config['work_path'])
                data_path = str(config['data_path'])
                dbs_name = str(config['dbs_name'])
                connect_limit = str(config['connect_limit'])
                lan_url = str(config['lan_url'])
                lan_api_psw = str(config['lan_api_psw'])

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
        # try:
        #     hx = httpx.Client(headers=headers, proxies=proxy_list, cookies=httpx_cookies)
        #     logger.info(f'[Running] Start testing Httpx to {test_url} network connection')
        #     r = hx.get(test_url, timeout=10, follow_redirects=True)
        #     res = BeautifulSoup(r, 'html.parser')
        #
        #     # 判断页面正常显示
        #     # Judging that the page is normal
        #     if len(res.get_text()) < 300 & len(res.get_text()) > 20:
        #         logger.error(res.get_text())
        #         sys.exit(1)
        #     elif len(res.get_text()) < 19:
        #         logger.error('Please check cookies')
        #         sys.exit(1)
        #
        #     logger.info(f'[OK] Start testing Httpx to {test_url} network connection')
        # except Exception as e:
        #     logger.error(e)
        #     sys.exit(1)

        self.dbs_name = dbs_name
        self.base_url = base_url
        self.request = httpx.Client(headers=headers, proxies=proxy_list, cookies=httpx_cookies)
        self.work_path = work_path
        self.data_path = data_path
        self.connect_limit = connect_limit
        self.lan_url = lan_url
        self.lan_api_psw = lan_api_psw

    def create_database(self):
        """
        创建数据库
        create database
        """
        with sqlite3.connect(self.dbs_name) as co:
            co.execute('''
            CREATE TABLE IF NOT EXISTS "fav" (
                "gid" INTEGER PRIMARY KEY NOT NULL,
                "token" TEXT,
                "title" TEXT,
                "title_jpn" TEXT,
                "category" TEXT /*分类*/,
                "thumb" TEXT /*封面 URL*/,
                "uploader" TEXT /*上传者*/,
                "posted" TEXT /*发布时间*/,
                "pages" INTEGER /*页数*/,
                "rating" TEXT /*评分*/,
                "ban" INTEGER NOT NULL DEFAULT 0/*版权*/,
                "status" INTEGER NOT NULL DEFAULT 0 /*状态, 0默认 1已下载*/,
                "a_status" INTEGER NOT NULL DEFAULT 0 /*Archive状态, 0默认 1已下载*/,
                "tags" TEXT /*标签*/
            )''')

            co.execute('''
            CREATE TABLE IF NOT EXISTS "fav_name" (
              "fav_id" INTEGER PRIMARY KEY NOT NULL,
              "fav_name" TEXT NOT NULL
            )''')

            co.execute('''
            CREATE TABLE IF NOT EXISTS "fav_category" (
              "gid" INTEGER PRIMARY KEY NOT NULL,
              "fav_id" INT NOT NULL /*收藏夹*/
            )''')

            co.commit()

            try:
                co.execute("ALTER TABLE fav ADD COLUMN a_status INTEGER NOT NULL DEFAULT 0;")
                co.commit()
            except Exception as e:
                if str(e).find("duplicate column name") != -1:
                    pass
                else:
                    raise
