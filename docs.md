## EH画廊更新策略

假如你收藏了 `gid=123` 的画廊，在某一天该画廊更新了，那么新画廊的 `gid` 就不是 123了。

这样出现一个新的问题，在本项目中你的旧画廊会和新画廊共存，因为无法判断两者的关联系。

**Q: 怎么解决呢？**
A: 可以运行 `2. Update Gallery Metadata (Update Tags)`，那么旧画廊的 `current_gid` 和 `current_token` 就是新画廊的值。

**Q: 如果我下载的画廊存在更新该怎么办？**
A: 先运行 `2. Update Gallery Metadata (Update Tags)`，然后下载 `4. Download Web Gallery (News Gallery)` 或者 `6. Download Archive Gallery (News Gallery)`

## Docs

本项目运行分为两种模式, 默认模式 和 Watch 模式

### Watch 模式

- `python main.py -w1`
  - 更新收藏夹所有数据
  - 更新所有 Meta 数据
  - 清理旧画廊，下载新画廊
  - 下载 `watch_fav_ids` 的画廊

- `python main.py -w2`
  - 以 **更新时间排序** 的方式更新收藏夹前几页画廊的 Meta 数据（直至当前页面没有新画廊时会跳出循环）
  - 清理旧画廊，下载新画廊
  - 下载 `watch_fav_ids` 的画廊

- `python main.py -w3`
  - 仅下载画廊
  - 适用于刚刚执行完 `w1` ，但由于意外情况导致程序中断，不希望再花费时间去更新所有画廊数据以及所有 Meta 数据的情况。

因此，w2 方式会比 w1 节省很多时间，他并不需要通过 EH API 更新所有 Meta 数据。

w2 并不是没有缺点的，他无法判断哪些画廊被移除收藏夹了，因为他没有获取所有收藏夹数据。

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
  - 获取收藏夹画廊数据，仅
- `2. Update Gallery Metadata`
  - 使用 EH API 更新所有画廊 Meta
- `3. Download Web Gallery`
  - 下载Web画廊, 文件会下载到: `$data_path$\web` 文件夹下
- `4. Download Web Gallery (News Gallery)`
  - 移动旧画廊到 `$data_path$\web\del` 文件夹下，然后根据 `eh_data` 表中的 `current_gid` 字段下载新画廊。
  - Tips: 请先运行 `2. Update Gallery Metadata (Update Tags)` 确保 Meta 数据是最新的。
- `5. Update Tags Translation`
  - 更新Tags翻译数据
- `6. Create ComicInfo.xml(only-folder)`
  - 为 `gid-` 开头的文件夹创建 `ComicInfo.xml`。(根据 `gid` 获取数据)

- `7. Update ComicInfo.xml(folder&.cbz)`
  - 解压所有符合条件的 `.cbz` 以及 文件夹，添加 `ComicInfo.xml` 后再压缩回 `.cbz`，因此他会造成大量的 读写 操作
- `8. Directory To CBZ File`
  - 转换gid-开头的文件夹为 `cbz` 文件
- `9. Rename CBZ File (Compatible with LANraragi)`
  - 在 `LANraragi` 中如果你文件名称过长，它会卡住报错. 因此你需要就可以使用这个功能格式化文件名长度
- `10. Rename Gid-Name`
  - 根据 `gid` 重命名文件和文件夹的名称，值为 `title_jpn`。
- `11. Update LANraragi Tags`
  - 更新 LANraragi Tags
- `12. Options (Checker)...`
  - `Checker().check_gid_in_local_cbz(target_path="")`: 移动目录下的重复 gid 的 CBZ 文件到 duplicate_del 文件夹
  - `Checker().sync_local_to_sqlite_cbz(cover=False, target_path="")`: 根据本地文件设置对应的 `original_flag`和 `web_1280x_flag` 字段. 
  - `cover=True` 会重置 fav_category 表 original_flag 和 web_1280x_flag 字段值, 根据本地文件重新设置
  - `Checker().check_loc_file()`: 检查zip文件是否有损坏

## 项目解析

我认为有必要开一小节，针对本项目一些重要的地方进行讲解，帮助你更好的理解运行逻辑，同时也为我自己梳理下流程。

### 判断旧画廊

最简单的办法就是 `AddFavData().update_meta_data(get_all=True)` 直接更新所有 Meta，`gid!=current_gid` 的就是旧画廊。

还有一种取巧的办法就是 `AddFavData().post_fav_data(url_params="?f_search=&inline_set=fs_p", get_all=False)`。

页面先以 **更新时间排序**，如果当前页面的画廊全在数据库中，就意味着没有旧画廊，直接跳过循环。（因为没有新画廊那就自然没有旧画廊了）

如果存在新画廊，则交给 `AddFavData().deep_check()` 进行深度检查。

> `if count == 0`：该 if 是作为一个保险，避免资源的过度消耗。

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

