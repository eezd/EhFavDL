import base64
import os.path
import shutil
import sqlite3
import sys
import zipfile
from datetime import datetime

import aiohttp
from loguru import logger
from tqdm import tqdm

from .Config import Config
from .common import *


class Support(Config):

    def __init__(self):
        super().__init__()

    @logger.catch()
    def create_zip(self, directory_path, zip_file_path):
        """
        创建一个ZIP文件
        Create a ZIP file
        """
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_STORED) as zipf:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 使用os.path.relpath()获取文件相对于目录的路径
                    # Using os.path.relpath() to get the file path relative to a directory.
                    zipf.write(file_path, os.path.relpath(file_path, directory_path))

    @logger.catch()
    def directory_to_zip(self):
        logger.info(f'Create ZIP ...')
        path_list = []
        for i in os.listdir(self.data_path):
            if i.find('-') == -1 or os.path.isfile(os.path.join(self.data_path, i)):
                continue
            path_list.append([os.path.join(self.data_path, i), os.path.join(self.data_path, i + ".zip")])

        logger.info(f'Total {len(path_list)}...')

        with tqdm(total=len(path_list)) as progress_bar:
            for i in path_list:
                self.create_zip(i[0], i[1])
                progress_bar.update(1)
        logger.info(f'[OK] Create ZIP')

    @logger.catch()
    def rename_zip_file(self):
        """
        重命名  (gid-name.zip) OR (gid-name-1280x.zip)  ZIP文件
        Rename the ZIP file (gid-name.zip) OR (gid-name-1280x.zip).
        """
        for i in os.listdir(self.data_path):
            if i.find('-') == -1 or os.path.isdir(os.path.join(self.data_path, i)):
                continue

            if i.find(".zip") == -1:
                continue

            new_i = i.replace(".zip", "")

            # -1280x
            web_1280x_flag = False
            if new_i.find("-1280X") != -1 or new_i.find("-1280x") != -1:
                new_i = new_i.replace("-1280x", "")
                new_i = new_i.replace("-1280X", "")
                web_1280x_flag = True

            base64_max_len = 280

            if len(str(base64.b64encode(new_i.encode('utf-8')))) > base64_max_len or len(new_i) > 114:
                while len(str(base64.b64encode(new_i.encode('utf-8')))) > base64_max_len:
                    new_i = new_i[:-1]
                if len(new_i) > 114:
                    new_i = new_i[:114]
                new_name = new_i + (".zip" if not web_1280x_flag else "-1280x.zip")
                shutil.move(os.path.join(self.data_path, i), os.path.join(self.data_path, new_name))
                logger.info(F"\nold_name: {i} \n new_name: {new_name} \n")
            elif web_1280x_flag and "-1280X" in i:
                new_name = i.replace("-1280X", "-1280x")
                shutil.move(os.path.join(self.data_path, i), os.path.join(self.data_path, new_name))
                logger.info(F"\nold_name: {i} \n new_name: {new_name} \n")

    @logger.catch()
    def create_xml(self):
        logger.info(f'[Running] Create ComicInfo.xml')

        # 遍历本地目录
        # traverse the local directory

        # os.makedirs(init.data_path, exist_ok=True)
        for i in os.listdir(self.data_path):
            if i.find('-') == -1 or os.path.isfile(os.path.join(self.data_path, i)):
                continue

            gid = int(str(i).split('-')[0])

            with sqlite3.connect(self.dbs_name) as co:
                co = co.execute(f'SELECT title,category,posted,token FROM eh_data WHERE gid="{gid}"')
                db_data = co.fetchone()
                if db_data is None:
                    logger.warning(f"The ID does not exist>> {gid}")
                    sys.exit(1)
                    
                # 获取 tid 列表 / Get tid_list
                tid_list = co.execute(f'SELECT tid FROM gid_tid WHERE gid="{gid}"').fetchall()
                tid_list = [tid[0] for tid in tid_list]
                
                # 在 tag_list 中查询对应 tag
                placeholders = ','.join(['?'] * len(tid_list))
                tag_list = co.execute(f'SELECT tag FROM tag_list WHERE tid IN ({placeholders})', tid_list).fetchall()
                db_tags = [tag[0] for tag in tag_list]
                
                xml_t = xml_escape(db_data[0])
                category = db_data[1]

                posted = str(datetime.fromtimestamp(int(db_data[2]))).split(" ")[0].split("-")

                tags = str(db_tags).replace("[", "").replace("]", "").replace("'", "").split(",")

                art = ""

                for _tags in tags:
                    if _tags.find("artist") != -1:
                        art = art + _tags.split(":")[1] + ", "

                art = art.strip()[:-1]

                tags = str(db_tags).replace("[", "").replace("]", "").replace("'", "")

            data_list = [
                r'<ComicInfo xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" encoding="utf-8">',
                r'<Manga/>',
                f'<Title>{xml_t}</Title>',
                r'<Summary/>',
                f'<Genre>{category}</Genre>',
                f'<Tags>{tags}</Tags>',
                r'<BlackAndWhite/>',
                f'<Year>{posted[0]}</Year>',
                f'<Month>{posted[1]}</Month>',
                f'<Day>{posted[2]}</Day>',
                r'<LanguageISO/>',
                f'<Writer>{art}</Writer>',
                f'<Series/>',
                r'<PageCount/>',
                r'<URL/>',
                f'<Web>exhentai.org/g/{gid}/{db_data[3]}</Web>',
                r'<Characters/>',
                r'<Translated>Yes</Translated>',
                r'</ComicInfo>',
            ]

            with open(os.path.join(self.data_path, i, "ComicInfo.xml"), 'w', encoding='utf-8') as file:
                for data in data_list:
                    file.write(data + '\n')

        logger.info(f'[OK] Create ComicInfo.xml')

    @logger.catch()
    def lan_request(self):
        logger.info("请按回车确认你的 LANraragi 地址及密码:")
        logger.info("Please press Enter to confirm your LANraragi address and password.")
        print("lan_url: " + self.lan_url)
        print("lan_api_psw: " + self.lan_api_psw)
        enter = input()
        if enter != "":
            sys.exit(1)

        authorization_token_base64 = str(base64.b64encode(self.lan_api_psw.encode('utf-8'))).replace("b",
                                                                                                     "").replace("'",
                                                                                                                 "")

        return aiohttp.ClientSession(headers={"Authorization": f"Bearer {authorization_token_base64}"})

    @logger.catch()
    async def lan_update_tags(self):
        session = self.lan_request()
        lan_url = self.lan_url

        if lan_url[-1] == "/":
            lan_url += "api/archives"
        else:
            lan_url += "/api/archives"

        async with session.get(lan_url) as response:
            all_archives = await response.json(content_type=None)

        logger.info(f"一共检查到 {len(all_archives)} 个")
        logger.info(f"A total of {len(all_archives)} were checked")
        if len(all_archives) == 0:
            logger.error(f"请添加画廊后再添加Tags")
            logger.error(f"Please add gallery before adding Tags")
            sys.exit(1)

        with tqdm(total=len(all_archives)) as progress_bar:
            with sqlite3.connect(self.dbs_name) as co:
                for sub_archives in all_archives:
                    try:
                        gid = re.compile('.*gid:([0-9]*),.*').match(str(sub_archives['tags']))
                        if gid is not None:
                            gid = int(gid.group(1))
                        else:
                            gid = int(str(sub_archives['title']).split('-')[0])
                    except ValueError:
                        logger.warning(
                            f"The ID does not exist>> arcid: {str(sub_archives['arcid'])}, title: {str(sub_archives['title'])}")
                        sys.exit(1)

                    # 根据 gid 查询数据库
                    co = co.execute(
                        f'SELECT eh.gid,eh.token,eh.title,eh.title_jpn,eh.category,eh.posted,eh.tags,fn.fav_name '
                        f'FROM eh_data AS eh, fav_category AS fc, fav_name AS fn WHERE eh.gid="{gid}" AND fc.gid="{gid}" '
                        f'AND fc.fav_id=fn.fav_id')
                    fav_info = co.fetchone()

                    # fav_category表中不存在该 gid , 则在eh_data表中查询↓↓↓
                    if fav_info is None:
                        co = co.execute(
                            f'SELECT eh.gid,eh.token,eh.title,eh.title_jpn,eh.category,eh.posted,eh.tags '
                            f'FROM eh_data AS eh WHERE eh.gid="{gid}"')
                        fav_info = co.fetchone()

                        if fav_info is None:
                            logger.warning(f"The ID does not exist>> {gid}")
                            continue
                        else:
                            fav_info = fav_info + ("no_category",)
                            logger.warning(
                                f"The data does not exist in fav_category, but it exists in eh_data. The data has been "
                                f"written.>> {gid}")

                    token = str(fav_info[1])

                    # 优先使用 title_jpn 作为标题
                    # title = str(gid) + "-" + str(fav_info[2])
                    if fav_info[3] is not None and fav_info[3] != "":
                        title = str(fav_info[3])
                    else:
                        title = str(fav_info[2])

                    source = f"exhentai.org/g/{gid}/{token}"

                    category = str(fav_info[4])

                    # posted = str(datetime.datetime.fromtimestamp(int(db_tags[3]))).split(" ")[0].replace("-", "/")
                    posted = fav_info[5]

                    # 使用 LANraragi 生成的 pages
                    # https://github.com/Difegue/LANraragi/issues/586
                    pages = int(sub_archives['pagecount'])

                    tags = str(fav_info[6]).replace("[", "").replace("]", "").replace("'", "")

                    fav_name = str(fav_info[7])

                    lan_tags = f"gid:{gid},token:{token},source:{source},category:{category},date_added:{posted},pages:{pages},fav_name:{fav_name}," + tags

                    async with session.put(f"{lan_url}/{sub_archives['arcid']}/metadata",
                                           data={"title": title, "tags": lan_tags.strip()}) as response:
                        await response.read()
                        progress_bar.update(1)

        logger.info("[OK] LANraragi Add Tags")

# <ComicInfo xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
# <Manga/>
# <Title>(C74)</Title>
# <Summary/>
# <Genre>doujinshi</Genre>
# <Tags>A,B</Tags>
# <BlackAndWhite/>
# <Year>2023</Year>
# <Month>6</Month>
# <Day>12</Day>
# <LanguageISO/>
# <Writer>ABCABC</Writer>
# <Series/>
# <PageCount/>
# <URL/>
# <Characters/>
# <Translated>Yes</Translated>
# </ComicInfo>
