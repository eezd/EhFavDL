# EhFavDL

[![PYTHON](https://img.shields.io/badge/Python-3.9-orange.svg)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/eezd/EhFavDL)](https://github.com/eezd/EhFavDL/releases)
[![Code size](https://img.shields.io/github/languages/code-size/eezd/EhFavDL?color=blueviolet)](https://github.com/eezd/EhFavDL)
[![Repo size](https://img.shields.io/github/repo-size/eezd/EhFavDL?color=eb56fd)](https://github.com/eezd/EhFavDL)
[![Last commit](https://img.shields.io/github/last-commit/eezd/EhFavDL/main)](https://github.com/eezd/EhFavDL/commits/main)
[![License](https://img.shields.io/badge/license-MIT-yellowgreen.svg)](https://github.com/eezd/EhFavDL/blob/main/LICENSE)

E-Hentai / Exhentai Download Favorites, compiled based on Python3.9, supports Komga and LANraragi.

[Chinese](README.md)

## 📌 TODO

- [x] Support for `Sqlite` storage
- [x] If the download fails, it will automatically re-download
- [x] Automatically generate `ComicInfo.xml` (support Komga/LANraragi)
- [x] Automatically compress into zip for Komga/LANraragi
- [x] LANraragi automatically adds EH Tags

![image](https://github.com/eezd/EhFavDL/blob/main/Snipaste_2023-07-23_12-52-40.png)

![image](https://github.com/eezd/EhFavDL/blob/main/Snipaste_2023-07-23_12-53-07.png)

## use

> **PyCharm** users will need to enable “emulate terminal” in output console option in run/debug configuration to see
> styled output.

- 1、Installation Environment

```
pip install -r requirements.txt
```

- 2、fill in `config.yaml`

```yaml
cookies:
  ipb_member_id:
  ipb_pass_hash:
  igneous:

User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36

proxy:
  enable: True
  url: http://127.0.0.1:7778

work_path: E:\Hso\myEhDL\ehNew

data_path: E:\Hso\myEhDL\ehNew\data

website: exhentai.org

connect_limit: 3
```

- 3、run

```shell
python main.py
```

## Komga or LANraragi ？

- `Komga`
  - 1.  It will freeze when encountering a large number of files (for example, there are 1000 files locally)
  - 2.  TAG can only be one line, not multiple TAG like EH

![img-Komga](https://github.com/eezd/EhFavDL/blob/main/img-Komga.png)

> WARNING!!
>
> LANraragi：When the file name is too long, it may not be readable

- `LANraragi`
- 1. When encountering a large number of files, it will not be stuck like `Komga`
  - 2.  TAG is the same as EH

![img-LANraragi](https://github.com/eezd/EhFavDL/blob/main/img-LANraragi.png)
