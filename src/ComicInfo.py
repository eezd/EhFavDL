import os.path
from datetime import datetime

from src.Utils import *


class ComicInfo(Config):

    def __init__(self):
        super().__init__()

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

    def update_meta_info(self, target_path="", only_folder=False):
        """
        更新符合条件的文件夹以及 cbz 文件的 ComicInfo 数据
        Update the ComicInfo data for eligible folders and CBZ files.
        """
        logger.info(f'update_meta_info ...')
        if target_path == "":
            target_path = self.gallery_path
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
                    create_cbz(src_path=temp_dir, target_path=file_path)
                    shutil.rmtree(temp_dir)
                    logger.info(f"update_meta_info >> {file_path}")
                progress_bar.update(1)
        logger.info(f'[OK] update_meta_info')
