import concurrent.futures
import os
import shutil
import sqlite3

from bs4 import BeautifulSoup
from loguru import logger
from tqdm import tqdm

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
    def download_image(self, url, file_name, index):
        """
        下载图片保存到本地 / Download pictures and save them locally
        url: 图片地址 / image url
        file_name: 文件名 / file name
        index: 文件索引位置 / file index

        返回值:
        Returns:
            下载成功返回: "OK"
            Successful download returns: "OK"
            下载失败返回: [file_name, index]
            Download failed return: [file_name, index]

            Returns-Example: ["01.jpg", 0]
        """
        try:
            with self.request.stream("GET", url, timeout=10) as response:
                if response.status_code == 200:
                    os.makedirs(self.filepath_tmp, exist_ok=True)
                    with open(os.path.join(self.filepath_tmp, file_name), "wb") as file:
                        for chunk in response.iter_raw():
                            file.write(chunk)
                    return "OK"
                else:
                    return [file_name, index]
        except Exception as exc:
            return [file_name, index]

    @logger.catch()
    def get_real_url_download(self, url, index):
        """
        获取图片真实地址, 调用 download_image() 下载
        Get the real address of the image, call download_image() to download
        """

        try:
            real_url = self.request.get(url)
            real_url = BeautifulSoup(real_url, 'html.parser')
            real_url = real_url.select_one('img#img').get('src')

            file_name = re.match('.*/(.*)\.(.*)$', real_url)
            file_name = file_name[1] + '.' + file_name[2]

            return self.download_image(real_url, file_name, index)
        except Exception as exc:
            # return [file_name, index]
            return self.get_real_url_download(url, index)

    @logger.catch()
    def get_image_url(self, err_id=None):
        """
        获取图片第一层地址
        Get the first layer address of the picture

        返回值:
        Returns:[
            [url, index],
            ...
            ["https://exhentai.org/s/57a822bab0/2614866-3", 2]
        ]
        """

        try:
            hx_res = self.request.get(self.long_url)

            page_data = BeautifulSoup(hx_res, 'html.parser')

            # 判断是否被版权
            copyright_msg = page_data.select_one('.d p')
            if copyright_msg is not None:
                if copyright_msg.find('copyright') != -1:
                    return "copyright"

            # 获取总页码 / Get the total page number
            ptb = page_data.select_one('.ptb td:nth-last-child(2)')

            if ptb is None:
                logger.warning(f"Recall after waiting 5 seconds >>> page number is None >>> {self.long_url}")
                time.sleep(5)
                return self.get_image_url(err_id)

            ptb = ptb.get_text()
            ptb = int(ptb) - 1

            # 第一层图片地址
            # The address of the first layer image
            page_img_url = []

            sub_ptb = 0
            # 遍历页码, 获取所有第一层图片地址
            # Traversing the page number to get all the first-level image addresses
            while sub_ptb <= ptb:
                if sub_ptb != 0:
                    try:
                        page_data = self.request.get(f"{self.long_url}?p={sub_ptb}")
                        page_data = BeautifulSoup(page_data, 'html.parser')
                    except Exception as exc:
                        logger.warning(exc)
                        logger.warning(
                            f"Recall after waiting 5 seconds >>> get_image_url({self.long_url})")
                        time.sleep(5)
                        self.get_image_url(err_id)

                page_data = page_data.select('#gdt > .gdtl > a')

                for i in page_data:
                    page_img_url.append(i.get('href'))
                sub_ptb = sub_ptb + 1

            # Format Data
            # Return >>> [[url1, 0], [url2, 1], ...]
            page_img_url = [[url, index] for index, url in enumerate(page_img_url)]

            # 返回需要重新下载的图片地址
            # Return the URL of the picture that needs to be downloaded again
            if err_id is not None:
                err_page_img_url = []
                for sub_err_id in err_id:
                    for _page_data in page_img_url:
                        if sub_err_id == _page_data[1]:
                            err_page_img_url.append([_page_data[0], _page_data[1]])
                return err_page_img_url

            return page_img_url

        except Exception as exc:
            logger.warning(exc)
            logger.warning(f"Recall after waiting 5 seconds >>> get_image_url()>>>{self.long_url}")
            time.sleep(5)
            return self.get_image_url(err_id)

    @logger.catch()
    def download(self, page_img_url):
        """
        多线程调用下载图片
        Multi-threaded call to download pictures

        Returns:[
            "OK",
            ["01.jpg", 0],
            "OK",
            ...
        ]
        """

        with tqdm(total=len(page_img_url)) as progress_bar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=int(self.connect_limit)) as executor:
                futures = [executor.submit(self.get_real_url_download, _p[0], _p[1]) for _p in page_img_url]

                for future in concurrent.futures.as_completed(futures):
                    progress_bar.update(1)

        concurrent.futures.wait(futures)
        data = [future.result() for future in futures if future.result() is not None]

        return data

    @logger.catch()
    def check_download(self, download_status):
        """
        判断全部图片是否成功下载, 否则再次重新下载失败的图片.
        Determine whether all pictures are successfully downloaded,
        otherwise re-download the failed pictures again.
        """

        dl_status = True

        dl_err_data = []
        for i in download_status:
            if i != "OK":
                dl_status = False
                dl_err_data.append(i)
                logger.warning(f"File download failed: {i[0], i[1]}")

        if not dl_status:
            logger.warning(f"Re-download After Waiting 5 Seconds")
            time.sleep(5)

            # 重新下载的索引
            # Re-downloaded index
            err_index_arr = [_index[1] for _index in dl_err_data]

            dl_err_data = self.get_image_url(err_index_arr)

            aaa = self.download(dl_err_data)

            return self.check_download(aaa)
        else:
            # old_path = os.path.join(self.data_path, folder, 'temp', str(self.gid) + '-' + self.title)
            # new_path = os.path.join(self.data_path, folder, str(self.gid) + '-' + self.title)

            # 判断 new_path 是否存在文件夹
            # # Determine whether there is a folder in new_path
            check_dir = None
            if os.path.isdir(self.filepath_end):
                logger.warning("Directory already exists, Whether to delete the overlay? Y/N")
                logger.warning(f"{self.filepath_tmp}>>>{self.filepath_end}")

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

            return True

    @logger.catch()
    def apply(self):
        logger.info(f"Download Web Gallery...: {self.long_url}")

        img_url_res = self.get_image_url()

        if img_url_res == "copyright":
            logger.warning(
                f"This gallery is unavailable due to a copyright claim. {self.long_url}    {self.title}")
            with sqlite3.connect(self.dbs_name) as co:
                co.execute(f'UPDATE eh_data SET copyright_flag=1 WHERE gid={self.gid}')
                co.commit()
            return False

        dl = self.download(img_url_res)
        cd = self.check_download(dl)

        if cd:
            logger.info(f"OK: {self.long_url}")
        else:
            logger.warning(f"check_download() return False: {self.long_url}")
