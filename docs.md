## Docs

本项目运行分为两种模式, 默认模式 和 Watch 模式

### config.yaml

- `connect_limit`: 最好不要大于3, 否则容易被BAN IP
- `watch`
  - `watch_fav_ids`: watch模式下, 需要下载的收藏夹 ID
  - `watch_lan_status`: watch模式下, 是否需要更新 `LANraragi` 的元数据
  - `watch_archive_status`: watch模式下, 是否以 `archive` 方式下载

### Watch 模式

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

### 默认


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

更新Fav信息

2. Update Gallery Metadata (Update Tags)

使用 EH API 去更新 `eh_data` `tag_list` `gid_tid` 这三个表的数据

3. Download Web Gallery

下载Web画廊, 文件会下载到: `data_path\web` 文件夹下

4. Download Web Gallery (Download clear_del_flag())

`AddFavData().clear_del_flag()` 方法会返回存在更新的画廊, 然后调用 `Watch().dl_new_gallery()` 去下载画廊

5. Download Archive Gallery

使用 `GP` 点数下载, 文件会下载到: `data_path\archive` 文件夹下

6. Download Archive Gallery (Download clear_del_flag())

`AddFavData().clear_del_flag()` 方法会返回存在更新的画廊, 然后调用 `Watch().dl_new_gallery()` 去下载画廊

7. Update Tags Translation

8. Create ComicInfo.xml(only-folder)

为符合规则的文件夹创建 `ComicInfo.xml`

9. Update ComicInfo.xml(folder&.cbz)

为符合规则的文件夹以及 `.cbz` 文件创建 `ComicInfo.xml`

关于 `9. Update ComicInfo.xml(folder&.cbz)` 一定要慎重, 我之所以不添加到 `-w` 里面是因为，会造成非常巨大的写入数据。比如我现在已经下了200g的画廊，那么该方法会解压再压缩，一次循环就造成400g的写入，如果每1小时运行一次我SSD顶不住了。所以我推荐使用 LANraragi, 他不是读取 `.cbz` 的元数据，而是读取 `LANraragi` 数据库。

10. Directory To CBZ File

根据目录下的符合规则的文件夹, 创建 `cbz` 文件

11. Rename CBZ File (Compatible with LANraragi)

在 `LANraragi` 中如果你文件名称过长，它会卡住报错. 因此你需要就可以使用这个功能格式化文件名长度

12. Rename Gid-Name

根据 `gid` 重命名文件和文件夹的名称，值为 `title_jpn`。

13. Update LANraragi Tags

更新 LANraragi Tags

14. Options (Checker)...

`Checker().check_gid_in_local_cbz(target_path="")`: 移动目录下的重复 gid 的 CBZ 文件到 duplicate_del 文件夹

`Checker().sync_local_to_sqlite_cbz(cover=False, target_path="")`: 根据本地文件设置对应的 `original_flag`和 `web_1280x_flag` 字段. 

`cover=True` 会重置 fav_category 表 original_flag 和 web_1280x_flag 字段值, 根据本地文件重新设置

`Checker().check_loc_file()`: 检查zip文件是否有损坏

## Tips

在使用 `Watch` 模式的时候, 如果你需要下载的画廊过多，一次无法下载完毕。觉得第二次运行又要重新获取数据库 `tags` 以及 `fav` 的数据太耗费时间，可以跳过更新 `tags&fav` 数据。(但是你下完记得改回来，否则该模式会失效)

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