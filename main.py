import argparse
import asyncio
import sys
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


if __name__ == "__main__":
    main()
