# EhFavDL

[![PYTHON](https://img.shields.io/badge/Python-3.9-orange.svg)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/eezd/EhFavDL)](https://github.com/eezd/EhFavDL/releases)
[![Code size](https://img.shields.io/github/languages/code-size/eezd/EhFavDL?color=blueviolet)](https://github.com/eezd/EhFavDL)
[![Repo size](https://img.shields.io/github/repo-size/eezd/EhFavDL?color=eb56fd)](https://github.com/eezd/EhFavDL)
[![Last commit](https://img.shields.io/github/last-commit/eezd/EhFavDL/main)](https://github.com/eezd/EhFavDL/commits/main)
[![License](https://img.shields.io/badge/license-MIT-yellowgreen.svg)](LICENSE)

E-Hentai / Exhentai 下载收藏夹，基于 Python3.9 编，支持 Komga 和 LANraragi。

[中文](README.md)/[English](README-EN.md)

## 📌 TODO

- [x] 支持 `Sqlite` 存储
- [x] 下载失败则自动重新下载
- [x] 生成 `ComicInfo.xml` (支持 Komga/LANraragi)
- [x] 压缩成 zip 适配 Komga/LANraragi
- [x] LANraragi 添加 EH Tags

![img-1AddFavInfo](img-1AddFavInfo.png)

![img-3DownloadData](img-3DownloadData.png)

![img-7LANraragiAddTags](img-7LANraragiAddTags.png)

## 🔨 使用

> ✏️ 如果你是使用 Pycharm 的话，请将需要在运行/调试配置中的输出控制台选项中启用“模拟终端”以查看样式的输出。

- 1、安装环境

```bash
pip install -r requirements.txt
```

- 2、填写 `config.yaml`

```yaml
cookies:
  ipb_member_id:
  ipb_pass_hash:
  igneous:

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36

proxy:
  enable: True
  url: http://127.0.0.1:7890

dbs_name: ./data.db

work_path: E:\Code\EhFavDL

data_path: E:\Code\EhFavDL\data

website: exhentai.org

connect_limit: 3

lan_url: http://127.0.0.1:7070

# Setting >>> Security >>> API Key
lan_api_psw: my-api-psw
```

- 3、运行

```shell
python main.py
```

> 🔧 接下来很重要, 请仔细阅读 🔧

1. `Add Fav Info`

**初次运行请执行这个**, 需要注意, 这个方法它不会更新字段信息(`INSERT OR IGNORE INTO`)

2. `Update Fav Info`

这个方法它会更新所有字段的信息

3. `Download Data`

下载画廊

4. `Create ComicInfo.xml`

根据文件夹开头的 `GID`, 搜索数据库匹配信息, 在文件夹中创建 `ComicInfo.xml`

5. `To ZIP`

将文件夹压缩成 ZIP 文件

6. `Format ZIP File Name`

需要注意, 在 `LANraragi` 中如果你文件名称过长，它会卡住报错. 因此你需要就可以使用这个功能格式化文件名长度.

7. `LANraragi Add Tags`

请看上面的图片

8. `LANraragi Check PageCount`

比较数据库与本地文件的页数

```python
if db_page_count > loc_page_count & abs(db_page_count - loc_page_count) > 3:
```



## 💡 Komga or LANraragi ？

- `Komga`
  - 1、在遇到大量文件时会卡顿（例如有 1000 个文件在本地）
  - 2、TAG 只能一行，无法像 EH 一样多个 TAG

![img-Komga](img-Komga.png)

> WARNING!!
>
> LANraragi：当文件名过长可能会无法读取

- `LANraragi`
  - 1、遇到大量文件不会像 `Komga` 一样卡
  - 2、TAG 和 EH 一样

![img-LANraragi](img-LANraragi.png)
