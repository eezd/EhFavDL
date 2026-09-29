import base64
import re
import sys

import aiohttp
from loguru import logger
from tqdm import tqdm



from src.Service import Service
class LANraragi(Service):
    def __init__(self, config, database, watch_status=False):
        super().__init__(config, database)
        self.watch_status = watch_status

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

            with self.get_db_connection() as co:
                eh_rows = co.execute('''
                    SELECT gid, token, title, title_jpn, category, posted
                    FROM eh_data
                ''').fetchall()
                fav_rows = co.execute('''
                    SELECT gid, fav_id
                    FROM fav_category
                ''').fetchall()
                fav_name_rows = co.execute('''
                    SELECT fav_id, fav_name
                    FROM fav_name
                ''').fetchall()
                gid_tid_rows = co.execute('''
                    SELECT gid, tid
                    FROM gid_tid
                ''').fetchall()
                tag_rows = co.execute('''
                    SELECT tid, tag, translated_tag
                    FROM tag_list
                ''').fetchall()

            eh_map = {
                int(gid): {
                    "token": token,
                    "title": title,
                    "title_jpn": title_jpn,
                    "category": category,
                    "posted": posted,
                }
                for gid, token, title, title_jpn, category, posted in eh_rows
            }
            fav_map = {int(gid): int(fav_id) for gid, fav_id in fav_rows}
            fav_name_map = {int(fav_id): str(fav_name) for fav_id, fav_name in fav_name_rows}
            gid_tid_map = {}
            for gid, tid in gid_tid_rows:
                gid_tid_map.setdefault(int(gid), []).append(int(tid))
            tid_map = {int(tid): (tag, translated_tag) for tid, tag, translated_tag in tag_rows}

            with tqdm(total=len(all_archives)) as progress_bar:
                for sub_archives in all_archives:
                    try:
                        gid_match = re.compile('.*gid:([0-9]*),.*').match(str(sub_archives['tags']))
                        if gid_match is not None:
                            gid = int(gid_match.group(1))
                        else:
                            gid = int(str(sub_archives['title']).split('-')[0])
                    except ValueError:
                        logger.warning(
                            f"The ID does not exist>> arcid: {str(sub_archives['arcid'])}, title: {str(sub_archives['title'])}")
                        sys.exit(1)

                    fav_info = eh_map.get(gid)
                    fav_name = ""
                    if gid in fav_map:
                        fav_name = "fav_name:" + fav_name_map.get(fav_map[gid], "")

                    if fav_info is None:
                        logger.warning(f"The ID does not exist>> {gid}")
                        progress_bar.update(1)
                        continue

                    token = str(fav_info["token"])
                    if fav_info["title_jpn"] is not None and fav_info["title_jpn"] != "":
                        title = str(fav_info["title_jpn"])
                    else:
                        title = str(fav_info["title"])

                    source = f"exhentai.org/g/{gid}/{token}"
                    category = str(fav_info["category"])
                    posted = fav_info["posted"]
                    pages = int(sub_archives['pagecount'])

                    tid_list = gid_tid_map.get(gid, [])
                    db_tags = []
                    for tid in tid_list:
                        tag_info = tid_map.get(tid)
                        if tag_info is None:
                            continue
                        tag, translated_tag = tag_info
                        if translated_tag is not None and translated_tag != "" and self.tags_translation is True:
                            db_tags.append(translated_tag)
                        else:
                            db_tags.append(tag)
                    tags = ','.join(db_tags)
                    lan_tags = f"gid:{gid},token:{token},source:{source},category:{category},date_added:{posted},pages:{pages},{fav_name}," + tags

                    async with session.put(f"{lan_url}/{sub_archives['arcid']}/metadata",
                                           data={"title": title, "tags": lan_tags.strip()}) as response:
                        await response.read()
                        progress_bar.update(1)

        logger.info("[OK] LANraragi Add Tags")
