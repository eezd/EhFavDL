import sys
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from tqdm import tqdm

from .Config import Config
from .common import *
from rich import print

folder = "archive"


class DownloadArchiveGallery(Config):

    def __init__(self):
        super().__init__()

    def search_download_url(self, gid, token):
        hx_res = self.request.get(f"https://{self.base_url}/g/{gid}/{token}/", timeout=10)
        page_data = BeautifulSoup(hx_res, 'html.parser')
        archive_url = page_data.select_one('.g2.gsp a')
        if archive_url is None:
            return False
        archive_url = archive_url['onclick'].split("'")[1].replace("--", "-")

        hx_res = self.request.post(archive_url, data={"dltype": "org", "dlcheck": "Download+Original+Archive"},
                                   timeout=10)
        page_data = BeautifulSoup(hx_res, 'html.parser')
        archive_url = page_data.select_one('#continue a')['href']

        dl_site = urlsplit(archive_url).netloc

        hx_res = self.request.get(archive_url, timeout=10)
        page_data = BeautifulSoup(hx_res, 'html.parser')
        archive_url = page_data.select_one('a')['href']

        dl_url = f"https://{dl_site}{archive_url}"
        return dl_url

    def download_file(self, dl_url, filename):
        with self.request.stream("GET", dl_url, timeout=10) as response:
            if response.status_code == 200:
                total_size = int(response.headers.get("Content-Length"))
                block_size = 1024
                # sub_path = os.path.join(self.data_path, 'temp', str(self.gid) + '-' + self.title)
                sub_path = os.path.join(self.data_path, folder)
                os.makedirs(sub_path, exist_ok=True)

                with tqdm(total=total_size, unit="B", unit_scale=True) as progress_bar:
                    with open(os.path.join(sub_path, filename), "wb") as file:
                        for data in response.iter_raw(block_size):
                            progress_bar.update(len(data))
                            file.write(data)

                if total_size != 0 and progress_bar.n != total_size:
                    raise RuntimeError("Could not download file")

                return True
            else:
                return False

    def check_loc_file(self):
        directory = os.path.join(self.data_path, folder)
        loc_gid = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.getsize(file_path) > 0:
                    file = str(file)
                    if len(file.split(".zip")) != 1:
                        loc_gid.append(file.split("-")[0])
        return loc_gid

    # def update_archive_state(self):
    #     directory = os.path.join(self.data_path, folder)
    #     loc_gid = []
    #     for root, dirs, files in os.walk(directory):
    #         for file in files:
    #             file_path = os.path.join(root, file)
    #             if os.path.getsize(file_path) > 0:
    #                 file = str(file)
    #                 if len(file.split(".zip")) != 1:
    #                     with sqlite3.connect(self.dbs_name) as co:
    #                         co.execute(f'UPDATE FAV SET STATE=1 WHERE GID={file.split("-")[0]}')
    #                         co.commit()

    def apply(self):
        print("[bold magenta]说明1: 下载所指定收藏夹的所有数据, 不受数据库 FAV 中 STATE 字段控制.[/bold magenta]")
        print(f"[bold magenta]说明2: 会跳过目录({folder})中已存在的GID文件.[/bold magenta]")
        print(f"[bold magenta]说明3: 确保已经执行了(1. Add Fav Info)更新FAV数据.[/bold magenta]")

        print(
            "[bold magenta]Note 1: Download all data from the specified collection, regardless of the STATE field in "
            "the FAV database.[/bold magenta]")
        print(
            f"[bold magenta]Note 2:The code will skip GID files that already exist in the directory ({folder}).[/bold magenta]")
        print(
            f"[bold magenta]Note 3: Make sure that the (1. Add Fav Info) update for FAV data has been executed.[/bold magenta]")
        time.sleep(1)

        favcat = int(input("请输入你需要下载的收藏夹ID(0-9)\nPlease enter the collection you want to download.:"))

        with sqlite3.connect(self.dbs_name) as co:
            favcat_data = co.execute(f'SELECT * FROM CATEGORY WHERE ID = {favcat}')
            favcat_data = favcat_data.fetchone()

            favcat_check = input(f"Press Enter to confirm.:{favcat_data}")
            if favcat_check != "":
                print("Cancel")
                sys.exit(1)

        dl_list = []
        with sqlite3.connect(self.dbs_name) as co:
            # ce = co.execute(f'SELECT GID, TOKEN, TITLE_JPN FROM FAV')
            loc_gid = self.check_loc_file()
            gid_condition = ','.join(['?' for _ in loc_gid])
            # ce = co.execute(f'SELECT GID, TOKEN, TITLE_JPN FROM FAV WHERE GID = 2172361')
            ce = co.execute(
                f'SELECT GID, TOKEN, TITLE_JPN FROM FAV WHERE FAVORITE={favcat} AND A_STATE=0 AND GID NOT IN ({gid_condition})',
                loc_gid)
            for i in ce.fetchall():
                dl_list.append([i[0], i[1], i[2]])
        print(dl_list)
        for j in dl_list:
            dl_url = self.search_download_url(j[0], j[1])

            if dl_url is False:
                logger.warning(f"⚠️ not found: https://{self.base_url}/g/{j[0]}/{j[1]}/")
                continue
            else:
                logger.info(f"https://{self.base_url}/g/{j[0]}/{j[1]}/, dl_url={dl_url}")

            dl_status = self.download_file(dl_url, str(j[0]) + "-" + str(j[2]) + ".zip")

            if dl_status is False:
                logger.warning(f"⚠️ download failed: https://{self.base_url}/g/{j[0]}/{j[1]}/")
                continue
            else:
                with sqlite3.connect(self.dbs_name) as co:
                    co.execute(f'UPDATE FAV SET A_STATE=1 WHERE GID={j[0]}')
                    co.commit()
                logger.info(f"https://{self.base_url}/g/{j[0]}/{j[1]}/, download OK")

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
