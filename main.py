import argparse
import asyncio
import os
import shutil
import sys
import zipfile
from datetime import datetime

from src import *

logger.add(f'./log/{datetime.today().date()}.log', rotation='10 MB')

parser = argparse.ArgumentParser(description="Process some arguments.")
parser.add_argument('-w', action='store_true', help="Listen to EH Fav and fetch data every 30 minutes.")
args = parser.parse_args()


@logger.catch()
def main():
    Config().create_database()

    if args.w:
        asyncio.run(Watch().apply())

    while True:
        image_limits, total_limits = asyncio.run(Config().get_image_limits())
        logger.info(f"Image Limits: {image_limits} / {total_limits}")
        time.sleep(1)
        print("\n1. Update User Fav Info")
        print("2. Update Gallery Metadata (Update Tags)")
        print("3. Download Web Gallery")
        print("4. Download Archive Gallery")
        print("5. Update Tags Translation")
        print("6. Create ComicInfo.xml(only-folder)")
        print("7. Update ComicInfo.xml(folder&.cbz)")
        print("8. Directory To CBZ File")
        print("9. Rename CBZ File")
        print("10. Update LANraragi Tags")
        print("11. Options (Checker)...")

        num = input("Select Number:")
        num = int(num) if num else None

        print('\n')

        add_fav_data = AddFavData()

        if num == 1:
            asyncio.run(add_fav_data.apply())
        elif num == 2:
            asyncio.run(add_fav_data.update_category())
            asyncio.run(add_fav_data.add_tags_data(True))
        elif num == 3:
            fav_cat = str(input("请输入你需要下载的收藏夹ID(0-9)\nPlease enter the collection you want to download.:"))

            dl_list = get_web_gallery_download_list(fav_cat=fav_cat)

            fav_cat_check = input(f"\n(len: {len(dl_list)})Press Enter to confirm\n")

            if fav_cat_check != "":
                print("Cancel")
                sys.exit(1)

            # 开始下载
            # start download
            for j in dl_list:
                download_gallery = DownloadWebGallery(gid=j[0], token=j[1], title=j[2])
                status = asyncio.run(download_gallery.apply())
                if not status:
                    logger.warning(f"Download https://{Config().base_url}/g/{j[0]}/{j[1]} failed")
        elif num == 4:
            asyncio.run(DownloadArchiveGallery().apply())
        elif num == 5:
            if Config().tags_translation:
                asyncio.run(add_fav_data.translate_tags())
        elif num == 6:
            folder = input(f"Please enter the file directory.\n")
            if folder == "":
                print("Cancel")
                sys.exit(1)
            Support().update_meta_info(target_path=folder, only_folder=True)
        elif num == 7:
            folder = input(f"Please enter the file directory.\n")
            if folder == "":
                print("Cancel")
                sys.exit(1)
            Support().update_meta_info(target_path=folder)
        elif num == 8:
            folder = input(f"Please enter the file directory.\n")
            if folder == "":
                print("Cancel")
                sys.exit(1)
            Support().directory_to_cbz(target_path=folder)
        elif num == 9:
            folder = input(f"Please enter the file directory.\n")
            if folder == "":
                print("Cancel")
                sys.exit(1)
            Support().rename_cbz_file(target_path=folder)
        elif num == 10:
            asyncio.run(Support().lan_update_tags())
        elif num == 11:
            while True:
                print("0. Return")
                print("1. Checker().check_gid_in_local_cbz()")
                print("2. Checker().sync_local_to_sqlite_cbz()")
                print("3. Checker().sync_local_to_sqlite_cbz(True)")
                print("4. Checker().check_loc_file()")
                num = input("(Options) Select Number:")
                num = int(num) if num else None
                if num == 1:
                    folder = input(f"Please enter the file directory.\n")
                    if folder == "":
                        print("Cancel")
                        sys.exit(1)
                    Checker().check_gid_in_local_cbz(target_path=folder)
                elif num == 2:
                    folder = input(f"Please enter the file directory.\n")
                    if folder == "":
                        print("Cancel")
                        sys.exit(1)
                    Checker().sync_local_to_sqlite_cbz(target_path=folder)
                elif num == 3:
                    folder = input(f"Please enter the file directory.\n")
                    if folder == "":
                        print("Cancel")
                        sys.exit(1)
                    Checker().sync_local_to_sqlite_cbz(cover=True, target_path=folder)
                elif num == 4:
                    Checker().check_loc_file()
                elif num == 0:
                    break


# if __name__ == "__main__":
#     main()

gid = 3008265
file_path = r"E:\Code\GitHub\EhFavDL\data2\archive\3008265-[あるぷ] アモラルアイランド2 (COMIC アンスリウム 2024年8月号) [中国翻訳] [DL版].zip"
extract_to = os.path.splitext(file_path)[0]
with zipfile.ZipFile(file_path, 'r') as zip_ref:
    zip_ref.extractall(extract_to)
support = Support()
support.create_xml(gid=gid, path=extract_to)
support.create_cbz(src_path=extract_to)
support.rename_cbz_file(target_path=extract_to)
shutil.rmtree(extract_to, ignore_errors=True)
os.remove(file_path)

# asyncio.run(DownloadArchiveGallery().dl_gallery(gid=3008265, token="ef31575a5d", title="123", original_flag=False))
# download_gallery = DownloadWebGallery(gid=2855960, token="ef31575a5d", title="123")
# status = asyncio.run(download_gallery.apply())

# asyncio.run(Config().fetch_data(
#     url=f"https://fzplaay.mxodeprmrzoc.hath.network:7878/h/632691cce87d3f0adbc82e537805e9f716b8018b-361036-1280-1807-jpg/keystamp=1725262500-50f6aabdf9;fileindex=145385188;xres=1280/PG02_06.jpg",
#     tqdm_file_path="./a.jpg"))

# Checker().sync_local_to_sqlite_cbz(True)

# Support().update_meta_info()
