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
                try:
                    response.raise_for_status()
                    all_archives = await response.json(content_type=None)
                except Exception as exc:
                    logger.error(f"Could not read the LANraragi archive list from {lan_url}: {exc}")
                    return

            if not isinstance(all_archives, list):
                logger.error(f"LANraragi did not return an archive list, check lan_url and lan_api_psw: {all_archives}")
                return

            logger.info(f"一共检查到 {len(all_archives)} 个")
            logger.info(f"A total of {len(all_archives)} were checked")
            if len(all_archives) == 0:
                logger.error(f"请添加画廊后再添加Tags")
                logger.error(f"Please add gallery before adding Tags")
                return
            failed_arcids = []

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
                        # Not an archive this tool downloaded: leave it alone instead of aborting the whole run.
                        logger.warning(
                            f"Skipping archive without a gallery id>> arcid: {str(sub_archives['arcid'])}, "
                            f"title: {str(sub_archives['title'])}")
                        progress_bar.update(1)
                        continue

                    fav_info = eh_map.get(gid)
                    fav_name = ""
                    if gid in fav_map:
                        fav_name = "fav_name:" + fav_name_map.get(fav_map[gid], "")

                    if fav_info is None:
                        logger.warning(f"The ID does not exist>> {gid}")
                        progress_bar.update(1)
                        continue

                    token = str(fav_info["token"])
                    title_jpn = fav_info["title_jpn"]
                    if self.prefer_japanese_title and title_jpn and len(str(title_jpn).strip()) > 3:
                        title = str(title_jpn)
                    else:
                        title = str(fav_info["title"])

                    source = f"exhentai.org/g/{gid}/{token}"
                    category = str(fav_info["category"])
                    posted = fav_info["posted"]
                    pagecount = sub_archives.get('pagecount')
                    pages = f"pages:{int(pagecount)}," if isinstance(pagecount, (int, float)) and pagecount > 0 else ""

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
                    lan_tags = f"gid:{gid},token:{token},source:{source},category:{category},date_added:{posted},{pages}{fav_name}," + tags

                    async with session.put(f"{lan_url}/{sub_archives['arcid']}/metadata",
                                           data={"title": title, "tags": lan_tags.strip()}) as response:
                        accepted = response.status < 400
                        try:
                            body = await response.json(content_type=None)
                            if isinstance(body, dict) and "success" in body:
                                accepted = accepted and bool(body["success"])
                        except Exception:
                            pass  # LANraragi did not answer with JSON; the HTTP status decides
                        if not accepted:
                            failed_arcids.append(str(sub_archives['arcid']))
                            logger.warning(f"LANraragi rejected the metadata for arcid {sub_archives['arcid']} "
                                           f"(HTTP {response.status}); check lan_api_psw")
                    progress_bar.update(1)

        if failed_arcids:
            logger.warning(f"LANraragi Add Tags finished with {len(failed_arcids)} failures: {failed_arcids[:10]}")
        else:
            logger.info("[OK] LANraragi Add Tags")
