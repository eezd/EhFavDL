import argparse
import asyncio
import sys


def build_parser():
    parser = argparse.ArgumentParser(description="Download E-Hentai and ExHentai favorites.")
    parser.add_argument('-w', action='store_true',
                        help="Listen to EH Fav and fetch data every 60 minutes with default watcher 1.")
    parser.add_argument('-w1', action='store_true', help="Listen to EH Fav and fetch data every 60 minutes with watcher 1.")
    parser.add_argument('-w2', action='store_true', help="Listen to EH Fav and fetch data every 60 minutes with watcher 2.")
    parser.add_argument('-w3', action='store_true', help="Listen to EH Fav and fetch data every 60 minutes with watcher 3.")
    return parser


async def run(args):
    from loguru import logger

    from src.AddFavData import AddFavData, FavoritesFetchError
    from src.AppConfig import AppConfig
    from src.Checker import Checker
    from src.ComicInfo import ComicInfo
    from src.Database import Database
    from src.DownloadWebGallery import DownloadStatus, DownloadWebGallery
    from src.EhClient import EhClient
    from src.ImageQuota import ImageQuota
    from src.LANraragi import LANraragi
    from src.Utils import (
        directory_to_cbz,
        get_web_gallery_download_list,
        rename_cbz_file,
        rename_gid_name,
    )
    from src.Watch import Watch

    config = AppConfig.load()
    database = Database(config.dbs_name)
    database.initialize()

    async with EhClient(config) as eh_client:
        quota = ImageQuota(eh_client)
        add_fav_data = AddFavData(config, database, eh_client)
        checker = Checker(config, database)
        comic_info = ComicInfo(config, database)
        watch = Watch(config, database, eh_client, quota)
        try:
            if args.w or args.w1:
                await watch.apply(1)
            elif args.w2:
                await watch.apply(2)
            elif args.w3:
                await watch.apply(3)

            while True:
                image_limits, total_limits = await quota.get_limits()
                logger.info(f"Image Limits: {image_limits} / {total_limits}")
                await asyncio.sleep(1)
                print("\n1. Update User Fav Info")
                print("2. Update Gallery Metadata")
                print("3. Download Web Gallery")
                print("4. Download Web Gallery (News Gallery)")
                print("5. Update Tags Translation")
                print("6. Create ComicInfo.xml(only-folder)")
                print("7. Update ComicInfo.xml(folder&.cbz)")
                print("8. Directory To CBZ File")
                print("9. Rename CBZ File (Compatible with LANraragi)")
                print("10. Rename Gid-Name")
                print("11. Update LANraragi Tags")
                print("12. Options (Checker)...")

                num = input("Select Number:")
                num = int(num) if num else None
                print("\n")
                if num == 1:
                    try:
                        await add_fav_data.apply()
                    except FavoritesFetchError as exc:
                        logger.error(f"Favorites were not updated, local galleries are untouched: {exc}")
                elif num == 2:
                    await add_fav_data.update_category()
                    await add_fav_data.update_meta_data(True)
                elif num == 3:
                    fav_cat = str(input("请输入你需要下载的收藏夹ID(0-9)\nPlease enter the collection you want to download.:"))
                    dl_list = get_web_gallery_download_list(database, fav_cat=fav_cat)
                    if input(f"\n(len: {len(dl_list)})Press Enter to confirm\n") != "":
                        sys.exit(1)
                    for gid, token, title in dl_list:
                        status = await DownloadWebGallery(config, database, eh_client, quota, gid, token, title).apply()
                        if status is DownloadStatus.COPYRIGHT_BLOCKED:
                            logger.warning(
                                f"Skipped copyright-blocked gallery: "
                                f"https://{config.base_url}/g/{gid}/{token}"
                            )
                        elif status is not DownloadStatus.SUCCESS:
                            logger.warning(f"Download https://{config.base_url}/g/{gid}/{token} failed")
                elif num == 4:
                    update_list = await add_fav_data.clear_del_flag()
                    current_gids = [item[2] for item in update_list]
                    # The old version is moved by clear_del_flag() below, only once the new one is downloaded.
                    if not await watch.dl_new_gallery(gids=",".join(map(str, current_gids))):
                        logger.warning("Some galleries failed to download; run option 4 again later.")
                    await add_fav_data.clear_del_flag()
                elif num == 5:
                    if config.tags_translation:
                        await add_fav_data.translate_tags()
                elif num == 6:
                    folder = input("Please enter the file directory.\n")
                    if not folder:
                        sys.exit(1)
                    comic_info.update_meta_info(target_path=folder, only_folder=True)
                elif num == 7:
                    folder = input("Please enter the file directory.\n")
                    if not folder:
                        sys.exit(1)
                    comic_info.update_meta_info(target_path=folder)
                elif num == 8:
                    folder = input("Please enter the file directory.\n")
                    if not folder:
                        sys.exit(1)
                    directory_to_cbz(folder)
                elif num == 9:
                    folder = input("Please enter the file directory.\n")
                    if not folder:
                        sys.exit(1)
                    rename_cbz_file(folder)
                elif num == 10:
                    folder = input("Please enter the file directory.\n")
                    if not folder:
                        sys.exit(1)
                    rename_gid_name(database, folder)
                elif num == 11:
                    await LANraragi(config, database).lan_update_tags()
                elif num == 12:
                    while True:
                        print("0. Return")
                        print("1. Checker().check_gid_in_local_cbz()")
                        print("2. Checker().sync_local_to_sqlite_cbz()")
                        print("3. Checker().sync_local_to_sqlite_cbz(True)")
                        print("4. Checker().check_loc_file()")
                        print("5. Checker().clear_old_file()")
                        sub_num = input("(Options) Select Number:")
                        sub_num = int(sub_num) if sub_num else None
                        if sub_num == 1:
                            checker.check_gid_in_local_cbz(input("Please enter the file directory.\n"))
                        elif sub_num == 2:
                            checker.sync_local_to_sqlite_cbz(target_path=input("Please enter the file directory.\n"))
                        elif sub_num == 3:
                            checker.sync_local_to_sqlite_cbz(cover=True, target_path=input("Please enter the file directory.\n"))
                        elif sub_num == 4:
                            checker.check_loc_file()
                        elif sub_num == 5:
                            checker.clear_old_file(target_path=input("Please enter the file directory.\n"))
                        elif sub_num == 0:
                            break
        finally:
            await eh_client.close()


def cli():
    args = build_parser().parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    cli()
