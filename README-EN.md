# EhFavDL

[![PYTHON](https://img.shields.io/badge/Python-3.11-orange.svg)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/eezd/EhFavDL)](https://github.com/eezd/EhFavDL/releases)
[![Code size](https://img.shields.io/github/languages/code-size/eezd/EhFavDL?color=blueviolet)](https://github.com/eezd/EhFavDL)
[![Repo size](https://img.shields.io/github/repo-size/eezd/EhFavDL?color=eb56fd)](https://github.com/eezd/EhFavDL)
[![Last commit](https://img.shields.io/github/last-commit/eezd/EhFavDL/main)](https://github.com/eezd/EhFavDL/commits/main)
[![License](https://img.shields.io/badge/license-MIT-yellowgreen.svg)](LICENSE)

A downloader for E-Hentai / Exhentai collections, developed in Python 3.11, with support for Komga and LANraragi.

[中文](README.md)/[English](README-EN.md)



## 📌 TODO

- [x] Support `Sqlite` storage
- [x] Support for downloading via Web (re-download supported)
- [x] Supports downloading the original image or a 1280x version via Archive (supports resume functionality).
- [x] Support for Chinese tags (requires setting up `config.yaml---tags_translation`)
- [x] Generate `ComicInfo.xml` (compatible with Komga/LANraragi)
- [x] Compress into zip for Komga/LANraragi compatibility
- [x] Add EH Tags in LANraragi
- [x] Recalculate waiting time based on `IP quota`
- [x] Display remaining `IP quota`
- [x] Optimize the strategy for **This gallery has an updated version available**

![main](/img/main.png)



## 🔨 Installation

- 1. Install dependencies

```bash
pip install -r requirements.txt
```



- 2. Configure `config.yaml`

```yaml
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
  url: http://127.0.0.1:7778

dbs_name: ./data.db

data_path: E:\Hso\exhentaiDL\data

# e-hentai.org / exhentai.org
website: exhentai.org

# Only DownloadWebGallery
connect_limit: 3

# Would you like to enable tag translation (applicable to 5. Create ComicInfo.xml & 8. Update LANraragi Tags)?
tags_translation: False

lan_url: http://127.0.0.1:22299
# Setting >>> Security >>> API Key
lan_api_psw: jskada
```



- 3. Run

```shell
python main.py
```



****



### 1. `Update User Fav Info`

**Run this initially** to update user favorites and update the `fav_category` table.

![UpdateUserFavInfo](/img/UpdateUserFavInfo.png)

#### Note 1

When executing `1. Update User Fav Info`, the following situation might occur:

- This indicates that there are new versions available for the following galleries:
  - In this case, you'll need to download the new gallery as instructed.
  - Then, delete the old gallery.
  - Finally, run `3. Checker().sync_local_to_sqlite_zip(True)` to reset the `original_flag` and `web_1280x_flag` fields of the old gallery to `0`.
    - The default behavior of `1. Update User Fav Info` will automatically remove galleries where `del_flag = 1 AND original_flag = 0 AND web_1280x_flag = 0`.

For more details, please refer to the code comments.

```log
Tips: The current judgment is based on eh_data.current_gid. For accurate assessment, please use `2. Update Gallery Metadata (
Update Tags)` to retrieve the data again.

The current gallery has a new version available.: 
```

Here’s the English translation of the provided Chinese text:

#### Note 2

Executing `1. Update User Fav Info` may result in the following situation.

- This means you have downloaded the gallery first.
  - Either you removed it from your favorites.
  - Or you didn’t promptly use `2. Update Gallery Metadata (Update Tags)`, which caused the failure to retrieve the new gallery's `gid&token`.

```log
The following gallery cannot determine whether a new version is available based on `eh_data.current_gid`.
If you are sure you want to remove the following gallery from the database, type ‘confirm’ (y/n).
```

<br/>

### 2. `Update Gallery Metadata (Update Tags)`

Use the EH API to update the data in the `eh_data`, `tag_list`, and `gid_tid` tables.

<br/>

### 3. `Download Web Gallery`

Downloads a web gallery. Note: this option significantly reduces your **IP quota**.

For free users, your access to galleries depends on your **IP quota**.

Files will be downloaded to: `web` directory

![DownloadWebGallery](/img/DownloadWebGallery.png)

<br/>

### 4. `Download Archive Gallery`

Recommended for downloading using your account's `GP` points.

If you encounter `IP quota exhausted`, try again after 30 minutes.

Files will be downloaded to: `archive` directory

![DownloadArchiveGallery](/img/DownloadArchiveGallery.png)

<br/>

#### 5. `Create ComicInfo.xml`

Ensure you have unpacked `*.zip` files.

Based on the folder's GID, search the database for matching information and create `ComicInfo.xml` in the folder.

<br/>

### 6. `Directory To Zip File`

Compress a folder into a ZIP file.

<br/>

### 7. `Rename Zip File`

Use this function in LANraragi if file names are too long and causing errors.

<br/>

### 8. `Update LANraragi Tags`

Update LANraragi Tags.

![UpdateLANraragiTags](/img/UpdateLANraragiTags.png)

<br/>

### 9. `Options (Checker)...`

Some options:

- `Checker().check_gid_in_local_zip()`: Checks for duplicate `gid` values in the local directory, only inspecting `.zip` files. It supports distinguishing between `1280x` and `original` files.

- `Checker().sync_local_to_sqlite_zip(cover=False)`: Sets the `original_flag` and `web_1280x_flag` fields based on local files.
  - If `cover=True` is set, all `original_flag` and `web_1280x_flag` fields are first reset to 0, and then re-set according to the local files.

- `Checker().check_loc_file()`: Checks if any `.zip` files are corrupted.



****



## Usage Flow

After following the steps above, you have completed the installation. Some of you may not yet know how to use it, so here’s a brief guide on how to get started (using LANraragi as an example):

1. First, enter `1` + Enter to run `1. Update User Fav Info` (to fetch FAV data).

2. Run `3. Download Web Gallery` or `4. Download Archive Gallery` (to download gallery `.zip` files).

3. Manually extract the `*.zip` files, and once completed, manually delete the `*.zip` files (if they exist).

> Tips: From this step onward, you need to manually move the files from (/web/folder `OR` /archive/*.zip) to the `data_path`.
> Also, I **do not recommend** setting `data_path` as the `LANraragi-data` directory. I’m not sure if there are any other bugs in the code, so it’s better to keep them separate.

4. Run `5. Create ComicInfo.xml` (make sure to keep the files in a folder format, as `*.zip` files cannot be recognized).

5. Run `6. Directory To Zip File`.

6. Run `7. Rename Zip File`.

7. Move your files to the corresponding `data` folder in `LANraragi`.

8. Open your browser and go to `LANraragi-Settings`.

- Set `Security---Enable Password` to `ON`.
- Set `Security---API Key` to `API PSW` (matching the `lan_api_psw` field in the config.yaml file).
- In `Archive Files---Rescan Archive Directory`, wait for the process to complete.

Finally, run `8. Update LANraragi Tags`, and you should be all set to use it normally.



****



- Best Practice: You can now use EH favorites to categorize galleries `>=1.1.2`

![lan-fav](/img/lan-fav.png)



## 💡 Komga or LANraragi?

- `Komga`
  - 1. Can lag with large file sets (e.g., 1000 files locally)
  - 2. TAGs limited to single line, unlike EH with multiple TAGs

![Komga](/img/Komga.png)

> WARNING!!
>
> LANraragi: May fail to read files with excessively long names

- `LANraragi`
  - 1. Handles large file sets better than `Komga`
  - 2. Supports multiple TAGs like EH

![LANraragi](/img/LANraragi.png)



# Special Thanks

- Tag translation: [Database](https://github.com/EhTagTranslation/Database)

