# EhFavDL

[![PYTHON](https://img.shields.io/badge/Python-3-orange.svg)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/eezd/EhFavDL)](https://github.com/eezd/EhFavDL/releases)
[![Code size](https://img.shields.io/github/languages/code-size/eezd/EhFavDL?color=blueviolet)](https://github.com/eezd/EhFavDL)
[![Repo size](https://img.shields.io/github/repo-size/eezd/EhFavDL?color=eb56fd)](https://github.com/eezd/EhFavDL)
[![Last commit](https://img.shields.io/github/last-commit/eezd/EhFavDL/main)](https://github.com/eezd/EhFavDL/commits/main)
[![License](https://img.shields.io/badge/license-MIT-yellowgreen.svg)](LICENSE)

E-Hentai / Exhentai 下载收藏夹，基于 Python 3 编写，支持 LANraragi 和 Komga。

[中文](README.md)/[English](README-EN.md)

[文档](docs.md)/[Docs English](docs-en.md)

## 📌 TODO

- [x] 支持 `Sqlite` 存储
- [x] 支持 `.cbz` 存储
- [x] 支持更新已下载的画廊
- [x] 通过Web下载(支持重新下载)
- [x] 支持中文Tag(需设置config.yaml---tags_translation)
- [x] 生成 `ComicInfo.xml` (支持 Komga/LANraragi)
- [x] 支持 `LANraragi Api` 自动更新META数据
- [x] 根据 `IP quota` 重新计算等待时间, 显示剩余 `IP quota`

## 🔨 安装

1. 安装项目

```bash
python -m pip install .
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
  enable: True
  url: http://127.0.0.1:7890

dbs_name: ./data.db

data_path: E:\Hso\exhentaiDL\data

# e-hentai.org / exhentai.org
website: exhentai.org

# Only DownloadWebGallery
connect_limit: 3

# 是否启用标签翻译
# Would you like to enable tag translation
# False / True
tags_translation: False

# ComicInfo 是否优先使用日语标题
# ComicInfo: Whether to prefer the Japanese title
# False / True
prefer_japanese_title: True

# LANraragi
lan_url: http://127.0.0.1:22299
# Setting >>> Security >>> API Key
lan_api_psw: jskada

# ehfavdl -w1 / -w2
watch_fav_ids: 0,1,2,3,4,5,6,7,8,9

# False / True
watch_lan_status: False
```

3. 运行

```shell
ehfavdl

# or

ehfavdl -w
ehfavdl -w1
ehfavdl -w2
ehfavdl -w3
```

- 最佳用法: 现在可以使用 eh 的收藏夹来分类画廊了 `>=1.1.2`

![lan-fav](/img/lan-fav.png)

# Special Thanks

- Tag translation: [Database](https://github.com/EhTagTranslation/Database)
