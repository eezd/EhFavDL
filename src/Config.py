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

        request = httpx.Client(headers=headers, proxies=proxy_list, cookies=httpx_cookies)

        self.dbs_name = dbs_name
        self.base_url = base_url
        self.request = request
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
                "A_STATE" INTEGER NOT NULL DEFAULT 0 /*Archive状态, 0默认 1已下载*/,
                "TAGS" TEXT /*标签*/
            )''')

            co.execute('''
            CREATE TABLE IF NOT EXISTS "CATEGORY" (
              "ID" INTEGER PRIMARY KEY NOT NULL,
              "NAME" TEXT NOT NULL
            )''')

            co.commit()
