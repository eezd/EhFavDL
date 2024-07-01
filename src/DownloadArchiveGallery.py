import copy
import sys
import zipfile
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from httpx import RemoteProtocolError
from rich import print, json
from tqdm import tqdm

from .Config import Config
from .common import *

folder = "archive"


class DownloadArchiveGallery(Config):

    def __init__(self):
        super().__init__()

    def search_download_url(self, gid, token):
        hx_res = self.request.get(f"https://{self.base_url}/g/{gid}/{token}", timeout=10)
        page_data = BeautifulSoup(hx_res, 'html.parser')
        archive_url = page_data.select_one('.g2.gsp a')
        if archive_url is None:
            return False
        archive_url = archive_url['onclick'].split("'")[1].replace("--", "-")

        hx_res = self.request.post(archive_url, data={"dltype": "org", "dlcheck": "Download+Original+Archive"},
                                   timeout=5)
        page_data = BeautifulSoup(hx_res, 'html.parser')
        archive_url = page_data.select_one('#continue a')['href']

        dl_site = urlsplit(archive_url).netloc

        hx_res = self.request.get(archive_url, timeout=5)
        page_data = BeautifulSoup(hx_res, 'html.parser')
        archive_url = page_data.select_one('a')['href']

        dl_url = f"https://{dl_site}{archive_url}"
        return dl_url

    def download_file(self, dl_url, filename):
        filename = windows_escape(filename)
        sub_path = os.path.join(self.data_path, folder)
        file_url = os.path.join(sub_path, filename)
        os.makedirs(sub_path, exist_ok=True)
        file_size = 0  # Initialize file_size to 0
        headers = copy.deepcopy(self.request_hearders)

        retry_attempts = 5  # Number of retry attempts
        retry_delay = 5  # Delay in seconds between retries

        for attempt in range(retry_attempts):
            try:
                if os.path.exists(file_url):
                    # If the file exists, determine the size and resume from where it left off
                    file_size = os.path.getsize(file_url)
                    headers.update({'Range': f'bytes={file_size}-'})
                    mode = 'ab'  # Append to existing file
                else:
                    mode = 'wb'  # Write new file

                with self.request.stream("GET", dl_url, headers=headers, timeout=10) as response:
                    if response.status_code == 200 or response.status_code == 206:  # 206 indicates partial content
                        total_size = int(response.headers.get("Content-Length", 0)) + file_size
                        block_size = 1024
                        with tqdm(total=total_size, initial=file_size, unit="B", unit_scale=True) as progress_bar:
                            with open(file_url, mode) as file:
                                for data in response.iter_raw(block_size):
                                    file.write(data)
                                    progress_bar.update(len(data))

                        if total_size != 0 and progress_bar.n != total_size:
                            raise RuntimeError("Could not download file")

                        try:
                            with zipfile.ZipFile(file_url, 'r') as zip_file:
                                zip_file.testzip()
                        except zipfile.BadZipFile:
                            logger.error(f"检测到压缩包损坏, 请删除文件: {file_url}")
                            logger.error(f"Detected a corrupted archive. Please delete the file.: {file_url}")
                            return False
                        except OSError as e:
                            logger.error(f"检测到压缩包损坏, 请删除文件: {file_url}")
                            logger.error(f"Detected a corrupted archive. Please delete the file.: {file_url}")
                            return False

                        return True
                    else:
                        content = response.read().decode('utf-8')
                        if "IP quota exhausted" in content:
                            logger.warning("IP quota exhausted.")
                            sys.exit(1)
                        logger.error(f'{content}: {filename}')
                        return False
            except (RemoteProtocolError, Exception) as e:
                if attempt < retry_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...({filename})")
                    time.sleep(retry_delay)
                else:
                    logger.warning(f"Download failed after {retry_attempts} attempts.({filename})")
                    sys.exit(1)
                    # return False

    def check_loc_file(self):
        directory = os.path.join(self.data_path, folder)
        loc_gid = []
        status = 0
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.getsize(file_path) > 0:
                    try:
                        with zipfile.ZipFile(file_path, 'r') as zip_file:
                            bad_file = zip_file.testzip()
                            if bad_file:
                                logger.error(f"检测到压缩包损坏, 请删除文件: {file_path}")
                                logger.error(f"Detected a corrupted archive. Please delete the file.: {file_path}")
                            else:
                                file = str(file)
                                if len(file.split(".zip")) != 1:
                                    loc_gid.append(file.split("-")[0])
                    except zipfile.BadZipFile:
                        logger.error(f"检测到压缩包损坏, 请删除文件: {file_path}")
                        logger.error(f"Detected a corrupted archive. Please delete the file.: {file_path}")
                        status = 1
                    except OSError as e:
                        logger.error(f"检测到压缩包损坏, 请删除文件: {file_path}")
                        logger.error(f"Detected a corrupted archive. Please delete the file.: {file_path}")
                        status = 1
        if status == 1:
            sys.exit(1)
        return loc_gid

    # def update_archive_status(self):
    #     directory = os.path.join(self.data_path, folder)
    #     loc_gid = []
    #     for root, dirs, files in os.walk(directory):
    #         for file in files:
    #             file_path = os.path.join(root, file)
    #             if os.path.getsize(file_path) > 0:
    #                 file = str(file)
    #                 if len(file.split(".zip")) != 1:
    #                     with sqlite3.connect(self.dbs_name) as co:
    #                         co.execute(f'UPDATE fav SET status=1 WHERE gid={file.split("-")[0]}')
    #                         co.commit()

    def apply(self):
        print("[bold magenta]说明1: 下载所指定收藏夹的所有数据, 不受数据库 fav 中 status 字段控制.[/bold magenta]")
        print(f"[bold magenta]说明2: 会跳过目录({folder})中已存在的gid文件.[/bold magenta]")
        print(f"[bold magenta]说明3: 确保已经执行了(1. Add Fav Info)更新FAV数据.[/bold magenta]")

        print(
            "[bold magenta]Note 1: Download all data from the specified collection, regardless of the status field in "
            "the FAV database.[/bold magenta]")
        print(
            f"[bold magenta]Note 2:The code will skip gid files that already exist in the directory ({folder}).[/bold magenta]")
        print(
            f"[bold magenta]Note 3: Make sure that the (1. Add Fav Info) update for FAV data has been executed.[/bold magenta]")
        time.sleep(0.5)

        loc_gid = []

        check_zip = input("是否检测zip文件是否损坏? y/n\nCheck if the zip file is corrupted? y/n\n")

        if check_zip.lower() != 'n':
            logger.info(f"check loc file...")
            loc_gid = self.check_loc_file()

        favcat = int(input("请输入你需要下载的收藏夹ID(0-9)\nPlease enter the collection you want to download.:"))

        dl_list = []

        with sqlite3.connect(self.dbs_name) as co:
            gid_condition = ','.join(['?' for _ in loc_gid])
            # ce = co.execute(f'SELECT gid, token, title, title_jpn FROM fav WHERE gid = 1249409')
            ce = co.execute(
                f'SELECT gid, token, title, title_jpn FROM fav WHERE a_status=0 AND gid in (SELECT gid FROM fav_category WHERE fav_id = {favcat} AND gid NOT IN ({gid_condition}))',
                loc_gid)

            for i in ce.fetchall():
                title = i[3] if i[3] else i[2]
                dl_list.append([i[0], i[1], title])

            logger.info(f"total download list:{json.dumps(dl_list, indent=4, ensure_ascii=False)}")

            favcat_check = input(f"(len: {len(dl_list)})Press Enter to confirm\n")
            if favcat_check != "":
                print("Cancel")
                sys.exit(1)

        for j in dl_list:
            dl_url = self.search_download_url(j[0], j[1])
            time.sleep(2)

            if dl_url is False:
                logger.warning(f"⚠️ not found: https://{self.base_url}/g/{j[0]}/{j[1]}/")
                continue
            else:
                logger.info(f"https://{self.base_url}/g/{j[0]}/{j[1]}/, dl_url={dl_url}")
            dl_status = self.download_file(dl_url, str(j[0]) + "-" + windows_escape(str(j[2])) + ".zip")

            if dl_status is False:
                logger.warning(f"⚠️ download failed: https://{self.base_url}/g/{j[0]}/{j[1]}/")
                continue
            else:
                with sqlite3.connect(self.dbs_name) as co:
                    co.execute(f'UPDATE fav SET a_status=1 WHERE gid={j[0]}')
                    co.commit()
                logger.info(f"https://{self.base_url}/g/{j[0]}/{j[1]}/, download OK")
            time.sleep(2)

        # with self.request.stream("GET", dl_url, timeout=10) as response:
        #     if response.status_code == 200:
        #         # sub_path = os.path.join(self.data_path, 'temp', str(self.gid) + '-' + self.title)
        #         sub_path = os.path.join(self.data_path, 'temp')
        #         os.makedirs(sub_path, exist_ok=True)
        #         with open(os.path.join(sub_path, "2868035.zip"), "wb") as file:
        #             for chunk in response.iter_raw():
        #                 file.write(chunk)
        #         return "OK"
        #     else:
        #         # return [file_name, index]
        #         sys.exit(1)
