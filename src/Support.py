import base64
import os.path
import sys
import zipfile
from datetime import datetime

import httpx

from .Config import Config
from .common import *


class Support(Config):

    def __init__(self):
        super().__init__()

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

    def directory_to_zip(self):
        """
        压缩成ZIP
        """
        logger.info(f'[Running] ZIP ...')
        for i in os.listdir(self.data_path):
            if i.find('-') == -1 or os.path.isfile(os.path.join(self.data_path, i)):
                continue

            self.create_zip(os.path.join(self.data_path, i), os.path.join(self.data_path, i + ".zip"))
        logger.info(f'[OK] ZIP ...')

    def format_zip_file_name(self):
        """
        格式化ZIP文件
        Format the ZIP file, intercept the part when the length is greater than 95
        """
        logger.info(f'[Running] Format the ZIP file ...')
        for i in os.listdir(self.data_path):
            if i.find('-') == -1 or os.path.isdir(os.path.join(self.data_path, i)):
                continue

            if i.find(".zip") == -1:
                continue

            new_i = i.replace(".zip", "")

            if len(str(base64.b64encode(new_i.encode('utf-8')))) > 300:
                while len(str(base64.b64encode(new_i.encode('utf-8')))) > 300:
                    new_i = new_i[:-1]
                shutil.move(os.path.join(self.data_path, i), os.path.join(self.data_path, new_i + ".zip"))
                logger.info(i, ">>>>>>", new_i + ".zip")
            elif len(new_i) > 120:
                new_i = new_i[:120]
                shutil.move(os.path.join(self.data_path, i), os.path.join(self.data_path, new_i + ".zip"))
                logger.info(i, ">>>>>>", new_i + ".zip")
        logger.info(f'[OK] Format the ZIP file ...')

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
                co = co.execute(f'SELECT title,category,posted,tags,token FROM fav WHERE gid="{gid}"')
                db_data = co.fetchone()
                if db_data is None:
                    logger.warning(f"The ID does not exist>> {gid}")
                    sys.exit(1)
                xml_t = xml_escape(db_data[0])
                category = db_data[1]

                posted = str(datetime.fromtimestamp(int(db_data[2]))).split(" ")[0].split("-")

                tags = str(db_data[3]).replace("[", "").replace("]", "").replace("'", "").split(",")

                art = ""

                for _tags in tags:
                    if _tags.find("artist") != -1:
                        art = art + _tags.split(":")[1] + ", "

                art = art.strip()[:-1]

                tags = str(db_data[3]).replace("[", "").replace("]", "").replace("'", "")

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
                f'<Web>exhentai.org/g/{gid}/{db_data[4]}</Web>',
                r'<Characters/>',
                r'<Translated>Yes</Translated>',
                r'</ComicInfo>',
            ]

            with open(os.path.join(self.data_path, i, "ComicInfo.xml"), 'w', encoding='utf-8') as file:
                for data in data_list:
                    file.write(data + '\n')

        logger.info(f'[OK] Create ComicInfo.xml')

    def lan_init_request(self):
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
        return httpx.Client(headers={"Authorization": f"Bearer {authorization_token_base64}"})

    def lan_add_tags(self):
        hx = self.lan_init_request()
        lan_url = self.lan_url

        if lan_url[-1] == "/":
            lan_url += "api/archives"
        else:
            lan_url += "/api/archives"

        all_archives = hx.get(lan_url)
        all_archives = all_archives.json()

        logger.info(f"一共检查到 {len(all_archives)} 个")
        logger.info(f"A total of {len(all_archives)} were checked")
        if len(all_archives) == 0:
            logger.error(f"请添加画廊后再添加Tags")
            logger.error(f"Please add gallery before adding Tags")
            sys.exit(1)

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
                    #
                    sys.exit(1)

                co = co.execute(
                    f'SELECT f.gid,f.token,f.title,f.title_jpn,f.category,f.posted,f.pages,f.tags,fn.fav_name FROM fav AS f, fav_category AS fc, fav_name AS fn WHERE f.gid="{gid}" AND fc.gid="{gid}" AND fc.fav_id=fn.fav_id')
                fav_info = co.fetchone()

                if fav_info is None:
                    co = co.execute(
                        f'SELECT f.gid,f.token,f.title,f.title_jpn,f.category,f.posted,f.pages,f.tags FROM fav AS f WHERE f.gid="{gid}"')
                    fav_info = co.fetchone()

                    if fav_info is None:
                        logger.warning(f"The ID does not exist>> {gid}")
                        continue
                    else:
                        fav_info = fav_info + ("no_category",)
                        logger.warning(
                            f"The data does not exist in fav_category, but it exists in fav. The data has been written.>> {gid}")

                token = str(fav_info[1])

                # title = str(gid) + "-" + str(fav_info[2])
                if fav_info[3] is not None:
                    title = str(fav_info[3])
                else:
                    title = str(fav_info[2])

                source = f"exhentai.org/g/{gid}/{token}"

                category = str(fav_info[4])

                # posted = str(datetime.datetime.fromtimestamp(int(db_tags[3]))).split(" ")[0].replace("-", "/")
                posted = fav_info[5]

                pages = int(fav_info[6])

                tags = str(fav_info[7]).replace("[", "").replace("]", "").replace("'", "")

                fav_name = str(fav_info[8])

                lan_tags = f"gid:{gid},token:{token},source:{source},category:{category},date_added:{posted},pages:{pages},fav_name:{fav_name}," + tags

                hx.put(f"{lan_url}/{sub_archives['arcid']}/metadata",
                       data={"title": title, "tags": lan_tags.strip()})

        logger.info("[OK] LANraragi Add Tags")

    def lan_check_page_count(self):
        db_data = []
        with sqlite3.connect(self.dbs_name) as co:
            co = co.execute(f'SELECT gid,token,title_jpn,posted,tags,pages FROM fav')
            db_data = co.fetchall()

        hx = self.lan_init_request()
        lan_url = self.lan_url

        if lan_url[-1] == "/":
            lan_url += "api/archives"
        else:
            lan_url += "/api/archives"

        all_archives = hx.get(lan_url)
        all_archives = all_archives.json()

        logger.info(f"一共检查到 {len(all_archives)} 个")
        logger.info(f"A total of {len(all_archives)} were checked")
        if len(all_archives) == 0:
            logger.error(f"请添加画廊后再添加Tags")
            logger.error(f"Please add gallery before adding Tags")
            sys.exit(1)

        for sub_archives in all_archives:
            gid = int(str(sub_archives['title']).split('-')[0])
            loc_page_count = int(sub_archives['pagecount'])

            for db_tags in db_data:
                if int(db_tags[0]) == gid:
                    db_page_count = int(db_tags[5])
                    token = str(db_tags[1])
                    if db_page_count > loc_page_count & abs(db_page_count - loc_page_count) > 3:
                        logger.warning(
                            f"Gallery with https://{self.base_url}/g/{gid}/{token} has an incorrect number of pages. {db_page_count} != {loc_page_count}")

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
