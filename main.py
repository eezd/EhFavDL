import json
import sqlite3
import sys
from datetime import datetime

from loguru import logger

from src import *

logger.add(f'./log/{datetime.today().date()}.log', rotation='10 MB')


@logger.catch()
def main():
    Config().create_database()

    while True:
        print("\n1. Update User Fav Info")
        print("2. Update Gallery Metadata (Update Tags)")
        print("3. Download Web Gallery")
        print("4. Download Archive Gallery")
        print("5. Create ComicInfo.xml")
        print("6. Directory To Zip File")
        print("7. Rename Zip File")
        print("8. Update LANraragi Tags")
        print("9. Options (Checker)...")

        num = input("Select Number:")
        num = int(num) if num else None

        print('\n')

        add_fav_data = AddFavData()

        if num == 1:
            add_fav_data.apply()
        elif num == 2:
            add_fav_data.update_category()
            add_fav_data.add_tags_data(True)
        elif num == 3:
            fav_cat = int(input("请输入你需要下载的收藏夹ID(0-9)\nPlease enter the collection you want to download.:"))

            # 明天任务: 他获取的是 title_jpn 假如不存在 就需要获取 title
            dl_list = []
            with sqlite3.connect(Config().dbs_name) as co:
                ce = co.execute(
                    f"SELECT fc.gid, fc.token, eh.title, eh.title_jpn FROM eh_data AS eh, fav_category AS fc "
                    f"WHERE fc.web_1280x_flag=0 AND eh.expunged=0 AND eh.gid=fc.gid AND fc.fav_id = {fav_cat} ORDER BY RANDOM()")
                co.commit()

                for i in ce.fetchall():
                    if i[3] is not None and i[3] != "":
                        title = str(i[3])
                        dl_list.append([i[0], i[1], title])
                    else:
                        title = str(i[2])
                        dl_list.append([i[0], i[1], title])

            logger.info(
                f"(fav_cat = {fav_cat}) total download list:{json.dumps(dl_list, indent=4, ensure_ascii=False)}")

            fav_cat_check = input(f"(len: {len(dl_list)})Press Enter to confirm\n")
            if fav_cat_check != "":
                print("Cancel")
                sys.exit(1)

            # 开始下载
            # start download
            for j in dl_list:
                download_gallery = DownloadWebGallery(j[0], j[1], j[2])
                download_gallery.apply()
        elif num == 4:
            DownloadArchiveGallery().apply()
        elif num == 5:
            Support().create_xml()
        elif num == 6:
            Support().directory_to_zip()
        elif num == 7:
            Support().rename_zip_file()
        elif num == 8:
            Support().lan_update_tags()
        elif num == 9:
            while True:
                print("0. Return")
                print("1. Checker().check_gid_in_local_zip()")
                print("2. Checker().sync_local_to_sqlite_zip()")
                print("3. Checker().sync_local_to_sqlite_zip(True)")
                print("4. Checker().check_loc_file()")
                num = input("(Options) Select Number:")
                num = int(num) if num else None
                if num == 1:
                    Checker().check_gid_in_local_zip()
                elif num == 2:
                    Checker().sync_local_to_sqlite_zip()
                elif num == 3:
                    Checker().sync_local_to_sqlite_zip(True)
                elif num == 4:
                    Checker().check_loc_file()
                elif num == 0:
                    break


if __name__ == "__main__":
    main()
# import json
#
# data = AddFavData().post_eh_api({
#     "method": "gdata",
#     "gidlist": [
#         ['1913638', 'e2d5763883']
#     ],
#     "namespace": 1
# })
# db = json.dumps(data, indent=4, ensure_ascii=False)
# print(db)

# https://exhentai.org/archiver.php?gid=2903358&token=4cfb6685da&or=477853--58944ea61cc90e239d01af5f4660078dc10499d7
# self.archiver_key = archiver_key

# DownloadWebGallery(2903358, "4cfb6685da",
#                    "[真・聖堂☆本舗 (聖☆司)] 義弟は思いはじめている。[中国翻訳][無修正][DL版]-1280x").apply()

# DownloadArchiveGallery().apply()

# print(DownloadArchiveGallery().search_download_url(2903358, "4cfb6685da",
#                                                    "4cfb6685da&or=477853--58944ea61cc90e239d01af5f4660078dc10499d7"
#                                                    ))

# DownloadArchiveGallery().download_file(
#     DownloadArchiveGallery().search_download_url(2903358, "4cfb6685da",
#                                                  "4cfb6685da&or=477853--58944ea61cc90e239d01af5f4660078dc10499d7"),
#     "123.zip")

# check = Checker()
# check.update_local_to_sqlite_status()

# with sqlite3.connect(Config().dbs_name) as co:
#     for root, dirs, files in os.walk(r"E:\Hso\exhentaiDL\data\archive"):
#         for file in files:
#             gid = int(file.split('-')[0])
#             query = co.execute(f'SELECT gid FROM fav_category WHERE gid={gid} AND fav_id = 2').fetchone()
#             if query is None:
#                 logger.warning(f"sqlite no gid:{gid}, file:{file}")

# 以本地为准, 查询数据库, 判断本地是否下多了文件
# with sqlite3.connect(Config().dbs_name) as co:
#     for root, dirs, files in os.walk(r"E:\Hso\exhentaiZIP"):
#         for file in files:
#             if file.find('-') == -1:
#                 continue
#             gid = int(file.split('-')[0])
#             query = co.execute(f'SELECT gid FROM fav_category WHERE gid={gid}').fetchone()
#             if query is None:
#                 logger.warning(f"sqlite no gid:{gid}, file:{file}")

# 以数据库为准, 查找本地缺少的文件
# with sqlite3.connect(Config().dbs_name) as co:
#     gid_arr = []
#     for root, dirs, files in os.walk(r"E:\Hso\exhentaiZIP"):
#         for file in files:
#             if file.find('-') == -1:
#                 continue
#             gid = int(file.split('-')[0])
#             gid_arr.append(gid)
#     query = co.execute(f'SELECT gid FROM fav_category WHERE fav_id in (5,6,7,8,9)').fetchall()
#     print(len(query))
#     for i in query:
#         if i[0] not in gid_arr:
#             logger.warning(f"sqlite no gid:{i[0]}")
