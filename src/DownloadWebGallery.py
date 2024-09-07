import asyncio
import hashlib
import os
import shutil

from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio

from src.Support import Support
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

    async def calc_sha256(self, file_path):
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def check_save(self, file_path, file):
        """
        假如存在相同文件, 使用哈希判断
        If identical files exist, use hash comparison to determine.
        """
        if os.path.exists(file_path):
            exist_hash = await self.calc_sha256(file_path)
            new_hash = hashlib.sha256(file).hexdigest()

            if new_hash == exist_hash:
                return file_path

            base_name, ext = os.path.splitext(file_path)
            counter = 2

            while os.path.exists(file_path):
                exist_hash = await self.calc_sha256(file_path)

                if new_hash == exist_hash:
                    return file_path

                counter += 1
                file_path = f"{base_name} ({counter}){ext}"

        with open(file_path, 'wb') as f:
            f.write(file)

        return file_path

    @logger.catch()
    async def download_image(self, semaphore, url, file_path):
        """
        注意: 一旦执行到这步, 那么不管你下没下载图片, 都会消耗你的 IP 配额
        Once you reach this step, your IP quota will be consumed regardless of whether you download the image or not.
        """
        async with semaphore:
            reload_count = 0
            while reload_count < 6:
                reload_count += 1
                real_url = await self.fetch_data(url=url)
                if real_url is False:
                    return real_url
                soup = BeautifulSoup(real_url, 'html.parser')
                real_url = soup.select_one('img#img').get('src')

                load_fail = soup.select_one('#loadfail').get('onclick')
                url = url + "&nl=" + str(re.search(r'return nl\(\'(.*)\'\)', load_fail).group(1))

                # 配额用尽，返回的 real_url 会变成509.gif
                # Quota exhausted, the returned real_url will change to 509.gif.
                if re.match(r'^https://(exhentai|e-hentai)\.org/img/509\.gif$', real_url):
                    logger.warning("509: YOU HAVE TEMPORARILY REACHED THE LIMIT")
                    if not await self.get_image_limits():
                        # 账号已被暂停，无法访问配额页面，等待12小时配额自行恢复 (10hits/min) / The account has been suspended
                        logger.warning(
                            "Can't get image limits as the account has been suspended, Attempt to wait for 12 hours")
                        await asyncio.sleep(12 * 60 * 60)
                    else:
                        await self.wait_image_limits()
                    return await self.download_image(semaphore=semaphore, url=url, file_path=file_path)
                dl_status = await self.fetch_data(url=real_url, tqdm_file_path=file_path)
                if isinstance(dl_status, str):
                    if dl_status == "reload_image":
                        logger.info(F"Reload Image. Retrying... {reload_count} / 6 ")
                else:
                    return dl_status
            return False

    @logger.catch()
    async def get_image_url(self):
        """
        获取图片地址
        Get the image address

        返回值:
        Returns:[
            [url, filename],
            ...
            ["https://exhentai.org/s/57a822bab0/2614866-3", "00000003.jpg"]
        ]
        OR
        Returns: "copyright"
        """

        hx_res = await self.fetch_data(url=self.long_url)
        page_data = BeautifulSoup(hx_res, 'html.parser')

        # 判断是否被版权 / Check for copyright status.
        copyright_msg = page_data.select_one('.d p')
        if copyright_msg is not None:
            if copyright_msg.find('copyright') != -1:
                return "copyright"

        # 获取页面上显示的 pages，用于校验是否获取到全部的 page_img_url
        pages = None
        lengthtd = page_data.find('td', text='Length:')
        if lengthtd:
            length = lengthtd.find_next_sibling('td', class_='gdt2').text.strip()
            pages = re.search(r'\d+', length).group()
            pages = int(pages)

        # 获取总页码 / Get the total page number
        ptb = page_data.select_one('.ptb td:nth-last-child(2)')
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
                # filename = str(i.select_one('img').get("title").split(" ")[-1:][0])
                filename = str(i.select_one('img').get("alt")).zfill(8) + ".jpg"
                page_img_url.append([img_url, filename])

            sub_ptb = sub_ptb + 1

        if len(page_img_url) == 0:
            # 加载到 https://exhentai.org/img/blank.gif，导致获取链接为空
            # 往往几个小时也不见恢复，这到底是为什么呢
            logger.warning("Failed to get image urls, retrying after 30mins……")
            await asyncio.sleep(30 * 60)
            return await self.get_image_url()
        elif pages and len(page_img_url) < pages:
            # 检查是否获取到全部链接
            logger.warning("Failed for missing pages, retrying after 30mins……")
            await asyncio.sleep(30 * 60)
            return await self.get_image_url()
        return page_img_url

    @logger.catch()
    async def apply(self):
        before_image_limits, _ = await self.wait_image_limits()
        logger.info(f"Download Web Gallery...: {self.long_url}")
        res_image_list = await self.get_image_url()
        if isinstance(res_image_list, str):
            if res_image_list == "copyright":
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
        for _p in res_image_list:
            url = _p[0]
            file_path = os.path.join(self.filepath_tmp, _p[1])
            if os.path.exists(file_path):
                logger.info(f"File {_p[1]} already exists. Skipping download.")
            else:
                req = self.download_image(semaphore, url, file_path)
                task_list.append(req)
        results = await tqdm_asyncio.gather(*task_list, desc=F"DownloadWebGallery>>{self.long_url}")
        for result in results:
            if not result:
                logger.warning(f"Failed to download image: {self.long_url}")
                return False

        # 再次检查是否缺页 / Recheck for missing pages
        file_count = 0
        for _, _, files in os.walk(self.filepath_tmp):
            file_count += len(files)
        if file_count != len(res_image_list):
            logger.warning(f"Failed for missing pages: {self.long_url}")
            return False

        # 判断 new_path 是否存在文件夹
        # Determine whether there is a folder in new_path
        if os.path.isdir(self.filepath_end):
            logger.warning(f"Directory already exists, coverage {self.filepath_end}")
            shutil.rmtree(self.filepath_end)
            shutil.move(self.filepath_tmp, self.filepath_end)
        else:
            shutil.move(self.filepath_tmp, self.filepath_end)

        Support().create_xml(gid=self.gid, path=self.filepath_end)
        Support().create_cbz(src_path=self.filepath_end, target_path=self.filepath_end)
        shutil.rmtree(self.filepath_end)

        with sqlite3.connect(self.dbs_name) as co:
            co.execute(f'UPDATE fav_category SET web_1280x_flag = 1 WHERE gid = {self.gid}')
            co.commit()

        logger.info(f"[OK] Download Web Gallery...: {self.long_url}")

        after_image_limits, after_total_limits = await self.get_image_limits()
        logger.info(
            f"OK, {after_image_limits - before_image_limits} IP quotas used({after_image_limits} / {after_total_limits}): {self.long_url}")
        return True
