import os.path
import sys
import zipfile
from datetime import datetime
from .common import *
import httpx
import base64


class CreateConmicinfo:
    """

    """

    def __init__(self, hx, dbs_name, data_path, base_url):
        self.hx = hx
        self.dbs_name = dbs_name
        self.data_path = data_path
        self.base_url = base_url

    def zip_directory(self, directory_path, zip_file_path):
        """
        创建一个ZIP文件
        Create a ZIP file
        """
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_STORED) as zipf:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 使用os.path.relpath()获取文件相对于目录的路径
                    zipf.write(file_path, os.path.relpath(file_path, directory_path))

    def create_xml(self):
        logger.info(f'[Loading] Create ComicInfo.xml')

        # 遍历本地目录
        # traverse the local directory
        # os.makedirs(init.data_path, exist_ok=True)
        for i in os.listdir(self.data_path):
            if i.find('-') == -1 or os.path.isfile(os.path.join(self.data_path, i)):
                continue

            gid = int(str(i).split('-')[0])

            with sqlite3.connect(self.dbs_name) as co:
                co = co.execute(f'SELECT TITLE,CATEGORY,POSTED,TAGS,TOKEN FROM FAV WHERE GID="{gid}"')
                db_data = co.fetchone()
                if db_data is None:
                    logger.warning(f"不存在该ID>> {gid}")
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

    def create_zip(self):
        """
        压缩成ZIP
        """
        logger.info(f'[Loading] ZIP ...')
        for i in os.listdir(self.data_path):
            if i.find('-') == -1 or os.path.isfile(os.path.join(self.data_path, i)):
                continue

            self.zip_directory(os.path.join(self.data_path, i), os.path.join(self.data_path, i + ".zip"))
        logger.info(f'[OK] ZIP ...')

    def lan_add_tags(self):
        db_data = []
        with sqlite3.connect(self.dbs_name) as co:
            co = co.execute(f'SELECT GID,TOKEN,TITLE_JPN,POSTED,TAGS FROM FAV')
            db_data = co.fetchall()

        logger.info("请输入你的 LANraragi 地址: (http://127.0.0.1:7070)")
        logger.info("Please enter your LANraragi address")

        lan_url = input()
        if lan_url[-1] == "/":
            lan_url = lan_url + "api/archives"
        else:
            lan_url = lan_url + "/api/archives"
        # lan_url = "http://127.0.0.1:7070/api/archives"

        logger.info(f"请输入 Authorization Token")
        logger.info(f"不要输入格式为base64的, 请输入明文")
        logger.info(f"如果没有, 请创建 Setting>>> Security >>> API Key")
        logger.info(f"Please enter Authorization Token")
        logger.info(f"Do not enter the format is base64, please enter plain text")
        logger.info(f"If not, please create Setting>>> Security >>> API Key")

        authorization_token = input()

        authorization_token_base64 = str(base64.b64encode(authorization_token.encode('utf-8'))).replace("b",
                                                                                                        "").replace("'",
                                                                                                                    "")

        hx = httpx.Client(headers={"Authorization": f"Bearer {authorization_token_base64}"})

        all_archives = hx.get(lan_url)
        all_archives = all_archives.json()

        logger.info(f"一共检查到 {len(all_archives)} 个")
        logger.info(f"A total of {len(all_archives)} were checked")
        if len(all_archives) == 0:
            logger.error(f"请添加画廊后再添加Tags")
            logger.error(f"Please add gallery before adding Tags")
            sys.exit(1)

        for sub_archives in all_archives:
            gid = str(sub_archives['title']).split('-')[0]

            gid = int(gid)

            for db_tags in db_data:
                if int(db_tags[0]) == gid:
                    token = str(db_tags[1])
                    title = str(gid) + "-" + str(db_tags[2])
                    source = f"exhentai.org/g/{gid}/{token}"
                    # posted = str(datetime.datetime.fromtimestamp(int(db_tags[3]))).split(" ")[0].replace("-", "/")
                    posted = db_tags[3]

                    sub_tags = str(db_tags[4]).replace("[", "").replace("]", "").replace("'", "")

                    sub_tags = f"gid:{gid},token:{token},source:{source},date_added:{posted}," + sub_tags

                    hx.put(f"{lan_url}/{sub_archives['arcid']}/metadata",
                           data={"tags": sub_tags.strip()})

        logger.info("[OK] LANraragi Add Tags")

    def format_zip_file_name(self):
        """
        格式化ZIP文件
        Format the ZIP file, intercept the part when the length is greater than 95
        """
        logger.info(f'[Loading] Format the ZIP file ...')
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

    def apply(self):
        # self.create_xml()
        print()

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
