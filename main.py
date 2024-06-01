from datetime import datetime

from rich import print

from src import *

logger.add(f'./log/{datetime.today().date()}.log', rotation='10 MB')


def main():
    Config().create_database()

    while True:
        print("1. Add Fav Info")
        print("2. Update Fav Tags")
        print("3. Download Data")
        print("4. Create ComicInfo.xml")
        print("5. To ZIP")
        print("6. Format ZIP File Name")
        print("7. LANraragi Add Tags")
        print("8. LANraragi Check PageCount")
        print("9. (experiment) Download Archive Gallery")

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
            DownloadFav().apply()
        elif num == 4:
            Support().create_xml()
        elif num == 5:
            Support().directory_to_zip()
        elif num == 6:
            Support().format_zip_file_name()
        elif num == 7:
            Support().lan_add_tags()
        elif num == 8:
            Support().lan_check_page_count()
        elif num == 9:
            DownloadArchiveGallery().apply()


if __name__ == "__main__":
    main()

# check = Checker()
# check.update_local_to_sqlite_status()

# with sqlite3.connect(Config().dbs_name) as co:
#     for root, dirs, files in os.walk(r"E:\Hso\exhentaiDL\data\archive"):
#         for file in files:
#             gid = int(file.split('-')[0])
#             query = co.execute(f'SELECT gid FROM fav_category WHERE gid={gid} AND fav_id = 2').fetchone()
#             if query is None:
#                 logger.warning(f"sqlite no gid:{gid}, file:{file}")
