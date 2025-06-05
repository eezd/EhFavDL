## EH Gallery Update Strategy

If you have added a gallery with `gid=123` to your collection, and that gallery gets updated on a certain day, the new
gallery will have a different `gid`.

This creates a new issue: in this project, your old gallery and the updated gallery will coexist, as there is no way to
determine their relationship.

**Q: How can this be resolved?**  
**A:** You can run `2. Update Gallery Metadata (Update Tags)`. This will update the `current_gid` and `current_token` of
the old gallery to match the new gallery.

**Q: What should I do if a downloaded gallery has been updated?**  
**A:** First, run `2. Update Gallery Metadata (Update Tags)`, and then download the updated gallery
using `4. Download Web Gallery (News Gallery)` or `6. Download Archive Gallery (News Gallery)`.

## Docs

This project runs in two modes: Default Mode and Watch Mode.

### Watch Mode

- `python main.py -w1`
    - Update all data in the favorites
    - Update all Meta data
    - Clean up old galleries and download new galleries
    - Download galleries from `watch_fav_ids`

- `python main.py -w2`
    - Update Meta data of galleries on the first few pages of favorites, sorted by **update time** (the loop will stop
      when there are no new galleries on the current page)
    - Clean up old galleries and download new galleries
    - Download galleries from `watch_fav_ids`

- `python main.py -w3`
  - Download galleries only 
  - Suitable for situations where you've just run `w1`, but the program was interrupted due to unforeseen issues, and you don't want to spend time updating all gallery data and all meta data again.


Therefore, the `w2` mode saves a lot of time compared to `w1` because it does not need to update all Meta data through
the EH API.

However, `w2` is not without drawbacks. It cannot determine which galleries have been removed from favorites because it
does not retrieve all the favorite data.

```python
class Watch(Config):
    ...

    async def apply(self, method=1):
        ...
        if method == 1:
            await add_fav_data.post_fav_data()
            await add_fav_data.update_meta_data(True)
        elif method == 2:
            await add_fav_data.post_fav_data(url_params="?f_search=&inline_set=fs_p", get_all=False)
            await add_fav_data.update_meta_data()

        update_list = await add_fav_data.clear_del_flag()
```

### Default

```sh
$ python main.py 

2025-04-03 17:44:18.031 | INFO     | __main__:main:29 - Image Limits: 0 / 50000

1. Update User Fav Info
2. Update Gallery Metadata
3. Download Web Gallery
4. Download Web Gallery (News Gallery)
5. Update Tags Translation
6. Create ComicInfo.xml(only-folder)
7. Update ComicInfo.xml(folder&.cbz)
8. Directory To CBZ File
9. Rename CBZ File (Compatible with LANraragi)
10. Rename Gid-Name
11. Update LANraragi Tags
12. Options (Checker)...
Select Number:12

0. Return
1. Checker().check_gid_in_local_cbz()
2. Checker().sync_local_to_sqlite_cbz()
3. Checker().sync_local_to_sqlite_cbz(True)
4. Checker().check_loc_file()
(Options) Select Number:
```

- `1. Update User Fav Info`
    - Get gallery data from the favorites.
- `2. Update Gallery Metadata`
    - Update all gallery Meta data using the EH API.
- `3. Download Web Gallery`
    - Download web galleries; the files will be saved in the `$data_path$\web` folder.
- `4. Download Web Gallery (News Gallery)`
    - Move old galleries to the `$data_path$\web\del` folder, then download new galleries based on the `current_gid`
      field in the `eh_data` table.
    - Tips: Please run `2. Update Gallery Metadata (Update Tags)` first to ensure the Meta data is up-to-date.
- `5. Update Tags Translation`
    - Update tags translation data.
- `6. Create ComicInfo.xml (only-folder)`
    - Create a `ComicInfo.xml` file for folders starting with `gid-`. (Data is fetched based on `gid`.)
- `7. Update ComicInfo.xml (folder & .cbz)`
    - Unzip all `.cbz` files and folders that meet the criteria, add a `ComicInfo.xml`, and then compress them back
      into `.cbz` files. This will result in a large number of read/write operations.
- `8. Directory To CBZ File`
    - Convert folders starting with `gid-` into `cbz` files.
- `9. Rename CBZ File (Compatible with LANraragi)`
    - In `LANraragi`, if the file name is too long, it will cause errors. You can use this function to format the file
      name length.
- `10. Rename Gid-Name`
    - Rename files and folders based on the `gid` value to `title_jpn`.
- `11. Update LANraragi Tags`
    - Update LANraragi tags.
- `12. Options (Checker)...`
    - `Checker().check_gid_in_local_cbz(target_path="")`: Move duplicate `gid` CBZ files in the directory to
      the `duplicate_del` folder.
    - `Checker().sync_local_to_sqlite_cbz(cover=False, target_path="")`: Set the corresponding `original_flag`
      and `web_1280x_flag` fields based on local files.
        - `cover=True` will reset the `original_flag` and `web_1280x_flag` values in the `fav_category` table and set
          them based on local files.
    - `Checker().check_loc_file()`: Check if zip files are corrupted.

## Project Analysis

I think it's necessary to have a small section explaining some important aspects of this project to help you better
understand its logic, while also helping me organize the flow.

### Identifying Old Galleries

The simplest way is to use `AddFavData().update_meta_data(get_all=True)` to directly update all Meta data. Galleries
where `gid != current_gid` are considered old galleries.

Another shortcut approach is using `AddFavData().post_fav_data(url_params="?f_search=&inline_set=fs_p", get_all=False)`.

The page is first sorted by **update time**, and if all galleries on the current page are already in the database, it
means there are no old galleries, and the loop can be skipped. (Since no new galleries imply no old galleries either.)

If new galleries exist, `AddFavData().deep_check()` is used for a thorough check.

> `if count == 0`: This `if` condition is a safety measure to prevent excessive resource consumption.

```python
class AddFavData(Config):
    async def post_fav_data(...):
        ...
        if get_all is False:
            gid_list = [gid for gid, _ in eh_data]
            with sqlite3.connect(self.dbs_name) as co:
                query = f"SELECT COUNT(*) FROM eh_data WHERE gid IN ({','.join(['?'] * len(gid_list))})"
                count = co.execute(query, gid_list).fetchone()[0]
            if count == 0:
                logger.error("因当前页面所有画廊均为新画廊，无法进行更新。")
                logger.error("The current page has all new galleries, unable to update.")
                logger.error("Please run 2. Update Gallery Metadata >>> 1. Update User Fav Info")
                sys.exit(1)
            # 当前没有新画廊时，跳出循环
            if count == len(gid_list):
                break
            elif url_params == "?f_search=&inline_set=fs_p":
                # 按照更新时间排序 + get_all is False 时, 需要进行深度检测
                await self.deep_check(gid_token=eh_data)
```

