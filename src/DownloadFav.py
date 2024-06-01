from .Config import Config
from .DownloadGallery import DownloadGallery
from .common import *


class DownloadFav(Config):

    def __init__(self):
        super().__init__()

    def apply(self):
        # 定义查询数组
        # Define query array
        dl_list = []
        with sqlite3.connect(self.dbs_name) as co:
            ce = co.execute(f'SELECT gid, token, title_jpn FROM fav WHERE status=0 AND ban=0 ORDER BY RANDOM()')
            # ce = co.execute(f'SELECT gid, token, title_jpn FROM fav WHERE gid = 2794528')
            co.commit()

            for i in ce.fetchall():
                dl_list.append([i[0], i[1], i[2]])

        # 开始下载
        # start download
        for j in dl_list:
            download_gallery = DownloadGallery(j[0], j[1], j[2])
            download_gallery.apply()
