import asyncio
import copy
import os
import sqlite3
import ssl
import sys
import zipfile

import aiohttp
import yaml
from bs4 import BeautifulSoup
from loguru import logger
from tqdm.asyncio import tqdm_asyncio

# ssl:default [[SSL: DH_KEY_TOO_SMALL] dh key too small (_ssl.c:1006)]
ssl_context = ssl.create_default_context()
ssl_context.set_ciphers('HIGH:!DH:!aNULL')


class Config:
    def __init__(self):
        try:
            with open('./config.yaml', 'r', encoding='UTF-8') as file:
                config = yaml.load(file, Loader=yaml.FullLoader)

                base_url = str(config['website'])
                self.base_url = base_url

                data_path = str(config['data_path'])
                self.data_path = data_path

                dbs_name = str(config['dbs_name'])
                self.dbs_name = dbs_name

                tags_translation = bool(config['tags_translation'])
                self.tags_translation = tags_translation

                connect_limit = str(config['connect_limit'])
                self.connect_limit = connect_limit

                lan_url = str(config['lan_url'])
                self.lan_url = lan_url

                lan_api_psw = str(config['lan_api_psw'])
                self.lan_api_psw = lan_api_psw

                eh_cookies = {
                    "ipb_member_id": str(config['cookies']['ipb_member_id']),
                    "ipb_pass_hash": str(config['cookies']['ipb_pass_hash']),
                    "igneous": str(config['cookies']['igneous']),
                    "sk": str(config['cookies']['sk']),
                    "hath_perks": str(config['cookies']['hath_perks']),
                }
                self.eh_cookies = eh_cookies

                proxy_status = bool(config['proxy']['enable'])
                self.proxy_status = proxy_status

                proxy_url = config['proxy']['url']
                self.proxy_url = proxy_url

                proxy_list = {
                    'http://': proxy_url,
                    'https://': proxy_url,
                }
                self.proxy_list = proxy_list

                headers = {
                    "User-Agent": config['User-Agent'],
                }
                self.request_headers = headers

        except FileNotFoundError:
            logger.error('File config.yaml not found')
            sys.exit(1)
        except Exception as e:
            logger.error(e)
            sys.exit(1)

    @logger.catch()
    async def fetch_data(self, url, data=None, json=None, retry_delay=5, retry_attempts=10):
        async with aiohttp.ClientSession(headers=self.request_headers, cookies=self.eh_cookies,
                                         connector=aiohttp.TCPConnector(ssl_context=ssl_context)) as session:
            try:
                if data is not None:
                    async with session.post(url, data=data,
                                            proxy=self.proxy_url if self.proxy_status else None) as response:
                        await self.check_fetch_err(response, url)
                        return await response.read()

                elif json is not None:
                    async with session.post(url, json=json,
                                            proxy=self.proxy_url if self.proxy_status else None) as response:
                        await self.check_fetch_err(response, url)
                        return await response.json(content_type=None)

                else:
                    async with session.get(url, proxy=self.proxy_url if self.proxy_status else None) as response:
                        await self.check_fetch_err(response, url)
                        return await response.read()
            except Exception as e:
                logger.error(e)
                if retry_attempts > 0:
                    logger.warning(
                        f"Failed to retrieve data. Retrying in {retry_delay} seconds, {retry_attempts - 1} attempts remaining.")
                    await asyncio.sleep(retry_delay)
                    return await self.fetch_data(url=url, data=data, json=json, retry_delay=retry_delay,
                                                 retry_attempts=retry_attempts - 1)
                else:
                    logger.warning(f"The request limit has been exceeded. Program terminated.")
                    sys.exit(1)

    @logger.catch()
    async def fetch_data_stream(self, url, file_path, stream_range=0, retry_delay=10, retry_attempts=5):
        headers = copy.deepcopy(self.request_headers)
        mode = 'wb'
        if stream_range != 0:
            headers.update({'Range': f'bytes={stream_range}-'})
            mode = 'ab'
        async with aiohttp.ClientSession(headers=headers, cookies=self.eh_cookies,
                                         connector=aiohttp.TCPConnector(ssl_context=ssl_context)) as session:
            try:
                async with session.get(url, proxy=self.proxy_url if self.proxy_status else None) as response:
                    await self.check_fetch_err(response, file_path)
                    with tqdm_asyncio(total=int(response.headers.get("Content-Length", 0)) + stream_range,
                                      initial=stream_range,
                                      unit="B", unit_scale=True) as progress_bar:
                        folder_path = os.path.dirname(file_path)
                        os.makedirs(folder_path, exist_ok=True)
                        with open(file_path, mode) as f:
                            async for data in response.content.iter_chunked(1024):
                                f.write(data)
                                progress_bar.update(len(data))
            except BaseException as e:
                # logger.error(e)
                if retry_attempts > 0:
                    logger.warning(
                        f"Failed to fetch data. Retrying in {retry_delay} seconds, {retry_attempts - 1} attempts left")
                    if os.path.exists(file_path) and str(file_path).find(".zip"):
                        try:
                            with zipfile.ZipFile(file_path, 'r') as zip_file:
                                zip_file.testzip()
                            logger.warning(f"The file already exists, skipping: {os.path.basename(file_path)}")
                            return True
                        except (zipfile.BadZipFile, OSError):
                            logger.warning(f"开始断点续传 / Start resumable download.: {os.path.basename(file_path)}")
                            file_size = os.path.getsize(file_path)
                    await asyncio.sleep(retry_delay)
                    return await self.fetch_data_stream(url=url, file_path=file_path, stream_range=file_size,
                                                        retry_delay=retry_delay, retry_attempts=retry_attempts - 1)
                else:
                    logger.warning(f"The request limit has been exceeded. Program terminated.")
                    sys.exit(1)

    async def check_fetch_err(self, response, msg):
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text' in content_type or 'json' in content_type or 'html' in content_type:
            content = await response.text()
            if "IP quota exhausted" in content:
                logger.warning("IP quota exhausted.")
                raise Exception("IP quota exhausted")
            elif "You have clocked too many downloaded bytes on this gallery" in content:
                logger.warning("You have clocked too many downloaded bytes on this gallery.")
                logger.warning("Please open Gallery---Archive Download---Cancel")
                logger.warning(msg)
                raise Exception("You have clocked too many downloaded bytes on this gallery")
            elif "Your IP address has been temporarily banned for excessive pageloads" in content:
                logger.warning(content)
                await asyncio.sleep(12 * 60 * 60)
                raise Exception("Your IP address has been temporarily banned for excessive pageloads")
            elif response.status != 200:
                logger.warning(f"code: {response.status_code}")
                logger.warning(f'{content}: {msg}')

    def create_database(self):
        with sqlite3.connect(self.dbs_name) as co:
            co.execute('''
            CREATE TABLE IF NOT EXISTS "eh_data" (
                "gid" INTEGER PRIMARY KEY NOT NULL,
                "token" TEXT NOT NULL,
                "title" TEXT,
                "title_jpn" TEXT,
                "category" TEXT /*分类*/,
                "thumb" TEXT /*封面 URL*/,
                "uploader" TEXT /*上传者*/,
                "posted" TEXT /*发布时间*/,
                "filecount" INTEGER /*页数*/,
                "filesize" INTEGER /*大小*/,
                "expunged" INTEGER NOT NULL DEFAULT 0 /*是否被隐藏*/,
                "copyright_flag" INTEGER NOT NULL DEFAULT 0 /*是否被版权*/,
                "rating" TEXT /*评分*/,
                "current_gid" INTEGER /*画廊最新gid*/,
                "current_token" TEXT /*画廊最新token*/
            )''')

            co.execute('''
            CREATE TABLE IF NOT EXISTS "fav_name" (
              "fav_id" INTEGER PRIMARY KEY NOT NULL,
              "fav_name" TEXT NOT NULL
            )''')

            co.execute('''
            CREATE TABLE IF NOT EXISTS "fav_category" (
              "gid" INTEGER PRIMARY KEY NOT NULL,
              "token" TEXT NOT NULL,
              "fav_id" INTEGER NOT NULL,
              "del_flag" INTEGER NOT NULL DEFAULT 0 /* 是否已被移除收藏夹 */,
              "original_flag" INTEGER NOT NULL DEFAULT 0 /* 1表示 通过archiver中original选择下载原图*/,
              "web_1280x_flag" INTEGER NOT NULL DEFAULT 0 /* 1表示 通过网页画廊下载/通过archiver中Resample选项下载*/
            )''')

            # 使用单独的标签列表和映射表相比字符串存储或许能实现更好的数据统计和管理
            co.execute('''
                CREATE TABLE IF NOT EXISTS tag_list (
                    tid INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag TEXT UNIQUE NOT NULL,
                    translated_tag TEXT
                )
            ''')
            co.execute('''
                CREATE TABLE IF NOT EXISTS gid_tid (
                    gid INTEGER UNSIGNED NOT NULL,
                    tid INTEGER UNSIGNED NOT NULL,
                    PRIMARY KEY (gid, tid),
                    UNIQUE(gid, tid)
                )
            ''')

            co.commit()

    async def get_image_limits(self):
        hx_res = await self.fetch_data(url="https://e-hentai.org/home.php")
        response = BeautifulSoup(hx_res, 'html.parser')
        image_limits = response.find_all('div', class_='homebox')[0].find('p').find_all('strong')[0].text.strip()
        total_limits = response.find_all('div', class_='homebox')[0].find('p').find_all('strong')[1].text.strip()
        return image_limits, total_limits
