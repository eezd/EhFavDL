import asyncio
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from src.ComicInfo import ComicInfo
from src.Utils import *


class DownloadArchiveGallery(Config):

    def __init__(self):
        super().__init__()

    async def search_download_url(self, gid, token, original_flag=True):
        """
        original=True: Original Image Download Url
        original=False: Resample(1280x) Image Download Url

        有些画廊在Archiver中不存在 Resample(1280x) 版本, 因此返回值第二参数用来校验, 比如(gid=56853&token=6318356cb1)
        Some galleries lack a Resample(1280x) version in Archiver. Therefore, the second parameter of the
         return value is used for verification, for example (gid=56853&token=6318356cb1)

        Returns:
            return [dl_url, "1280x"]
            return [dl_url, "original"]
            return [False, "copyright"]
            return [False, ""]
        """

        if gid is None or token is None:
            logger.error("gid or token is None")
            sys.exit(1)

        main_url = f"https://{self.base_url}/g/{gid}/{token}"

        logger.info(f"get >>> search archive key... {main_url}")
        hx_res = await self.fetch_data(url=main_url)
        page_data = BeautifulSoup(hx_res, 'html.parser')

        # 判断是否被版权 / Check for copyright status.
        copyright_msg = page_data.select_one('.d p')
        if copyright_msg is not None:
            if copyright_msg.find('copyright') != -1:
                return [False, "copyright"]

        # 获取 archiver-key / Get archiver-key
        archive_url = page_data.select_one('a[onclick*="archiver.php"]')
        if archive_url is None:
            return [False, ""]
        archive_url = archive_url['onclick'].split("'")[1].replace("--", "-")

        # 获取下载地址 / Get download url
        logger.info(f"get >>> archive_url... {archive_url}")
        if original_flag:
            hx_res = await self.fetch_data(url=archive_url,
                                           data={"dltype": "org", "dlcheck": "Download+Original+Archive"})
        else:
            hx_res = await self.fetch_data(url=archive_url,
                                           data={"dltype": "res", "dlcheck": "Download+Resample+Archive"})

        page_data = BeautifulSoup(hx_res, 'html.parser')
        archive_url = page_data.select_one('#continue a')['href']
        dl_site = urlsplit(archive_url).netloc

        # 获取文件地址 / Get file url
        logger.info(f"get >>> download_url... {archive_url}")
        hx_res = await self.fetch_data(url=archive_url)

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
        # True indicates the current gallery is for 1280x, used to handle galleries that do not have 1280x,
        # such as (gid=56853&token=6318356cb1).
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

    async def download_file(self, dl_url, file_path):
        filename = os.path.basename(file_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file_size = 0  # Initialize file_size to 0
        if os.path.exists(file_path):
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_file:
                    zip_file.testzip()
                logger.warning(f"The file already exists, skipping: {filename}")
                return True
            except (zipfile.BadZipFile, OSError):
                logger.info(f"开始断点续传 / Start resumable download.: {filename}")
                file_size = os.path.getsize(file_path)

        await self.fetch_data_stream(url=dl_url, file_path=file_path, stream_range=file_size)

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

    async def dl_gallery(self, gid, token, title, original_flag):
        file_name = (str(gid) + "-" + windows_escape(str(title)) + ".zip") if original_flag else (
                str(gid) + "-" + windows_escape(str(title)) + "-1280x.zip")
        sub_path = self.web_path
        file_path = os.path.join(sub_path, file_name)

        if os.path.exists(file_path):
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_file:
                    zip_file.testzip()
                logger.warning(f"The file already exists, skipping: {file_path}")
                return True
            except (zipfile.BadZipFile, OSError):
                pass

        _search_dl = await self.search_download_url(gid=gid, token=token, original_flag=original_flag)

        if _search_dl[0] is False and _search_dl[1] == "copyright":
            logger.warning(
                f"This gallery is unavailable due to a copyright claim. https://{self.base_url}/g/{gid}/{token}    {title}")
            with sqlite3.connect(self.dbs_name) as co:
                co.execute(f'''UPDATE eh_data SET copyright_flag=1 WHERE gid={gid}''')
                co.commit()
            return False

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

        if dl_url is False:
            logger.warning(f"⚠️ not found: https://{self.base_url}/g/{gid}/{token}/")
            return False
        else:
            logger.info(f"https://{self.base_url}/g/{gid}/{token}/, dl_url={dl_url}")

        file_path = os.path.join(sub_path, file_name)
        dl_status = await self.download_file(dl_url, file_path)
        # dl_status = True

        if dl_status is False:
            logger.warning(f"⚠️ download failed: https://{self.base_url}/g/{gid}/{token}/")
            return False
        else:
            extract_to = os.path.splitext(file_path)[0]
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            ComicInfo().create_xml(gid=gid, path=extract_to)
            create_cbz(src_path=extract_to)
            rename_cbz_file(target_path=extract_to)
            shutil.rmtree(extract_to, ignore_errors=True)
            os.remove(file_path)
            with sqlite3.connect(self.dbs_name) as co:
                co.execute(f'''UPDATE fav_category SET {download_type}=1 WHERE gid={gid}''')
                co.commit()
            logger.info(f"https://{self.base_url}/g/{gid}/{token}/, download OK")
            return True

    async def go_dl(self, fav_cat, original_flag=False):
        dl_list = []
        # 检查数量和下载列表 / Check Quantity and Download List
        with sqlite3.connect(self.dbs_name) as co:
            ce = co.execute(f'''
            SELECT
                gid,
                token,
                title,
                title_jpn 
            FROM
                eh_data 
            WHERE
                gid in ( SELECT gid FROM fav_category WHERE fav_id IN ({fav_cat}) AND web_1280x_flag = 0 AND original_flag = 0 ) 
                AND copyright_flag = 0 
            ORDER BY
                gid DESC
            ''')
            # Testing
            # ce = co.execute(f'''
            # SELECT
            #     gid,
            #     token,
            #     title,
            #     title_jpn
            # FROM
            #     eh_data
            # WHERE
            #     gid in ( SELECT gid FROM fav_category WHERE gid = 2826520 )
            # ''')

            for i in ce.fetchall():
                title = i[3] if i[3] else i[2]
                dl_list.append([i[0], i[1], title])

            logger.info(
                f"(fav_cat = {fav_cat}) total download list:{json.dumps(dl_list, indent=4, ensure_ascii=False)}")

            await asyncio.sleep(5)

        # Start downloading
        for j in dl_list:
            gid = j[0]
            token = j[1]
            title = j[2]
            await self.dl_gallery(gid=gid, token=token, title=title, original_flag=original_flag)

    async def apply(self):
        fav_cat = -1
        while not 0 <= fav_cat <= 9:
            fav_cat = int(input("请输入你需要下载的收藏夹ID(0-9)\nPlease enter the collection you want to download.:"))

        download_type = ""
        while download_type != "o" and download_type != "r":
            download_type = str(
                input(
                    "下载 Original 还是 Resample-1280x, 请输入 O / R. \n "
                    "For downloading, choose Original or Resample-1280x. Please enter O / R.")).lower()

        # 判断下载类型 / Determine download type
        if download_type == "o":
            original_flag = True
        else:
            original_flag = False

        return await self.go_dl(fav_cat=fav_cat, original_flag=original_flag)
