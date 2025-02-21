import asyncio
import copy
import os
import re
import sqlite3
import ssl
import sys
import zipfile

import aiohttp
import yaml
from PIL import Image
from bs4 import BeautifulSoup
from loguru import logger
from tqdm.asyncio import tqdm_asyncio

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

                self.gallery_path = os.path.join(data_path, 'gallery')
                self.web_path = os.path.join(data_path, 'web')
                self.archive_path = os.path.join(data_path, 'archive')
                self.del_path = os.path.join(data_path, 'del')
                self.duplicate_del_path = os.path.join(data_path, 'duplicate_del')

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
                }
                if 'sk' in config['cookies']:
                    eh_cookies['sk'] = str(config['cookies']['sk'])
                if 'hath_perks' in config['cookies']:
                    eh_cookies['hath_perks'] = str(config['cookies']['hath_perks'])
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

                # Watch
                watch_fav_ids = str(config['watch_fav_ids']) if config['watch_fav_ids'] else None
                watch_download_fav_ids = str(config['watch_download_fav_ids']) if config['watch_download_fav_ids'] else None
                self.watch_fav_ids = watch_fav_ids
                self.watch_download_fav_ids = watch_download_fav_ids
                watch_lan_status = bool(config['watch_lan_status'])
                self.watch_lan_status = watch_lan_status
                watch_archive_status = bool(config['watch_archive_status'])
                self.watch_archive_status = watch_archive_status

        except FileNotFoundError as e:
            logger.error('File config.yaml not found')
            logger.error(e)
            sys.exit(1)
        except Exception as e:
            logger.error(e)
            sys.exit(1)

    async def fetch_data(self, url, json=None, data=None, tqdm_file_path=None, retry_delay=5, retry_attempts=5):
        """
        Return: True | False | "reload_image"
        """
        try:
            async with aiohttp.ClientSession(headers=self.request_headers, cookies=self.eh_cookies,
                                             connector=aiohttp.TCPConnector(ssl_context=ssl_context),
                                             timeout=aiohttp.ClientTimeout(connect=30)) as session:
                # Convert speed limit from 10KB/s to bytes per second
                # speed_limit_bps = 10 * 1024
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
                    has_inline_set = True if 'inline_set' in url else False
                    if has_inline_set:
                        # 此处似乎需要先访问一次获取完整 Cookies的sk值，否则无法固定设置配置项
                        # Task:可以通过将sk值填入yaml配置以避免此重复，但是sk其有效期是否足够长呢，其值是否需要频繁更新呢
                        if not self.eh_cookies['sk']:
                            async with session.get(url, proxy=self.proxy_url if self.proxy_status else None) as response:
                                await self.check_fetch_err(response, url)
                            # 考虑到上面存在的一次重复请求，添加一个延迟以降低请求频率
                            await asyncio.sleep(1)
                        async with session.get(url, proxy=self.proxy_url if self.proxy_status else None) as response:
                            await self.check_fetch_err(response, url)
                            return await response.read()
                    else:
                        async with session.get(url, proxy=self.proxy_url if self.proxy_status else None) as response:
                            await self.check_fetch_err(response, url)
                            if tqdm_file_path is not None:
                                total_size = int(response.headers.get('Content-Length', 0))
                                desc_name = url.split('/')[-1] + "/" + os.path.basename(tqdm_file_path)
                                temp_file_path = os.path.dirname(tqdm_file_path) + "/temp_" + os.path.basename(
                                    tqdm_file_path)
                                with open(temp_file_path, 'wb') as f:
                                    with tqdm_asyncio(total=total_size, unit='B', unit_scale=True, desc=desc_name) as pbar:
                                        # bytes_written = 0
                                        async for chunk in response.content.iter_chunked(1024):
                                            f.write(chunk)
                                            # bytes_written += len(chunk)
                                            # # Calculate the time to sleep to maintain the desired speed limit
                                            # if bytes_written >= speed_limit_bps:
                                            #     sleep_time = len(chunk) / speed_limit_bps
                                            #     await asyncio.sleep(sleep_time)
                                            pbar.update(len(chunk))
                                if os.path.exists(tqdm_file_path):
                                    os.remove(tqdm_file_path)
                                # Verify Img
                                if os.path.exists(temp_file_path):
                                    # if tqdm_file_path.endswith(".webp"):
                                    try:
                                        webp_image = Image.open(temp_file_path)
                                        webp_image.verify()
                                        webp_image.close()
                                    except Exception as e:
                                        os.remove(temp_file_path)
                                        logger.error(f"Failed to process image: {temp_file_path}. Error: {e}")
                                        return "reload_image"
                                os.rename(temp_file_path, tqdm_file_path)
                                return True
                            return await response.read()
        except Exception as e:
            logger.error(e)
            if retry_attempts > 0:
                if "hath.network" in str(url):
                    return "reload_image"
                logger.warning(
                    f"Failed to retrieve data. Retrying in {retry_delay} seconds, {retry_attempts - 1} attempts remaining. {url}")
                await asyncio.sleep(retry_delay)
                return await self.fetch_data(url=url, json=json, data=data, tqdm_file_path=tqdm_file_path,
                                             retry_delay=retry_delay,
                                             retry_attempts=retry_attempts - 1)
            else:
                while True:
                    # 等待1~2小时即可恢复
                    logger.warning("The request limit has been exceeded. Waiting 2 hour...")
                    await asyncio.sleep(2 * 60 * 60)
                    if "hath.network" in str(url):
                        return "reload_image"
                    logger.warning(
                        f"Failed to retrieve data. Retrying in {retry_delay} seconds, {retry_attempts - 1} attempts remaining. {url}")
                    await asyncio.sleep(retry_delay)
                    return await self.fetch_data(url=url, json=json, data=data, tqdm_file_path=tqdm_file_path, retry_delay=retry_delay, retry_attempts=2)

    async def fetch_data_stream(self, url, file_path, stream_range=0, retry_delay=10, retry_attempts=10):
        try:
            headers = copy.deepcopy(self.request_headers)
            mode = 'wb'
            if stream_range != 0:
                headers.update({'Range': f'bytes={stream_range}-'})
                mode = 'ab'
            async with aiohttp.ClientSession(headers=headers, cookies=self.eh_cookies,
                                             connector=aiohttp.TCPConnector(ssl_context=ssl_context)) as session:
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
                return True
        except BaseException as e:
            logger.error(e)
            if retry_attempts > 0:
                file_size = 0
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
                logger.error(f"The request limit has been exceeded. Program terminated.")
                sys.exit(1)

    async def check_fetch_err(self, response, msg):
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text' in content_type or 'json' in content_type or 'html' in content_type:
            try:
                content = await response.text()
            except Exception as e:
                content = await response.text(errors='replace')
                if '�' in content:
                    logger.warning("Some characters were replaced.")
            if "IP quota exhausted" in content:
                logger.warning("IP quota exhausted. wait 360 seconds and try again.")
                await asyncio.sleep(360)
                raise Exception("IP quota exhausted")
            elif "This IP address has been temporarily banned due to an excessive request rate" in content:
                hours_match = re.search(r'(\d+) hours?', content)
                minutes_match = re.search(r'(\d+) minutes?', content)
                seconds_match = re.search(r'(\d+) seconds?', content)
                hours = int(hours_match.group(1)) if hours_match else 0
                minutes = int(minutes_match.group(1)) if minutes_match else 0
                seconds = int(seconds_match.group(1)) if seconds_match else 0
                total_seconds = hours * 60 * 60 + minutes * 60 + seconds + 10
                logger.warning(
                    f"This IP address has been temporarily banned due to an excessive request rate. Wait {total_seconds} Seconds")
                await asyncio.sleep(total_seconds)
                raise Exception("This IP address has been temporarily banned due to an excessive request rate")
            elif "You have clocked too many downloaded bytes on this gallery" in content:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                target_text = re.compile(r'You have clocked too many downloaded bytes on this gallery')
                for text_node in soup.find_all(string=target_text):
                    is_comment = text_node.find_parent(class_='c6')
                    if not is_comment:
                        logger.warning("You have clocked too many downloaded bytes on this gallery.")
                        logger.warning("Please open Gallery---Archive Download---Cancel")
                        logger.warning(msg)
                        raise Exception("You have clocked too many downloaded bytes on this gallery")
            elif "Your IP address has been temporarily banned for excessive pageloads" in content:
                logger.warning(content)
                await asyncio.sleep(12 * 60 * 60)
                raise Exception("Your IP address has been temporarily banned for excessive pageloads")
            # elif response.status != 200:
            #     logger.warning(f"code: {response.status}")
            #     logger.warning(f'{content}: {msg}')

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

            co.execute('''
                CREATE TABLE IF NOT EXISTS tag_list (
                    "tid" INTEGER PRIMARY KEY AUTOINCREMENT,
                    "tag" TEXT UNIQUE NOT NULL,
                    "translated_tag" TEXT
                )
            ''')
            co.execute('''
                CREATE TABLE IF NOT EXISTS gid_tid (
                    "gid" INTEGER UNSIGNED NOT NULL,
                    "tid" INTEGER UNSIGNED NOT NULL,
                    PRIMARY KEY (gid, tid),
                    UNIQUE(gid, tid)
                )
            ''')
            co.execute('''
                CREATE TABLE IF NOT EXISTS watch_record (
                    "id" INTEGER PRIMARY KEY NOT NULL,
                    "last_check_time" TEXT
                )
            ''')

            co.commit()

    async def get_image_limits(self):
        hx_res = await self.fetch_data(url="https://e-hentai.org/home.php")
        response = BeautifulSoup(hx_res, 'html.parser')
        limits_arr = response.select('div.homebox p strong')
        image_limits = int(limits_arr[0].text.strip().replace(",", ""))
        total_limits = int(limits_arr[1].text.strip().replace(",", ""))
        return image_limits, total_limits

    async def wait_image_limits(self):
        """
        total_limits * 30% = lower_value < image_limits < total_limits * 80%
        """
        while True:
            image_limits, total_limits = await self.get_image_limits()
            logger.info(f"Image Limits: {image_limits} / ({total_limits}*0.8 = {total_limits * 0.8})")
            if image_limits > total_limits * 0.8:
                lower_value = total_limits * 0.3
                # 每分钟回复12个, 每个需要 5s, 这里额外 +1s 并且总时长 +60s 增加容错
                # Reply to 12 messages per minute, with each reply taking
                # 5 seconds. Add an extra 1 second for each reply and increase the total duration by 60 seconds to
                # allow for error tolerance.
                wait_time = (image_limits - lower_value) * 6
                wait_time += 60
                logger.warning(f"The IP quota has been exceeded. Please try again in {wait_time} Second.")
                await asyncio.sleep(wait_time)
            else:
                return image_limits, total_limits
