## Docs

This project can be run in two modes: Default Mode and Watch Mode.

### config.yaml

- `connect_limit`: It's recommended not to exceed 3, as a higher limit may lead to IP bans.
- `watch`
  - `watch_fav_ids`: In watch mode, the favorite IDs that need to be downloaded.
  - `watch_lan_status`: In watch mode, whether to update `LANraragi` metadata.
  - `watch_archive_status`: In watch mode, whether to download in `archive` mode.

### Watch Mode

```sh
$ python main.py -w

2024-09-02 19:08:11.677 | INFO     | src.Watch:apply:60 - Image Limits: 486 / 50000                       
2024-09-02 19:08:11.683 | INFO     | src.Checker:check_gid_in_local_cbz:81 - gid_list_1280x count: 0      
2024-09-02 19:08:11.686 | INFO     | src.Checker:check_gid_in_local_cbz:82 - gid_list_original count: 2   
2024-09-02 19:08:11.692 | INFO     | src.Checker:sync_local_to_sqlite_cbz:102 - gid_list_1280x count: 0   
2024-09-02 19:08:11.694 | INFO     | src.Checker:sync_local_to_sqlite_cbz:103 - gid_list_original count: 1
2024-09-02 19:08:11.708 | INFO     | src.Checker:sync_local_to_sqlite_cbz:117 - Finish sync local to sqlite. web_1280x_flag: 0, original_flag: 1
2024-09-02 19:08:11.710 | INFO     | src.Checker:sync_local_to_sqlite_cbz:118 - Finish sync local to sqlite.                                    
2024-09-02 19:08:11.714 | INFO     | src.AddFavData:add_tags_data:202 - Get EH tags...
 10%|███████████| 200/2032 [00:15<02:23, 12.73it/s]
2024-09-02 19:09:53.587 | INFO     | src.AddFavData:translate_tags:22 - Downloading translation database...
2024-09-02 19:09:58.719 | WARNING  | src.AddFavData:translate_tags:49 - Invalid tag: miyoshi shiomi
2024-09-02 19:09:58.722 | WARNING  | src.AddFavData:translate_tags:49 - Invalid tag: nyotaika
2024-09-02 19:09:58.731 | WARNING  | src.AddFavData:translate_tags:49 - Invalid tag: tawawa club
2024-09-02 19:09:58.737 | INFO     | src.AddFavData:update_category:60 - Get Favorite Category Name...
2024-09-02 19:10:00.578 | INFO     | src.AddFavData:add_fav_data:124 - Get User Favorite gid and token...
2024-09-02 19:10:00.588 | INFO     | src.AddFavData:add_fav_data:138 - Get [0th]...
2024-09-02 19:10:03.323 | INFO     | src.AddFavData:add_fav_data:178 - Switch to [1th] ...
2024-09-02 19:10:03.326 | INFO     | src.AddFavData:add_fav_data:138 - Get [1th]...
2024-09-02 19:10:05.116 | INFO     | src.AddFavData:add_fav_data:178 - Switch to [2th] ...
2024-09-02 19:10:05.118 | INFO     | src.AddFavData:add_fav_data:138 - Get [2th]...
2024-09-02 19:10:07.477 | INFO     | src.AddFavData:add_fav_data:178 - Switch to [3th] ...
2024-09-02 19:10:07.479 | INFO     | src.AddFavData:add_fav_data:138 - Get [3th]...
2024-09-02 19:10:09.217 | INFO     | src.AddFavData:add_fav_data:178 - Switch to [4th] ...
2024-09-02 19:10:09.219 | INFO     | src.AddFavData:add_fav_data:138 - Get [4th]...
2024-09-02 19:10:11.536 | INFO     | src.AddFavData:add_fav_data:178 - Switch to [5th] ...
2024-09-02 19:10:11.537 | INFO     | src.AddFavData:add_fav_data:138 - Get [5th]...
2024-09-02 19:10:13.302 | INFO     | src.AddFavData:add_fav_data:178 - Switch to [6th] ...
2024-09-02 19:10:13.303 | INFO     | src.AddFavData:add_fav_data:138 - Get [6th]...
2024-09-02 19:10:23.203 | INFO     | src.AddFavData:add_fav_data:178 - Switch to [7th] ...
2024-09-02 19:10:23.206 | INFO     | src.AddFavData:add_fav_data:138 - Get [7th]...
2024-09-02 19:10:35.248 | INFO     | src.AddFavData:add_fav_data:178 - Switch to [8th] ...
2024-09-02 19:10:35.252 | INFO     | src.AddFavData:add_fav_data:138 - Get [8th]...
2024-09-02 19:10:51.033 | INFO     | src.AddFavData:add_fav_data:178 - Switch to [9th] ...
2024-09-02 19:10:51.035 | INFO     | src.AddFavData:add_fav_data:138 - Get [9th]...
2024-09-02 19:11:08.796 | INFO     | src.AddFavData:add_fav_data:182 -  User Favorite, A Total Of: 2027...
2024-09-02 19:11:08.798 | INFO     | src.AddFavData:add_tags_data:202 - Get EH tags...
2024-09-02 19:11:10.523 | INFO     | src.Checker:sync_local_to_sqlite_cbz:102 - gid_list_1280x count: 0
2024-09-02 19:11:10.525 | INFO     | src.Checker:sync_local_to_sqlite_cbz:103 - gid_list_original count: 1
2024-09-02 19:11:10.538 | INFO     | src.Checker:sync_local_to_sqlite_cbz:117 - Finish sync local to sqlite. web_1280x_flag: 0, original_flag: 1
2024-09-02 19:11:10.539 | INFO     | src.Checker:sync_local_to_sqlite_cbz:118 - Finish sync local to sqlite.
2024-09-02 19:11:10.547 | INFO     | src.common:get_web_gallery_download_list:39 - (fav_cat = 3,4) total download list:[
    [
        3028715,
        "920ad36b4d",
        "..."
    ],
    [
        3028714,
        "8318eb330a",
        "..."
    ],
    [
        2781060,
        "2836efe17e",
        "..."
    ],
    [
        2763895,
        "05907ee0af",
        "..."
    ]
]
(len: 4)

2024-09-02 19:11:11.682 | INFO     | src.Config:wait_image_limits:288 - Image Limits: 450 / (50000*0.8 = 40000.0)
2024-09-02 19:11:11.684 | INFO     | src.DownloadWebGallery:apply:170 - Download Web Gallery...: https://exhentai.org/g/3028715/920ad36b4d/
048.jpg/00000049.jpg: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 314k/314k [00:00<00:00, 454kB/s] 
029.jpg/00000030.jpg: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 495k/495k [00:00<00:00, 614kB/s] 
019.jpg/00000020.jpg: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 441k/441k [00:00<00:00, 535kB/s] 
DownloadWebGallery>>https://exhentai.org/g/3028715/920ad36b4d/:  18%|█████████████████▎                                                                              | 9/50 [00:11<00:41,  1.02s/it]

...

2024-09-02 19:12:14.309 | INFO     | src.Support:create_xml:158 - Create ./data2\web\3028715-.../ComicInfo.xml
2024-09-02 19:12:14.705 | INFO     | src.Support:create_cbz:37 - Create CBZ: ./data2\web\3028715-...-1280x.cbz
2024-09-02 19:12:14.718 | INFO     | src.DownloadWebGallery:apply:224 - [OK] Download Web Gallery...: https://exhentai.org/g/3028715/920ad36b4d/

...

2024-09-02 19:15:15.691 | INFO     | src.Watch:watch_move_data_path:27 - Moved: ./data2\web\2763895-...-1280x.cbz -> .
/data2\2763895-...-1280x.cbz
2024-09-02 19:15:15.693 | INFO     | src.Watch:watch_move_data_path:27 - Moved: ./data2\web\2781060-...-1280x.cbz -> ./data2\27810
60-...-1280x.cbz
2024-09-02 19:15:15.695 | INFO     | src.Watch:watch_move_data_path:27 - Moved: ./data2\web\3028714-...-1280x.cbz -> ./data2\3028714-...-1280x.cbz
2024-09-02 19:15:15.698 | INFO     | src.Watch:watch_move_data_path:27 - Moved: ./data2\web\3028715-...-1280x.cbz -> ./data2\3028715-...-1280x.cbz
2024-09-02 19:15:15.699 | INFO     | src.Watch:apply:104 - Done! Wait 3600 s
```

### Default Mode


```sh
$ python main.py 

2024-09-02 18:54:31.585 | INFO     | __main__:main:24 - Image Limits: 650 / 50000

1. Update User Fav Info
2. Update Gallery Metadata (Update Tags)
3. Download Web Gallery
4. Download Web Gallery (Download clear_del_flag())
5. Download Archive Gallery
6. Download Archive Gallery (Download clear_del_flag())
7. Update Tags Translation
8. Create ComicInfo.xml(only-folder)
9. Update ComicInfo.xml(folder&.cbz)
10. Directory To CBZ File
11. Rename CBZ File (Compatible with LANraragi)
12. Rename Gid-Name
13. Update LANraragi Tags
14. Options (Checker)...

Select Number: 14

0. Return
1. Checker().check_gid_in_local_cbz()
2. Checker().sync_local_to_sqlite_cbz()
3. Checker().sync_local_to_sqlite_cbz(True)
4. Checker().check_loc_file()
(Options) Select Number:
```

1. Update User Fav Info

Update Fav information.

2. Update Gallery Metadata (Update Tags)

Use the EH API to update data in the `eh_data`, `tag_list`, and `gid_tid` tables.

3. Download Web Gallery

Download the Web gallery. Files will be saved in the `data_path\web` folder.

4. Download Web Gallery (Download clear_del_flag())

The `AddFavData().clear_del_flag()` method will return the galleries with updates, and then the `Watch().dl_new_gallery()` method will be called to download the galleries.

5. Download Archive Gallery

Use `GP` points to download. Files will be saved in the `data_path\archive` folder.

6. Download Archive Gallery (Download clear_del_flag())

The `AddFavData().clear_del_flag()` method will return the galleries with updates, and then the `Watch().dl_new_gallery()` method will be called to download the galleries.

7. Update Tags Translation

8. Create ComicInfo.xml(only-folder)

Create `ComicInfo.xml` for folders that meet the specified criteria.

9. Update ComicInfo.xml(folder&.cbz)

Create or update `ComicInfo.xml` for both folders and `.cbz` files that meet the specified criteria.

Regarding `9. Update ComicInfo.xml (folder & .cbz)`, please be very cautious. The reason I didn’t include it in `-w` is that it would result in a massive amount of data being written. For example, if I’ve already downloaded 200GB of galleries, this method would decompress and then recompress them, resulting in 400GB of write operations in a single cycle. If this runs every hour, my SSD wouldn’t be able to handle it. Therefore, I recommend using LANraragi, which doesn’t read the metadata from `.cbz` files, but instead reads from the `LANraragi` database.

10. Directory To CBZ File

Create `.cbz` files based on folders in the directory that meet the specified criteria.

11. Rename CBZ File (Compatible with LANraragi)

In `LANraragi`, if a file name is too long, it may cause the system to freeze and throw an error. Use this feature to format file names to a manageable length.

12.  Rename Gid-Name

Rename files and folders based on `gid`, with the value set to `title_jpn`.

13. Update LANraragi Tags

Update LANraragi Tags.

14. Options (Checker)...

- `Checker().check_gid_in_local_cbz(target_path="")`: Move CBZ files with duplicate GIDs in the directory to the `duplicate_del` folder.
- `Checker().sync_local_to_sqlite_cbz(cover=False, target_path="")`: Set the `original_flag` and `web_1280x_flag` fields based on local files.
- Setting `cover=True` will reset the `original_flag` and `web_1280x_flag` fields in the `fav_category` table and reassign values based on local files.
- `Checker().check_loc_file()`: Check if ZIP files are corrupted.

## Tips

When using the `Watch` mode, if there are too many galleries to download and you can't finish downloading them all at once, and you find that running it again to fetch the database `tags` and `fav` data takes too much time, you can skip updating the `tags & fav` data. (But remember to change it back after you're done, or this mode will not work properly.)

```python
class Watch(Config):
    @logger.catch
    async def apply(self):
        while True:
            ...
            add_fav_data = AddFavData()
            #await add_fav_data.add_tags_data(True)
            ...
            #update_list = await add_fav_data.apply()
            update_list = await add_fav_data.clear_del_flag()
```