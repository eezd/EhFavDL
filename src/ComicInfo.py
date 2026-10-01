import os.path
import re
import shutil
import sqlite3
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime

from loguru import logger
from tqdm import tqdm

from src.Service import Service
from src.Utils import create_cbz

XML_INVALID_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
COMICINFO_NAMESPACES = {
    "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


class ComicInfo(Service):
    def __init__(self, config, database):
        super().__init__(config, database)

    def create_xml(self, gid, path):
        with sqlite3.connect(self.dbs_name) as co:
            db_data = co.execute(
                '''SELECT title, title_jpn, category, posted, token FROM eh_data WHERE gid = ?''',
                (gid,),
            ).fetchone()
            if db_data is None:
                logger.warning(f"The ID does not exist>> {gid}")
                sys.exit(1)
            # 获取 tid 列表 / Get tid_list
            tid_rows = co.execute(
                '''SELECT tid FROM gid_tid WHERE gid = ?''',
                (gid,),
            ).fetchall()
            tid_list = [tid[0] for tid in tid_rows]
            db_tags = []
            if tid_list:
                placeholders = ','.join(['?'] * len(tid_list))
                tag_list = co.execute(
                    f'''
                    SELECT tag, translated_tag
                    FROM tag_list
                    WHERE tid IN ({placeholders})
                    ''',
                    tid_list,
                ).fetchall()
                for tag, translated_tag in tag_list:
                    if self.tags_translation and translated_tag is not None and translated_tag != "":
                        db_tags.append(translated_tag)
                    else:
                        db_tags.append(tag)
            if self.prefer_japanese_title and db_data[1] is not None and db_data[1] != "" and len(str(db_data[1]).strip()) > 3:
                title = str(db_data[1])
            else:
                title = str(db_data[0])
            logger.debug(f"ComicInfo title: {title}")
            category = db_data[2]
            posted = datetime.fromtimestamp(int(db_data[3])).strftime("%Y-%m-%d").split("-")
            art = ", ".join(
                tag.split(":", 1)[1]
                for tag in db_tags
                if tag.startswith("artist:") and ":" in tag
            )
            tags = ", ".join(db_tags)
        fields = [
            ("Manga", None),
            ("Title", title),
            ("Summary", None),
            ("Genre", category),
            ("Tags", tags),
            ("BlackAndWhite", None),
            ("Year", posted[0]),
            ("Month", posted[1]),
            ("Day", posted[2]),
            ("LanguageISO", None),
            ("Writer", art),
            ("Series", None),
            ("PageCount", None),
            ("URL", None),
            ("Web", f"{self.base_url}/g/{gid}/{db_data[4]}"),
            ("Characters", None),
            ("Translated", "Yes"),
        ]
        root = ET.Element("ComicInfo", COMICINFO_NAMESPACES)
        for name, value in fields:
            ET.SubElement(root, name).text = XML_INVALID_CHARS.sub("", str(value)) if value else None
        ET.indent(root)
        ET.ElementTree(root).write(os.path.join(path, "ComicInfo.xml"), encoding="utf-8", xml_declaration=True)
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
                    try:
                        os.makedirs(temp_dir, exist_ok=True)
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                            zip_ref.extractall(temp_dir)
                        self.create_xml(gid, temp_dir)
                        create_cbz(src_path=temp_dir, target_path=file_path)
                        logger.info(f"update_meta_info >> {file_path}")
                    except (OSError, zipfile.BadZipFile) as exc:
                        # create_cbz replaces the CBZ only after writing it completely, so the original is untouched.
                        logger.error(f"update_meta_info failed for {file_path}: {exc}")
                    finally:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                progress_bar.update(1)
        logger.info(f'[OK] update_meta_info')
