import base64
import os.path
import shutil
import sys
import zipfile
from datetime import datetime

import aiohttp
from tqdm import tqdm

from .common import *


class Support(Config):

    def __init__(self, watch_status=False):
        super().__init__()
        self.watch_status = watch_status

    @logger.catch()
    def create_cbz(self, src_path, target_path=""):
        """
        创建一个 CBZ 文件, 不传递 target_path 时默认在当前位置创建
        Create a CBZ file
        """
        if target_path == "":
            target_path = src_path + ".cbz"
        elif not target_path.endswith(".cbz"):
            target_path = target_path + ".cbz"
        with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_STORED) as cbz:
            for root, _, files in os.walk(src_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 使用os.path.relpath()获取文件相对于目录的路径
                    # Using os.path.relpath() to get the file path relative to a directory.
                    cbz.write(file_path, os.path.relpath(file_path, src_path))
        logger.info(f'Create CBZ: {target_path}')

    @logger.catch()
    def directory_to_cbz(self, target_path=""):
        """
        转换 self.data_path 下的 gid- 文件夹为CBZ文件
        Convert the "gid-" folders under self.data_path to CBZ files
        """
        logger.info(f'Create CBZ ...')
        if target_path == "":
            target_path = self.data_path
        path_list = []
        for i in os.listdir(target_path):
            if not re.match(r'^\d+-', i) or os.path.isfile(os.path.join(target_path, i)):
                continue
            path_list.append(os.path.join(target_path, i))
        logger.info(f'Total {len(path_list)}...')

        with tqdm(total=len(path_list)) as progress_bar:
            for i in path_list:
                self.create_cbz(src_path=i)
                progress_bar.update(1)
        logger.info(f'[OK] Create CBZ')

    @logger.catch()
    def rename_cbz_file(self, target_path=""):
        """
        重命名  (gid-name.cbz) OR (gid-name-1280x.cbz)  CBZ文件
        Rename the CBZ file (gid-name.cbz) OR (gid-name-1280x.cbz).

        限制文件名称最长 114位 并且转化为 base64 不超过280位
        Limit the file name to a maximum of 114 characters and ensure that its base64 encoding does not exceed 280 characters.
        """
        if target_path == "":
            target_path = self.data_path
        for i in os.listdir(target_path):
            if not re.match(r'^\d+-', i) or os.path.isdir(os.path.join(target_path, i)):
                continue
            if not i.endswith(".cbz"):
                continue
            new_i = i.replace(".cbz", "")
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
                new_name = new_i + (".cbz" if not web_1280x_flag else "-1280x.cbz")
                shutil.move(os.path.join(target_path, i), os.path.join(target_path, new_name))
                logger.info(F"\nold_name: {i} \n new_name: {new_name} \n")
            elif web_1280x_flag and "-1280X" in i:
                new_name = i.replace("-1280X", "-1280x")
                shutil.move(os.path.join(target_path, i), os.path.join(target_path, new_name))
                logger.info(F"\nold_name: {i} \n new_name: {new_name} \n")

    @logger.catch()
    def create_xml(self, gid, path):
        with sqlite3.connect(self.dbs_name) as co:
            co = co.execute(f'''SELECT title,category,posted,token FROM eh_data WHERE gid="{gid}"''')
            db_data = co.fetchone()
            if db_data is None:
                logger.warning(f"The ID does not exist>> {gid}")
                sys.exit(1)
            # 获取 tid 列表 / Get tid_list
            tid_list = co.execute(f'''SELECT tid FROM gid_tid WHERE gid="{gid}"''').fetchall()
            tid_list = [tid[0] for tid in tid_list]
            # 在 tag_list 中查询对应 tag
            placeholders = ','.join(['?'] * len(tid_list))
            tag_list = co.execute(f'''
            SELECT tag, translated_tag 
            FROM
                tag_list 
            WHERE
                tid IN ( {placeholders} )
            ''', tid_list).fetchall()
            db_tags = []
            for tag in tag_list:
                if tag[1] is not None and tag[1] != "" and self.tags_translation == True:
                    db_tags.append(tag[1])
                else:
                    db_tags.append(tag[0])
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
            f'<Web>{self.base_url}/g/{gid}/{db_data[3]}</Web>',
            r'<Characters/>',
            r'<Translated>Yes</Translated>',
            r'</ComicInfo>',
        ]
        with open(os.path.join(path, "ComicInfo.xml"), 'w', encoding='utf-8') as file:
            for data in data_list:
                file.write(data + '\n')
        logger.info(f"Create {path}/ComicInfo.xml")

    @logger.catch()
    def update_meta_info(self, target_path="", only_folder=False):
        """
        更新符合条件的文件夹以及 cbz 文件的 ComicInfo 数据
        Update the ComicInfo data for eligible folders and CBZ files.
        """
        logger.info(f'update_meta_info ...')
        if target_path == "":
            target_path = self.data_path
        path_list = []
        for i in os.listdir(target_path):
            if not re.match(r'^\d+-', i):
                continue
            if not i.endswith(".cbz") and os.path.isfile(os.path.join(target_path, i)):
                continue
            if only_folder and os.path.isfile(os.path.join(target_path, i)):
                continue
            path_list.append(os.path.join(target_path, i))
        logger.info(f'Total {len(path_list)}...')
        with tqdm(total=len(path_list)) as progress_bar:
            for file_path in path_list:
                filename = os.path.basename(file_path)
                gid = re.match(r'^(\d+)-', filename).group(1)
                if not os.path.isfile(file_path):
                    self.create_xml(gid, file_path)
                else:
                    temp_dir = file_path + '-tmp'
                    os.makedirs(temp_dir, exist_ok=True)
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    self.create_xml(gid, temp_dir)
                    self.create_cbz(src_path=temp_dir, target_path=file_path)
                    shutil.rmtree(temp_dir)
                    logger.info(f"update_meta_info >> {file_path}")
                progress_bar.update(1)
        logger.info(f'[OK] update_meta_info')

    @logger.catch()
    def lan_request(self):
        if not self.watch_status:
            logger.info("请按回车确认你的 LANraragi 地址及密码:")
            logger.info("Please press Enter to confirm your LANraragi address and password.")
            print("lan_url: " + self.lan_url)
            print("lan_api_psw: " + self.lan_api_psw)
            enter = input()
            if enter != "":
                sys.exit(1)
        authorization_token_base64 = base64.b64encode(self.lan_api_psw.encode('utf-8')).decode('utf-8')
        return authorization_token_base64

    @logger.catch()
    async def lan_update_tags(self):
        authorization_token_base64 = self.lan_request()
        headers = {"Authorization": f"Bearer {authorization_token_base64}"}

        async with aiohttp.ClientSession(headers=headers) as session:
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
                        co = co.execute(f'''
                        SELECT
                            eh.gid,
                            eh.token,
                            eh.title,
                            eh.title_jpn,
                            eh.category,
                            eh.posted,
                            fn.fav_name 
                        FROM
                            eh_data AS eh,
                            fav_category AS fc,
                            fav_name AS fn 
                        WHERE
                            eh.gid = "{gid}" 
                            AND fc.gid = "{gid}" 
                            AND fc.fav_id = fn.fav_id
                        ''')
                        fav_info = co.fetchone()

                        # fav_category表中不存在该 gid , 则在eh_data表中查询↓↓↓
                        if fav_info is None:
                            co = co.execute(f'''
                            SELECT
                                eh.gid,
                                eh.token,
                                eh.title,
                                eh.title_jpn,
                                eh.category,
                                eh.posted 
                            FROM
                                eh_data AS eh 
                            WHERE
                                eh.gid = "{gid}"
                            ''')
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

                        fav_name = ""
                        if len(fav_info) > 6:
                            fav_name = "fav_name:" + str(fav_info[6])

                        # 获取 tid 列表 / Get tid_list
                        tid_list = co.execute(f'''SELECT tid FROM gid_tid WHERE gid="{gid}"''').fetchall()
                        tid_list = [tid[0] for tid in tid_list]

                        # 在 tag_list 中查询对应 tag
                        placeholders = ','.join(['?'] * len(tid_list))
                        tag_list = co.execute(f'''
                        SELECT tag, translated_tag 
                        FROM
                            tag_list 
                        WHERE
                            tid IN ( {placeholders} )
                        ''', tid_list).fetchall()
                        db_tags = []
                        for tag in tag_list:
                            if tag[1] is not None and tag[1] != "" and self.tags_translation == True:
                                db_tags.append(tag[1])
                            else:
                                db_tags.append(tag[0])
                        tags = ','.join(db_tags)
                        lan_tags = f"gid:{gid},token:{token},source:{source},category:{category},date_added:{posted},pages:{pages},{fav_name}," + tags

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
