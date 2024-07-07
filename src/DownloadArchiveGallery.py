import copy
import json
import os
import sqlite3
import sys
import zipfile
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from httpx import RemoteProtocolError, ReadTimeout, WriteTimeout, ConnectTimeout
from loguru import logger
from tqdm import tqdm

from .Config import Config
from .common import *

# 下载路径为: data_path + "archive"
folder = "archive"


class DownloadArchiveGallery(Config):

    def __init__(self):
        super().__init__()

    @logger.catch()
    def search_download_url(self, gid, token, original_flag=True):
        """
        original=True: 默认获取 Original(原图) Download Url
        有些画廊在Archiver中不存在 Resample(1280x) 版本, 因此返回值第二参数用来校验, 比如(gid=56853&token=6318356cb1)

        Returns:
            return [dl_url, "1280x"]
            return [dl_url, "original"]
        """

        retry_attempts = 5  # Number of retry attempts
        retry_delay = 5  # Delay in seconds between retries

        if gid is None or token is None:
            logger.error("gid or token is None")
            sys.exit(1)

        main_url = f"https://{self.base_url}/g/{gid}/{token}"

        for attempt in range(retry_attempts):
            try:
                logger.info(f"get >>> search archive key... {main_url}")

                hx_res = self.request.get(main_url, timeout=30)
                time.sleep(0.5)
                page_data = BeautifulSoup(hx_res, 'html.parser')

                # 判断是否被版权
                copyright_msg = page_data.select_one('.d p')
                if copyright_msg is not None:
                    if copyright_msg.find('copyright') != -1:
                        return [False, "copyright"]

                archive_url = page_data.select_one('a[onclick*="archiver.php"]')
                if archive_url is None:
                    return [False, ""]
                archive_url = archive_url['onclick'].split("'")[1].replace("--", "-")

                logger.info(f"get >>> archive_url... {archive_url}")

                if original_flag:
                    hx_res = self.request.post(archive_url,
                                               data={"dltype": "org", "dlcheck": "Download+Original+Archive"},
                                               timeout=30)
                else:
                    hx_res = self.request.post(archive_url,
                                               data={"dltype": "res", "dlcheck": "Download+Resample+Archive"},
                                               timeout=30)
                time.sleep(0.5)
                page_data = BeautifulSoup(hx_res, 'html.parser')
                archive_url = page_data.select_one('#continue a')['href']
                dl_site = urlsplit(archive_url).netloc

                logger.info(f"get >>> download_url... {archive_url}")
                hx_res = self.request.get(archive_url, timeout=300)
                time.sleep(0.5)
                page_data = BeautifulSoup(hx_res, 'html.parser')
                archive_url = page_data.select_one('a')['href']
                dl_url = f"https://{dl_site}{archive_url}"

                if archive_url is None or archive_url == "" or archive_url == False:
                    logger.error(
                        f"page_data: {page_data}\n"
                        f"archive_url is None or empty.(search_download_url(): {archive_url}\n{main_url}\n")
                    logger.error(f"Please submit issues to GitHub >>> https://github.com/eezd/EhFavDL/issues")
                    sys.exit(1)

                # True 代表当前是 1280x 画廊, 用来处理一些不存在 1280x 的画廊, 比如(gid=56853&token=6318356cb1)
                check_resample_status = False
                file_name = str(page_data.select_one('strong').getText())
                if len(file_name) > 13:
                    check_resample_status = file_name[-12:].find("1280x") != -1

                if check_resample_status:
                    logger.info(f"return [{dl_url}, '1280x']")
                    return [dl_url, "1280x"]
                else:
                    logger.info(f"return [{dl_url}, 'original']")
                    return [dl_url, "original"]

            except (ReadTimeout, WriteTimeout, ConnectTimeout):
                if attempt < retry_attempts - 1:
                    logger.warning(
                        f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...(search_download_url(): {main_url})")
                    time.sleep(retry_delay)
                else:
                    logger.warning(
                        f"search_download_url {retry_attempts} attempts.(search_download_url(): {main_url})")
                    sys.exit(1)

    @logger.catch()
    def download_file(self, dl_url, filename):
        filename = windows_escape(filename)
        sub_path = os.path.join(self.data_path, folder)
        file_path = os.path.join(sub_path, filename)
        os.makedirs(sub_path, exist_ok=True)
        file_size = 0  # Initialize file_size to 0
        headers = copy.deepcopy(self.request_headers)

        retry_attempts = 5  # Number of retry attempts
        retry_delay = 10  # Delay in seconds between retries
        for attempt in range(retry_attempts):
            try:
                mode = 'wb'  # Write new file
                if os.path.exists(file_path):
                    try:
                        with zipfile.ZipFile(file_path, 'r') as zip_file:
                            zip_file.testzip()
                        logger.warning(f"已存在该文件, 跳过: {filename}")
                        return True
                    except (zipfile.BadZipFile, OSError):
                        logger.info(f"开始断点续传: {filename}")
                        logger.info(f"Start resumable download.: {filename}")
                        file_size = os.path.getsize(file_path)
                        headers.update({'Range': f'bytes={file_size}-'})
                        mode = 'ab'  # Append to existing file

                with self.request.stream("GET", dl_url, headers=headers, timeout=30) as response:
                    if response.status_code == 200 or response.status_code == 206:  # 206 indicates partial content
                        total_size = int(response.headers.get("Content-Length", 0)) + file_size
                        block_size = 1024
                        with tqdm(total=total_size, initial=file_size, unit="B", unit_scale=True) as progress_bar:
                            with open(file_path, mode) as file:
                                for data in response.iter_raw(block_size):
                                    file.write(data)
                                    progress_bar.update(len(data))

                        if total_size != 0 and progress_bar.n != total_size:
                            raise RuntimeError("Could not download file")

                        try:
                            with zipfile.ZipFile(file_path, 'r') as zip_file:
                                zip_file.testzip()
                        except zipfile.BadZipFile:
                            logger.error(f"检测到压缩包损坏, 请删除文件: {file_path}")
                            logger.error(f"Detected a corrupted archive. Please delete the file.: {file_path}")
                            return False
                        except OSError as e:
                            logger.error(f"检测到压缩包损坏, 请删除文件: {file_path}")
                            logger.error(f"Detected a corrupted archive. Please delete the file.: {file_path}")
                            return False
                        return True

                    else:
                        content = response.read().decode('utf-8')
                        if "IP quota exhausted" in content:
                            logger.warning("IP quota exhausted.")
                            time.sleep(5)
                            return False
                        elif "You have clocked too many downloaded bytes on this gallery" in content:
                            logger.warning("You have clocked too many downloaded bytes on this gallery.")
                            logger.warning("Please open Gallery---Archive Download---Cancel")
                            logger.warning(filename)
                            time.sleep(5)
                            return False
                        else:
                            logger.warning(f"code: {response.status_code}")
                            logger.warning(f'{content}: {filename}')
                            logger.error(f"Please submit issues to GitHub >>> https://github.com/eezd/EhFavDL/issues")

                        raise RemoteProtocolError
            except (RemoteProtocolError, Exception) as e:
                if attempt < retry_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...({filename})")
                    time.sleep(retry_delay)
                else:
                    logger.warning(f"Download failed after {retry_attempts} attempts.({filename})")
                    return False

    @logger.catch()
    def apply(self):
        fav_cat = -1
        while not 0 <= fav_cat <= 9:
            fav_cat = int(input("请输入你需要下载的收藏夹ID(0-9)\nPlease enter the collection you want to download.:"))

        download_type = ""
        while download_type != "o" and download_type != "r":
            download_type = str(
                input(
                    "下载 Original 还是 Resample-1280x, 请输入 O / R. \n For downloading, choose Original or Resample-1280x. Please enter O / R.")).lower()

        # 用在 search_download_url() 判断下载类型
        if download_type == "o":
            original_flag = True
            download_type = "original_flag"
        else:
            original_flag = False
            download_type = "web_1280x_flag"

        dl_list = []

        # 检查数量和下载列表
        with sqlite3.connect(self.dbs_name) as co:
            ce = co.execute(
                f'SELECT gid, token, title, title_jpn FROM eh_data WHERE gid in '
                f'(SELECT gid FROM fav_category WHERE fav_id = {fav_cat} AND {download_type} = 0)')
            # ce = co.execute(
            #     f'SELECT gid, token, title, title_jpn FROM eh_data WHERE gid in '
            #     f'(SELECT gid FROM fav_category WHERE gid = 1593645)')

            for i in ce.fetchall():
                title = i[3] if i[3] else i[2]
                dl_list.append([i[0], i[1], title])

            logger.info(
                f"(fav_cat = {fav_cat}) total download list:{json.dumps(dl_list, indent=4, ensure_ascii=False)}")

            fav_cat_check = input(f"(len: {len(dl_list)})Press Enter to confirm\n")
            if fav_cat_check != "":
                print("Cancel")
                sys.exit(1)

        # 开始下载
        for j in dl_list:
            gid = j[0]
            token = j[1]
            title = j[2]

            # 和
            check_file_name = (str(gid) + "-" + windows_escape(str(title)) + ".zip") if original_flag else (
                    str(gid) + "-" + windows_escape(str(title)) + "-1280x.zip")
            sub_path = os.path.join(self.data_path, folder)
            file_path = os.path.join(sub_path, check_file_name)
            os.makedirs(sub_path, exist_ok=True)
            if os.path.exists(file_path):
                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_file:
                        zip_file.testzip()
                    logger.warning(f"已存在该文件, 跳过: {file_path}")
                    continue
                except (zipfile.BadZipFile, OSError):
                    pass

            _search_dl = self.search_download_url(gid, token, original_flag)

            if _search_dl[0] is False and _search_dl[1] == "copyright":
                logger.warning(
                    f"This gallery is unavailable due to a copyright claim. https://{self.base_url}/g/{gid}/{token}    {title}")
                with sqlite3.connect(self.dbs_name) as co:
                    co.execute(f'UPDATE eh_data SET copyright_flag=1 WHERE gid={gid}')
                    co.commit()
                continue

            dl_url = _search_dl[0]

            # original or 1280x
            dl_type = _search_dl[1]
            if dl_type == "1280x":
                file_name = str(gid) + "-" + windows_escape(str(title)) + "-1280x.zip"
                download_type = "web_1280x_flag"
            elif dl_type == "original":
                file_name = str(gid) + "-" + windows_escape(str(title)) + ".zip"
                download_type = "original_flag"
            else:
                logger.warning(f"_search_dl: {_search_dl}")
                logger.error(f"Please provide the log file to the GitHub issue >>> github.com/eezd/EhFavDL/issues")
                sys.exit(1)

            time.sleep(2)

            # 找不到就跳过, 需要重新执行代码下载
            if dl_url is False:
                logger.warning(f"⚠️ not found: https://{self.base_url}/g/{gid}/{token}/")
                continue
            else:
                logger.info(f"https://{self.base_url}/g/{gid}/{token}/, dl_url={dl_url}")

            dl_status = self.download_file(dl_url, file_name)

            if dl_status is False:
                logger.warning(f"⚠️ download failed: https://{self.base_url}/g/{j[0]}/{j[1]}/")
                continue
            else:
                with sqlite3.connect(self.dbs_name) as co:
                    co.execute(f'UPDATE fav_category SET {download_type}=1 WHERE gid={j[0]}')
                    co.commit()
                logger.info(f"https://{self.base_url}/g/{j[0]}/{j[1]}/, download OK")
            time.sleep(2)
