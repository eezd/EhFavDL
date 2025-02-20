# EhFavDL

[![PYTHON](https://img.shields.io/badge/Python-3.11-orange.svg)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/eezd/EhFavDL)](https://github.com/eezd/EhFavDL/releases)
[![Code size](https://img.shields.io/github/languages/code-size/eezd/EhFavDL?color=blueviolet)](https://github.com/eezd/EhFavDL)
[![Repo size](https://img.shields.io/github/repo-size/eezd/EhFavDL?color=eb56fd)](https://github.com/eezd/EhFavDL)
[![Last commit](https://img.shields.io/github/last-commit/eezd/EhFavDL/main)](https://github.com/eezd/EhFavDL/commits/main)
[![License](https://img.shields.io/badge/license-MIT-yellowgreen.svg)](LICENSE)

Download favorites from E-Hentai / Exhentai, written in Python 3.11, with support for LANraragi and Komga.

[中文](README.md)/[English](README-EN.md)

[文档](docs.md)/[Docs English](docs-en.md)

## 📌 TODO

- [x]  Support for `Sqlite` storage
- [x]  Support for `.cbz` storage
- [x]  Monitor for automatic downloads and gallery updates
- [x]  Download via Web (supports re-download)
- [x]  Download original or 1280x images via Archive (supports resuming downloads)
- [x]  Support for Chinese Tags (requires configuration in `config.yaml` --- `tags_translation`)
- [x]  Generate `ComicInfo.xml` (compatible with Komga/LANraragi)
- [x]  Support for `LANraragi API` to automatically update META data
- [x]  Recalculate wait time based on `IP quota` and display remaining `IP quota`

## 🔨 Installation

1. Install dependencies

```bash
pip install -r requirements.txt
```

2. Configure `config.yaml`

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

- Best Practice: You can now use EH favorites to categorize galleries `>=1.1.2`

![lan-fav](/img/lan-fav.png)

# Special Thanks

- Tag translation: [Database](https://github.com/EhTagTranslation/Database)
