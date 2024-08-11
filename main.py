import asyncio
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
        image_limits, total_limits = asyncio.run(Config().get_image_limits())
        logger.info(f"Image Limits: {image_limits} / {total_limits}")
        time.sleep(1)
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
            asyncio.run(add_fav_data.apply())
        elif num == 2:
            asyncio.run(add_fav_data.update_category())
            asyncio.run(add_fav_data.add_tags_data(True))
        elif num == 3:
            fav_cat = int(input("请输入你需要下载的收藏夹ID(0-9)\nPlease enter the collection you want to download.:"))

            dl_list = []
            with sqlite3.connect(Config().dbs_name) as co:
                ce = co.execute(f'''
                SELECT
                    fc.gid,
                    fc.token,
                    eh.title,
                    eh.title_jpn 
                FROM
                    eh_data AS eh,
                    fav_category AS fc 
                WHERE
                    fc.web_1280x_flag = 0 
                    AND eh.copyright_flag = 0 
                    AND eh.gid = fc.gid 
                    AND fc.fav_id = {fav_cat} 
                ORDER BY
                    fc.gid DESC
                ''').fetchall()

                for i in ce:
                    if i[3] is not None and i[3] != "":
                        title = str(i[3])
                        dl_list.append([i[0], i[1], title])
                    else:
                        title = str(i[2])
                        dl_list.append([i[0], i[1], title])

            logger.info(
                f"(fav_cat = {fav_cat}) total download list:{json.dumps(dl_list, indent=4, ensure_ascii=False)}")

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
            Support().create_xml()
        elif num == 6:
            Support().directory_to_zip()
        elif num == 7:
            Support().rename_zip_file()
        elif num == 8:
            if Config().tags_translation:
                asyncio.run(add_fav_data.translate_tags())
            asyncio.run(Support().lan_update_tags())
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
