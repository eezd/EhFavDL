# EhFavDL

[![PYTHON](https://img.shields.io/badge/Python-3.9-orange.svg)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/eezd/EhFavDL)](https://github.com/eezd/EhFavDL/releases)
[![Code size](https://img.shields.io/github/languages/code-size/eezd/EhFavDL?color=blueviolet)](https://github.com/eezd/EhFavDL)
[![Repo size](https://img.shields.io/github/repo-size/eezd/EhFavDL?color=eb56fd)](https://github.com/eezd/EhFavDL)
[![Last commit](https://img.shields.io/github/last-commit/eezd/EhFavDL/main)](https://github.com/eezd/EhFavDL/commits/main)
[![License](https://img.shields.io/badge/license-MIT-yellowgreen.svg)](https://github.com/eezd/EhFavDL/blob/main/LICENSE)

E-Hentai / Exhentai 下载收藏夹，基于 Python3.9 编，支持 Komga 和 LANraragi。

[English](README-EN.md)

## 📌 TODO

- [x] 支持 `Sqlite` 存储
- [x] 下载失败则自动重新下载
- [x] 自动生成 `ComicInfo.xml` (支持 Komga/LANraragi)
- [x] 自动压缩成 zip 适配 Komga/LANraragi
- [x] LANraragi 自动添加 EH Tags

![image](https://github.com/eezd/EhFavDL/blob/main/Snipaste_2023-07-23_12-52-40.png)

![image](https://github.com/eezd/EhFavDL/blob/main/Snipaste_2023-07-23_12-53-07.png)

## 使用

> 如果你是使用 Pycharm 的话，请将需要在运行/调试配置中的输出控制台选项中启用“模拟终端”以查看样式的输出。
>
> **PyCharm** users will need to enable “emulate terminal” in output console option in run/debug configuration to see
> styled output.

- 1、安装环境

```
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
  url: http://127.0.0.1:7778

work_path: E:\Hso\myEhDL\ehNew

data_path: E:\Hso\myEhDL\ehNew\data

website: exhentai.org

connect_limit: 3
```

- 3、运行

```shell
python main.py
```

## Komga or LANraragi ？

- `Komga`
  - 1、在遇到大量文件时会卡顿（例如有 1000 个文件在本地）
  - 2、TAG 只能一行，无法像 EH 一样多个 TAG

![img-Komga](https://github.com/eezd/EhFavDL/blob/main/img-Komga.png)

> WARNING!!
>
> LANraragi：当文件名过长可能会无法读取

- `LANraragi`
  - 1、遇到大量文件不会像 `Komga` 一样卡
  - 2、TAG 和 EH 一样

![img-LANraragi](https://github.com/eezd/EhFavDL/blob/main/img-LANraragi.png)
