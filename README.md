# EhFavDL

[![PYTHON](https://img.shields.io/badge/Python-3.11-orange.svg)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/eezd/EhFavDL)](https://github.com/eezd/EhFavDL/releases)
[![Code size](https://img.shields.io/github/languages/code-size/eezd/EhFavDL?color=blueviolet)](https://github.com/eezd/EhFavDL)
[![Repo size](https://img.shields.io/github/repo-size/eezd/EhFavDL?color=eb56fd)](https://github.com/eezd/EhFavDL)
[![Last commit](https://img.shields.io/github/last-commit/eezd/EhFavDL/main)](https://github.com/eezd/EhFavDL/commits/main)
[![License](https://img.shields.io/badge/license-MIT-yellowgreen.svg)](LICENSE)

E-Hentai / Exhentai 下载收藏夹，基于 Python3.11 编写，支持 Komga 和 LANraragi。

[中文](README.md)/[English](README-EN.md)

**v1.2 已发布, 存在重大变化**

**v1.2 已发布, 存在重大变化**

**v1.2 已发布, 存在重大变化**

## 📌 TODO

- [x] 支持 `Sqlite` 存储
- [x] 支持通过Web下载
- [x] 支持下载原图/归档下载
- [x] 下载失败则自动重新下载
- [x] 断点续传
- [x] 生成 `ComicInfo.xml` (支持 Komga/LANraragi)
- [x] 压缩成 zip 适配 Komga/LANraragi
- [x] LANraragi 添加 EH Tags
- [ ] 根据 `IP quota` 重新计算等待时间
- [ ] 显示剩余的 `IP quota`
- [ ] 优化 **此图库有更新的版本可用** 的策略

![main](/img/main.png)

## 🔨 安装

- 1、安装环境

```bash
pip install -r requirements.txt
```

- 2、填写 `config.yaml`

```yaml
cookies:
  ipb_member_id: 1234567
  ipb_pass_hash: 123456789abcdefg
  igneous: d2fbv51sa

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36

proxy:
  enable: True
  url: http://127.0.0.1:7778

dbs_name: ./data.db

work_path: E:\Hso\exhentaiDL

#data_path: E:\Hso\exhentaiDL
data_path: E:\Hso\exhentaiDL\data

website: exhentai.org

# Only DownloadWebGallery
connect_limit: 3

lan_url: http://127.0.0.1:22299
# Setting >>> Security >>> API Key
lan_api_psw: hso+zg+134-
```

- 3、运行

```shell
python main.py
```

****

### 1. `Update User Fav Info`

**初次运行请执行这个**, 更新用户收藏夹的数据, 更新 `fav_category` 表.

![UpdateUserFavInfo](/img/UpdateUserFavInfo.png)

<br/>

### 2. `Update Gallery Metadata (Update Tags)`

使用 EH API 去更新 `eh_data` 表的数据,

<br/>

### 3. `Download Web Gallery`

下载Web画廊, 注意, 该选项会大幅度减少你的 **IP配额**.

如果是免费用户, 那么你访问画廊的数量取决于你何时用完 **IP配额**

文件会下载到: `web` 下

![DownloadWebGallery](/img/DownloadWebGallery.png)

<br/>

### 4. `Download Archive Gallery`

我推荐使用该选项下载, 他是使用你账号的 `GP` 点数下载.

如果收到 `IP quota exhausted` 请30分钟后再次下载.

文件会下载到: `archive` 下

![DownloadArchiveGallery](/img/DownloadArchiveGallery.png)

<br/>

#### 5. `Create ComicInfo.xml`

你需要确保, 你已经解压了 `*.zip` 文件

根据文件夹开头的 `GID`, 搜索数据库匹配信息, 在文件夹中创建 `ComicInfo.xml`

<br/>

### 6. `Directory To Zip File`

将文件夹压缩成 ZIP 文件

<br/>

### 7. `Rename Zip File`

在 `LANraragi` 中如果你文件名称过长，它会卡住报错. 因此你需要就可以使用这个功能格式化文件名长度

<br/>

### 8. `Update LANraragi Tags`

更新 LANraragi Tags

![UpdateLANraragiTags](/img/UpdateLANraragiTags.png)

<br/>

### 9. `Options (Checker)...`

一些选项

`Checker().check_gid_in_local_zip()`: 检查本地目录下的重复gid, 只能检查 `.zip` 文件, 支持区分 `1280x/original` 文件

`Checker().sync_local_to_sqlite_zip(cover=False)`: 据本地文件重新设置 `fav_category` 的 `original_flag`
和 `web_1280x_flag` 字段. 如果设置 `cover=True`, 那么他就会将所有状态设置成0,
在进行匹配. (`UPDATE fav_category SET original_flag=0, web_1280x_flag=0`)

`Checker().check_loc_file()`: 检查zip文件是否有损坏


****

## 使用流程

经过上面的步骤你已经完成了安装, 可能有些人还不知道该怎么用, 接下来简单说明下该如何使用.(以 LANraragi 为例子

-
    1) 首先输入 `1` + Enter 运行 `1. Update User Fav Info`

    - 获取 FAV 数据

-
    2) `3. Download Web Gallery` 或者 `4. Download Archive Gallery` 去下载画廊(`.zip`) 文件

-
    3) 请手动解压 `*.zip` 文件, 完成后并手动删除 `*.zip`

> Tips: 从这步开始, 需要你手动将(/web/folder `OR` /archive/*.zip)文件移动到 `data_path` 中.
> 并且我 **不建议** 将 `data_path` 设置为 `LANraragi-data` 数据目录, 我不确定代码中有没有其他BUG, 建议分开.

-
    4) 运行 `5. Create ComicInfo.xml`

    - 需要保持为文件夹形式, 无法识别 `*.zip`

-
    5) 运行 `6. Directory To Zip File`

-
    6) 运行 `7. Rename Zip File`

-
    7) 将你的文件移动到 `LANraragi` 对应的 `data` 文件夹下

-
    8) 打开浏览器, 进入 `LANraragi-Settings`

    - `Security---Enable Password` 设置为 `ON`
    - `Security---API Key` 设置为 `API PSW` (配合config.yaml文件中 `lan_api_psw` 字段)
    - ` Archive Files---Rescan Archive Directory` 等待完成

-
    9) 运行 `8. Update LANraragi Tags` 你就可以正常使用了

****

- 最佳用法: 现在可以使用 eh 的收藏夹来分类画廊了 `>=1.1.2`

![lan-fav](/img/lan-fav.png)

## 💡 Komga or LANraragi ？

- `Komga`
    - 1、在遇到大量文件时会卡顿（例如有 1000 个文件在本地）
    - 2、TAG 只能一行，无法像 EH 一样多个 TAG

![Komga](/img/Komga.png)

> WARNING!!
>
> LANraragi：当文件名过长可能会无法读取

- `LANraragi`
    - 1、遇到大量文件不会像 `Komga` 一样卡
    - 2、TAG 和 EH 一样

![LANraragi](/img/LANraragi.png)
