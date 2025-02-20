# EhFavDL

[![PYTHON](https://img.shields.io/badge/Python-3.11-orange.svg)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/eezd/EhFavDL)](https://github.com/eezd/EhFavDL/releases)
[![Code size](https://img.shields.io/github/languages/code-size/eezd/EhFavDL?color=blueviolet)](https://github.com/eezd/EhFavDL)
[![Repo size](https://img.shields.io/github/repo-size/eezd/EhFavDL?color=eb56fd)](https://github.com/eezd/EhFavDL)
[![Last commit](https://img.shields.io/github/last-commit/eezd/EhFavDL/main)](https://github.com/eezd/EhFavDL/commits/main)
[![License](https://img.shields.io/badge/license-MIT-yellowgreen.svg)](LICENSE)

E-Hentai / Exhentai 下载收藏夹，基于 Python3.11 编写，支持 LANraragi 和 Komga。

[中文](README.md)/[English](README-EN.md)

[文档](docs.md)/[Docs English](docs-en.md)

## 📌 TODO

- [x] 支持 `Sqlite` 存储
- [x] 支持 `.cbz` 存储
- [x] 监听自动下载并更新画廊
- [x] 通过Web下载(支持重新下载)
- [x] 通过Archive下载原图或1280x(支持断点续传)
- [x] 支持中文Tag(需设置config.yaml---tags_translation)
- [x] 生成 `ComicInfo.xml` (支持 Komga/LANraragi)
- [x] 支持 `LANraragi Api` 自动更新META数据
- [x] 根据 `IP quota` 重新计算等待时间, 显示剩余 `IP quota`

## 🔨 安装

1. 安装环境

```bash
pip install -r requirements.txt
```

2. 填写 `config.yaml`

```yaml
# 缺少 sk 和 hath_perks 会导致无法获取正确的 IP 配额
# Missing sk and hath_perks will result in the inability to obtain the correct IP quota.
cookies:
  ipb_member_id: 1234567
  ipb_pass_hash: 123456789abcdefg
  igneous: d2fbv51sa
  sk: asdjnasdjk
  hath_perks: m1.m2...

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36

proxy:
  # False / True
  enable: True
  url: http://127.0.0.1:7890

dbs_name: ./data.db

data_path: E:\Hso\exhentaiDL\data

# e-hentai.org / exhentai.org
website: exhentai.org

# Only DownloadWebGallery
connect_limit: 3

# 是否启用标签翻译(适用于 5. Create ComicInfo.xml & 8. Update LANraragi Tags)
# Would you like to enable tag translation (applicable to 5. Create ComicInfo.xml & 8. Update LANraragi Tags)?
# False / True
tags_translation: False

# LANraragi
lan_url: http://127.0.0.1:22299
# Setting >>> Security >>> API Key
lan_api_psw: jskada

# python main.py -w2
# watch_fav_ids: 3,4
watch_fav_ids:
# python main.py -w1 和 -w2
# watch_download_fav_ids: 3,4
watch_download_fav_ids: # 为空表示全部下载
# False / True
watch_lan_status: False
# False / True
watch_archive_status: False
```

3. Run

```shell
python main.py

# or

python main.py -w
```

- 最佳用法: 现在可以使用 eh 的收藏夹来分类画廊了 `>=1.1.2`

![lan-fav](/img/lan-fav.png)

# Special Thanks

- Tag translation: [Database](https://github.com/EhTagTranslation/Database)
