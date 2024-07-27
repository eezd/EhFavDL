import asyncio
import os
import shutil
import sqlite3
import sys

from bs4 import BeautifulSoup
from loguru import logger
from tqdm.asyncio import tqdm_asyncio

from .Config import Config
from .common import *

# 下载路径为: data_path + "web"
folder = "web"


class DownloadWebGallery(Config):

    def __init__(self, gid, token, title):
        super().__init__()

        self.gid = gid
        self.token = token

        # 格式化不合法的命名
        # invalid format name
        self.title = windows_escape(title)

        # 临时路径 (当前是文件夹形式)
        self.filepath_tmp = os.path.join(self.data_path, folder, 'temp', str(self.gid) + '-' + self.title + "-1280x")
        # 最终路径
        self.filepath_end = os.path.join(self.data_path, folder, str(self.gid) + '-' + self.title + "-1280x")

        self.long_url = f"https://{self.base_url}/g/{self.gid}/{self.token}/"

    @logger.catch()
    async def download_image(self, semaphore, url, file_path):
        async with semaphore:
            real_url = await self.fetch_data(url=url)
            real_url = BeautifulSoup(real_url, 'html.parser')
            real_url = real_url.select_one('img#img').get('src')
            if real_url == "https://exhentai.org/img/509.gif":
                logger.warning("509:YOU HAVE TEMPORARILY REACHED THE LIMIT")
                if self.get_image_limits() == False:
                        logger.warning("Can't get image limits as the account has been suspended, Attempt to wait for 12 hours")
                        # 账号已被暂停，无法访问配额页面，等待12小时配额自行恢复 / The account has been suspended
                        time.sleep(12 * 60 * 60)
                else:
                    image_limits,total_limits=self.get_image_limits()
                    logger.warning(f"Currently at {image_limits} towards the limit of {total_limits}. Waiting for quota restoration")
                    while True:
                        time.sleep(3600)
                        image_limits,_=self.get_image_limits()
                        print(f"Currently at {image_limits}")
                        if image_limits <= 200:
                            break
                return await self.download_image(semaphore, url, file_path)
            file = await self.fetch_data(url=real_url)
            with open(file_path, 'wb') as f:
                f.write(file)

    @logger.catch()
    async def get_image_url(self):
        """
        获取图片地址
        Get the image address

        返回值:
        Returns:[
            [url, filename],
            ...
            ["https://exhentai.org/s/57a822bab0/2614866-3", "110030937_p2.jpg"]
        ]
        """

        hx_res = await self.fetch_data(url=self.long_url)
        page_data = BeautifulSoup(hx_res, 'html.parser')

        # 判断是否被版权 / Check for copyright status.
        copyright_msg = page_data.select_one('.d p')
        if copyright_msg is not None:
            if copyright_msg.find('copyright') != -1:
                return "copyright"

        # 获取总页码 / Get the total page number
        ptb = page_data.select_one('.ptb td:nth-last-child(2)')
        if ptb is None:
            # 这通常意味着当前ip已被暂时封禁 / This usually means that the current ip has been temporarily banned
            logger.warning(page_data)
            sys.exit(0)

        ptb = ptb.get_text()
        ptb = int(ptb) - 1

        # 第一层图片地址 / The address of the first layer image
        page_img_url = []

        sub_ptb = 0
        # 遍历页码, 获取所有第一层图片地址
        # Traversing the page number to get all the first-level image addresses
        while sub_ptb <= ptb:
            if sub_ptb != 0:
                page_data = await self.fetch_data(url=f"{self.long_url}?p={sub_ptb}")
                page_data = BeautifulSoup(page_data, 'html.parser')

            page_data = page_data.select('#gdt > .gdtl > a')

            for i in page_data:
                img_url = str(i.get('href'))
                filename = str(i.select_one('img').get("title").split(" ")[-1:][0])
                page_img_url.append([img_url, filename])

            sub_ptb = sub_ptb + 1

        return page_img_url

    @logger.catch()
    async def apply(self):
        logger.info(f"Download Web Gallery...: {self.long_url}")

        img_url_res = await self.get_image_url()

        if img_url_res == "copyright":
            logger.warning(
                f"This gallery is unavailable due to a copyright claim. {self.long_url}    {self.title}")
            with sqlite3.connect(self.dbs_name) as co:
                co.execute(f'UPDATE eh_data SET copyright_flag=1 WHERE gid={self.gid}')
                co.commit()
            return False

        # Download images
        semaphore = asyncio.Semaphore(int(self.connect_limit))
        task_list = []
        os.makedirs(self.filepath_tmp, exist_ok=True)
        for _p in img_url_res:
            url = _p[0]
            file_path = os.path.join(self.filepath_tmp, _p[1])
            if os.path.exists(file_path):
                logger.info(f"File {_p[1]} already exists. Skipping download.")
            else:
                req = self.download_image(semaphore, url, file_path)
                task_list.append(req)

        await tqdm_asyncio.gather(*task_list)

        # 判断 new_path 是否存在文件夹
        # # Determine whether there is a folder in new_path
        check_dir = None
        if os.path.isdir(self.filepath_end):
            logger.warning("Directory already exists, Whether to delete the overlay? Y/N\n")
            logger.warning(f"{self.filepath_tmp}\n>>>\n{self.filepath_end}")

            while check_dir is None:
                check_dir = input()
                if check_dir.lower() == "n":
                    logger.warning("[OK] skip coverage")
                elif check_dir.lower() == "y":
                    shutil.rmtree(self.filepath_end)
                    shutil.move(self.filepath_tmp, self.filepath_end)
                    logger.warning("[OK] del and coverage")
                else:
                    check_dir = None
        else:
            shutil.move(self.filepath_tmp, self.filepath_end)

        with sqlite3.connect(self.dbs_name) as co:
            co.execute(f'UPDATE fav_category SET web_1280x_flag = 1 WHERE gid = {self.gid}')
            co.commit()

        logger.info(f"OK: {self.long_url}")
