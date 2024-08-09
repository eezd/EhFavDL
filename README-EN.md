# EhFavDL

[![PYTHON](https://img.shields.io/badge/Python-3.11-orange.svg)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/eezd/EhFavDL)](https://github.com/eezd/EhFavDL/releases)
[![Code size](https://img.shields.io/github/languages/code-size/eezd/EhFavDL?color=blueviolet)](https://github.com/eezd/EhFavDL)
[![Repo size](https://img.shields.io/github/repo-size/eezd/EhFavDL?color=eb56fd)](https://github.com/eezd/EhFavDL)
[![Last commit](https://img.shields.io/github/last-commit/eezd/EhFavDL/main)](https://github.com/eezd/EhFavDL/commits/main)
[![License](https://img.shields.io/badge/license-MIT-yellowgreen.svg)](LICENSE)

A downloader for E-Hentai / Exhentai collections, developed in Python 3.11, with support for Komga and LANraragi.

[中文](README.md)/[English](README-EN.md)

**v1.2 has been released, featuring significant changes**

**v1.2 has been released, featuring significant changes**

**v1.2 has been released, featuring significant changes**



## 📌 TODO

- [x] Support `Sqlite` storage
- [x] Support downloading via the web
- [x] Support downloading original images/archives
- [x] Automatic retry on download failure
- [x] Resumable downloads
- [x] Generate `ComicInfo.xml` (supports Komga/LANraragi)
- [x] Zip compression for Komga/LANraragi compatibility
- [x] LANraragi tag additions
- [ ] Recalculate the waiting time based on `IP quota`
- [ ] Display the remaining `IP quota`
- [ ] Optimize the strategy for **This gallery has an updated version available**


![main](/img/main.png)



## 🔨 Installation

- 1. Install dependencies

```bash
pip install -r requirements.txt
```



- 2. Configure `config.yaml`

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



- 3. Run

```shell
python main.py
```



****



### 1. `Update User Fav Info`

**Run this initially** to update user favorites and update the `fav_category` table.

![UpdateUserFavInfo](/img/UpdateUserFavInfo.png)

<br/>

### 2. `Update Gallery Metadata (Update Tags)`

Use EH API to update data in the `eh_data` table.

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

`Checker().check_gid_in_local_zip()`: Check for duplicate GIDs in local directories, limited to `.zip` files, supporting differentiation of `1280x/original` files.

`Checker().sync_local_to_sqlite_zip(cover=False)`: Reset `original_flag` and `web_1280x_flag` fields in `fav_category` based on local files. Set `cover=True` to reset all statuses to 0 before matching. (`UPDATE fav_category SET original_flag=0, web_1280x_flag=0`)

`Checker().check_loc_file()`: Check for corrupt ZIP files.


****

## Usage Flow

After completing the installation steps, some users may need guidance on how to proceed. Here's a simple guide (using LANraragi as an example):

- 1) Enter `1` and press Enter to run `1. Update User Fav Info`

  - Retrieve FAV data

- 2) Use `3. Download Web Gallery` or `4. Download Archive Gallery` to download gallery (`.zip`) files

- 3) Manually unzip `*.zip` files, then manually delete `*.zip` after completion.

> Tips: From this step onward, you need to manually move files from (/web/folder `OR` /archive/*.zip) to `data_path`.
> It's **not recommended** to set `data_path` as the `LANraragi-data` directory. There may be bugs in the code; it's safer to keep them separate.

- 4) Run `5. Create ComicInfo.xml`

  - Must be in folder format; cannot recognize `*.zip`

- 5) Run `6. Directory To Zip File`

- 6) Run `7. Rename Zip File`

- 7) Move your files to the corresponding `data` folder in LANraragi

- 8) Open your browser, go to `LANraragi-Settings`

    - `Security---Enable Password` set to `ON`
    - `Security---API Key` set to `API PSW` (match `lan_api_psw` in config.yaml)
    - ` Archive Files---Rescan Archive Directory` and wait for completion

- 9) Run `8. Update LANraragi Tags` and you're good to go



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