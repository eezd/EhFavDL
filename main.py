from datetime import datetime

from rich import print

from src import *

logger.add(f'./log/{datetime.today().date()}.log', rotation='10 MB',
           format="{time} {level} {message}")


def main():
    Config().create_database()

    while True:
        print("1. Add Fav Info")
        print("2. Update Fav Info")
        print("3. Download Data")
        print("4. Create ComicInfo.xml")
        print("5. To ZIP")
        print("6. Format ZIP File Name")
        print("7. LANraragi Add Tags")
        print("8. LANraragi Check PageCount")

        num = input("Select Number:")
        num = int(num) if num else None

        print('\n')

        add_fav_data = AddFavData()

        if num == 1:
            add_fav_data.update_category()
            add_fav_data.add_fav_data()
            add_fav_data.add_tags_data()
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


if __name__ == "__main__":
    main()
