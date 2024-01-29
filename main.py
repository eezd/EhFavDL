import sys
import time
import atexit
from loguru import logger
from datetime import datetime
from src import *

from rich import print

logger.add(f'./log/{datetime.today().date()}.log', rotation='10 MB',
           format="{time} {level} {message}")

start = time.time()
atexit.register(lambda: print('用时(秒):', time.time() - start))

# database file name
dbs_name = './data.db'


def dl(init):
    # 定义查询数组
    # Define query array
    dl_list = []
    with sqlite3.connect(init.dbs_name) as co:
        ce = co.execute(f'SELECT GID, TOKEN, TITLE_JPN FROM FAV WHERE STATE=0 AND BAN=0')
        co.commit()

        for i in ce.fetchall():
            dl_list.append([i[0], i[1], i[2]])

    # 开始下载
    # start download
    for j in dl_list:
        dl = DownloadImage(init.hx, init.dbs_name, init.data_path, init.connect_limit, j[0], j[1], j[2],
                           init.base_url)
        dl.apply()


def main():
    init = Init(dbs_name)
    init.apply()

    gfd = GetFavData(init.hx, init.dbs_name, init.data_path, init.base_url)

    createCon = CreateConmicinfo(init.hx, init.dbs_name, init.data_path, init.base_url)

    print("1. (Init) Update Fav Info + Download Fav")
    print("2. (Next) Update Fav Info")
    print("3. (Next) Download Fav")
    print("4. Komga/LANraragi Options")

    num = input("Select Number:")
    num = int(num) if num else None

    print('\n')

    if num == 1:
        gfd.apply()
        dl(init)

    elif num == 2:
        gfd.apply()
    elif num == 3:
        dl(init)
    elif num == 4:

        while True:
            print("Komga/LANraragi 需要每个文件夹存在 ComicInfo.xml, 然后压缩成ZIP.")
            print('因此请先输入 "1" 然后执行 "2"')
            print("Komga/LANraragi requires ComicInfo.xml to exist in each folder, and zip it..")
            print('So enter "1" and then execute "2"')

            print('[bold magenta]Tips: Folder name must be "gid-name"[/bold magenta]')
            print("1. Create ComicInfo.xml")
            print("2. ZIP")
            print("3. LANraragi Add Tags")
            print(
                "4. Format zip_file Name: [bold magenta]Tips: LANraragi cannot read files with names that are too long[/bold magenta]")
            print("0. exit()")
            sub_num = input()
            if int(sub_num) == 1:
                createCon.create_xml()
            elif int(sub_num) == 2:
                createCon.create_zip()
            elif int(sub_num) == 3:
                createCon.lan_add_tags()
            elif int(sub_num) == 4:
                createCon.format_zip_file_name()
            elif int(sub_num) == 0:
                sys.exit(1)


main()

# from PIL import Image
#
# baa = r"E:\Hso\exhentaiDL"
#
#
# def is_image_openable(image_path):
#     try:
#         with Image.open(image_path) as img:
#             return True
#     except (IOError, OSError):
#         # 图片无法打开或格式不正确
#         return False
#
#
# for i in os.listdir(baa):
#     if i.find('-') == -1 or os.path.isfile(os.path.join(baa, i)):
#         continue
#
#     for j in os.listdir(os.path.join(baa, i)):
#         if j.find("xml") != -1:
#             continue
#         # size = os.path.getsize(os.path.join(baa, i, j)) / 1024
#
#         # if size < 1:
#         #     print(os.path.join(baa, i, j))
#
#         if is_image_openable(os.path.join(baa, i, j)):
#             # print("图片可以打开。")
#             continue
#         else:
#             print(os.path.join(baa, i, j))
#             print("图片无法打开或格式不正确。")

# with sqlite3.connect(init.dbs_name) as co:
#     co = co.execute(f'SELECT PAGES FROM FAV WHERE GID="19229990"')
#     db_pages = co.fetchone()
#     if db_pages is not None:
#         db_pages = db_pages[0]
#     else:
#         db_pages = 0
#     print(db_pages)

# checkout_local_state()
