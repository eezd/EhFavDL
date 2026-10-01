import ast
import asyncio
import html
import json
import os
import re
import sqlite3
import sys
from datetime import datetime

from bs4 import BeautifulSoup
from loguru import logger
from tqdm import tqdm

from src.Service import Service
from src.Utils import clear_old_file, remove_duplicates_2d_array

META_BATCH_SIZE = 25
META_RETRY = 3


class FavoritesFetchError(Exception):
    """Raised when the favorites pages cannot be read, so local state must not be synced from them."""


class AddFavData(Service):
    def __init__(self, config, database, eh_client):
        super().__init__(config, database, eh_client)

    async def translate_tags(self):
        """
        对 tag_list 表中的标签进行中文翻译
        Translate the tags in the `tag_list` table into Chinese.
        """
        logger.info(f"Downloading translation database...")
        translate_tag_url = "https://github.com/EhTagTranslation/Database/releases/latest/download/db.text.json"
        translate_tag_name = "db.text.json"
        r = await self.fetch_data(translate_tag_url)
        try:
            with open(translate_tag_name, 'wb') as f:
                f.write(r)

            with open(translate_tag_name, 'r', encoding='utf-8') as file:
                db_data = json.load(file)

            namespace_data = {}
            for item in db_data["data"]:
                namespace_data[item["namespace"]] = item["data"]

            with sqlite3.connect(self.dbs_name) as co:
                result = co.execute('''SELECT tid, tag FROM tag_list''').fetchall()
                if len(result) == 0:
                    logger.warning("The tag_list table in the database is empty.")
                    return

                updates = []
                for tid, tag in result:
                    try:
                        namespace, tagcontent = tag.split(":", 1)
                    except ValueError:
                        logger.warning(f"Invalid tag: {tag}")
                        continue
                    if namespace in namespace_data and tagcontent in namespace_data[namespace]:
                        translated_tag = namespace + ":" + namespace_data[namespace][tagcontent]["name"]
                        updates.append((translated_tag, tid))

                if updates:
                    co.executemany('''UPDATE tag_list SET translated_tag = ? WHERE tid = ?''', updates)
                    co.commit()
        finally:
            if os.path.exists(translate_tag_name):
                os.remove(translate_tag_name)

    async def update_category(self):
        logger.info(f'Get Favorite Category Name...')
        hx_res = await self.fetch_data(url=f'https://{self.base_url}/uconfig.php')
        hx_res_bs = BeautifulSoup(hx_res, 'html.parser')
        hx_res_bs = hx_res_bs.select('#favsel > div input')
        fav_category = []
        for index, i in enumerate(hx_res_bs):
            fav_category.append((index, i.get('value')))
        with sqlite3.connect(self.dbs_name) as co:
            co.executemany(
                'INSERT OR REPLACE INTO fav_name(fav_id, fav_name) VALUES (?,?)',
                fav_category,
            )
            co.commit()

    def write_meta_data(self, post_data):
        # 向数据库插入数据 / Insert data into the database.
        post_data = list(post_data)
        if len(post_data) == 0:
            return

        upsert_sql = """
        INSERT INTO eh_data (
            gid, token, title, title_jpn, category,
            thumb, uploader, posted, filecount,
            filesize, expunged, rating, current_gid, current_token
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(gid) DO UPDATE SET
            token         = excluded.token,
            title         = excluded.title,
            title_jpn     = excluded.title_jpn,
            category      = excluded.category,
            thumb         = excluded.thumb,
            uploader      = excluded.uploader,
            posted        = excluded.posted,
            filecount     = excluded.filecount,
            filesize      = excluded.filesize,
            expunged      = excluded.expunged,
            rating        = excluded.rating,
            current_gid   = excluded.current_gid,
            current_token = excluded.current_token
        ;
        """

        gid_tag_map = {}
        all_tags = set()
        upsert_rows = []
        delete_rows = []
        for item in post_data:
            gid = item.get('gid')
            tags = item.get('tags', '')
            upsert_rows.append(item.get('data'))
            delete_rows.append((gid,))
            try:
                tag_items = ast.literal_eval(tags) if tags else []
            except Exception:
                logger.warning(f"Failed to parse tags for gid={gid}")
                tag_items = []
            if isinstance(tag_items, (tuple, set)):
                tag_items = list(tag_items)
            elif not isinstance(tag_items, list):
                tag_items = [tag_items]
            gid_tag_map[gid] = tag_items
            all_tags.update(tag_items)

        with sqlite3.connect(self.dbs_name) as co:
            co.executemany(upsert_sql, upsert_rows)
            co.executemany('DELETE FROM gid_tid WHERE gid = ?', delete_rows)

            tag_id_map = {}
            if all_tags:
                tag_values = sorted(all_tags)
                placeholders = ','.join(['?'] * len(tag_values))
                result = co.execute(
                    f'''SELECT tid, tag FROM tag_list WHERE tag IN ({placeholders})''',
                    tag_values,
                ).fetchall()
                tag_id_map = {tag: tid for tid, tag in result}

                missing_tags = [(tag,) for tag in tag_values if tag not in tag_id_map]
                if missing_tags:
                    co.executemany('''INSERT OR IGNORE INTO tag_list (tag) VALUES (?)''', missing_tags)
                    result = co.execute(
                        f'''SELECT tid, tag FROM tag_list WHERE tag IN ({placeholders})''',
                        tag_values,
                    ).fetchall()
                    tag_id_map = {tag: tid for tid, tag in result}

            gid_tid_rows = []
            for gid, tag_items in gid_tag_map.items():
                for tag in tag_items:
                    tid = tag_id_map.get(tag)
                    if tid is not None:
                        gid_tid_rows.append((gid, tid))
            if gid_tid_rows:
                co.executemany('''INSERT OR IGNORE INTO gid_tid (gid, tid) VALUES (?, ?)''', gid_tid_rows)
            co.commit()

    async def post_eh_api(self, json):
        """
        Returns:[
            {
                gid: "",
                token: "",
                tags: "",
                current_gid: 0,
                current_token: ""
                parent_gid: "",
                parent_token: "",
                data: (
                    title,
                    title_jpn,
                    category,
                    thumb,
                    uploader,
                    posted,
                    filecount,
                    filesize,
                    expunged,
                    rating,
                    current_gid,
                    current_token,
                    gid
                )
            },
            ...
        ]
        """
        eh_api_data = await self.fetch_data(url="https://api.e-hentai.org/api.php", json=json)
        json_data = eh_api_data['gmetadata']
        await asyncio.sleep(0.5)
        format_data = []
        for sub_post_data in json_data:
            gid = sub_post_data['gid']
            if 'error' in sub_post_data:
                logger.warning(f"EH API error for gid={gid}: {sub_post_data['error']}")
                continue
            token = sub_post_data['token']
            expunged = sub_post_data.get('expunged')
            expunged = 0 if expunged in (False, 0) else 1
            format_data.append({
                "gid": gid,
                "token": token,
                "tags": str(sub_post_data.get('tags', '')),
                "current_gid": int(sub_post_data.get('current_gid', gid)),
                "current_token": str(sub_post_data.get('current_key', token)),
                "parent_gid": sub_post_data.get('parent_gid'),
                "parent_token": sub_post_data.get('parent_key'),
                "first_gid": sub_post_data.get('first_gid'),
                "first_token": sub_post_data.get('first_key'),
                "data": (
                    gid,
                    token,
                    html.unescape(sub_post_data.get('title', '')),
                    html.unescape(sub_post_data.get('title_jpn', '')),
                    sub_post_data.get('category', ''),
                    sub_post_data.get('thumb', ''),
                    sub_post_data.get('uploader', ''),
                    sub_post_data.get('posted', ''),
                    int(sub_post_data.get('filecount', 0)),
                    int(sub_post_data.get('filesize', 0)),
                    expunged,
                    str(sub_post_data.get('rating', '')),
                    int(sub_post_data.get('current_gid', gid)),
                    str(sub_post_data.get('current_key', token)),
                ),
            })
        return format_data

    async def update_meta_data(self, get_all=False):
        """
        默认get_all=False只更新标题为空或NULL的TAG
        The default behavior `get_all=False` only updates TAGs where the title is empty or NULL.

        以 `eh_data` 表为准, 更新字段数据及其tag( `gid_tid` & `tag_list` )
        Based on the `eh_data` table, update the field data and its tags (`gid_tid` and `tag_list`).
        """
        logger.info(f'Get Meta Data...')
        with self.database.connection() as co:
            if not get_all:
                gid_token = co.execute(
                    '''
                    SELECT gid, token
                    FROM eh_data
                    WHERE title = '' OR title IS NULL
                    '''
                ).fetchall()
            else:
                gid_token = co.execute('''SELECT gid,token FROM eh_data''').fetchall()

        targets = [list(t) for t in gid_token]
        for attempt in range(1, META_RETRY + 1):
            missing = []
            with tqdm(total=len(targets)) as progress_bar:
                for i in range(0, len(targets), META_BATCH_SIZE):
                    chunk = targets[i:i + META_BATCH_SIZE]
                    post_data = await self.post_eh_api({"method": "gdata", "gidlist": chunk, "namespace": 1})
                    self.write_meta_data(post_data)
                    returned = {item['gid'] for item in post_data}
                    missing.extend(pair for pair in chunk if pair[0] not in returned)
                    progress_bar.update(len(chunk))
            if not missing:
                return
            targets = missing
            if attempt < META_RETRY:
                logger.warning(f"Missed metadata for {len(missing)} galleries, retry in 3 seconds")
                await asyncio.sleep(3)
        logger.warning(f"Metadata unavailable after {META_RETRY} attempts: {[gid for gid, _ in missing]}")

    def format_fav_page_info(self, res):
        """
        格式化页面数据获取 gid 和 token 以及 Next_Gid
        Format page data to get gid and token and Next_Gid

        Returns: [
            [
                {'gid': gid, 'token': token, 'published_time': time, 'fav_id': fav_id},
                ...
            ],
            Next_gid
        ]
        """
        with sqlite3.connect(self.dbs_name) as co:
            query = "SELECT fav_id, fav_name FROM fav_name"
            results = co.execute(query).fetchall()
            fav_category = {fav_name: fav_id for fav_id, fav_name in results}

        search_list = res.select('.itg a[href]')
        if len(search_list) == 0:
            return [[], None]
        mylist = []

        for i in search_list:
            url = i.get('href')
            if str(url).find("/g/") == -1:
                continue
            if url is not None:
                gid = int(re.match('.*g/(.*)/(.*)/', url)[1])
                token = re.match('.*g/(.*)/(.*)/', url)[2]

                div_tag = res.find('div', id=f'posted_{gid}')
                time_text_updated = div_tag.get_text(strip=True)
                published_time = datetime.strptime(time_text_updated, "%Y-%m-%d %H:%M")

                fav_name = div_tag.get('title')
                fav_id = fav_category.get(fav_name)
                if fav_id is None:
                    logger.error(f"Can't find fav id for {fav_name}")
                    sys.exit(1)

                mylist.append({
                    'gid': gid,
                    'token': token,
                    'published_time': published_time,
                    'fav_id': fav_id
                })
        next_gid = res.select_one('a#dnext[href]')
        if next_gid is not None:
            next_gid = re.match('.*=([0-9].*)', next_gid.get('href'))[1].replace("/", "").replace(" ", "")
        mylist = remove_duplicates_2d_array(mylist)
        return [mylist, next_gid]

    def wirte_fav_data(self, data, replace_all=False):
        """
        data:{
            'eh_data': eh_data,
            'fav_category_data': fav_category_data
        }

        replace_all=True: `data` is the complete favorites list. In the same transaction, every
        fav_category row that is not in it is marked del_flag=1, so a failure leaves the database untouched.
        """
        eh_data = data['eh_data']
        fav_category_data = data['fav_category_data']
        with sqlite3.connect(self.dbs_name) as co:
            co.executemany(
                '''INSERT INTO eh_data(gid, token) VALUES (?,?)
                   ON CONFLICT(gid) DO UPDATE SET token = excluded.token''',
                eh_data,
            )
            co.executemany(
                '''INSERT INTO fav_category(gid, token, fav_id, del_flag)
                   VALUES (?,?,?,0)
                   ON CONFLICT(gid) DO UPDATE SET
                        token = excluded.token,
                        fav_id = excluded.fav_id,
                        del_flag = 0''',
                fav_category_data,
            )
            if replace_all:
                co.execute('CREATE TEMP TABLE current_favorites(gid INTEGER PRIMARY KEY)')
                co.executemany('INSERT OR IGNORE INTO current_favorites(gid) VALUES (?)',
                               [(gid,) for gid, _, _ in fav_category_data])
                co.execute('UPDATE fav_category SET del_flag = 1 WHERE gid NOT IN (SELECT gid FROM current_favorites)')
                co.execute('DROP TABLE current_favorites')
            co.commit()

    async def deep_check(self, gid_token, max_depth=4):
        """
        深度检查是否存在旧版本, 如若存在则 del_falg=1, 并且设置 current_gid 与 current_token
        """
        if max_depth == 0:
            return

        _gid_token = []
        with sqlite3.connect(self.dbs_name) as co:
            for item in gid_token:
                gid = item[0]
                token = item[1]
                status = co.execute(
                    '''
                    SELECT gid, token FROM eh_data WHERE gid = ?
                    ''', (gid,)).fetchone()
                if status is None:
                    _gid_token.append([gid, token])
            gid_token = _gid_token

            piece = 25
            gid_token = [list(t) for t in gid_token]
            gid_token = [gid_token[i:i + piece] for i in range(0, len(gid_token), piece)]
            post_json_arr = []
            for i in gid_token:
                post_json_arr.append({
                    "method": "gdata",
                    "gidlist": i,
                    "namespace": 1
                })

            gid_token = []
            update_del_rows = []
            update_current_rows = []
            for post_json in post_json_arr:
                post_data = await self.post_eh_api(post_json)
                for item in post_data:
                    current_gid = item.get('current_gid')
                    current_token = item.get('current_token')
                    parent_gid = item.get('parent_gid')
                    parent_token = item.get('parent_token')
                    if parent_gid is None:
                        continue
                    p_gid = co.execute(
                        '''
                        SELECT gid, token FROM eh_data WHERE gid = ?
                        ''', (parent_gid,)).fetchone()
                    if p_gid is None:
                        gid_token.append((parent_gid, parent_token))
                    else:
                        update_del_rows.append((p_gid[0],))
                        update_current_rows.append((current_gid, current_token, p_gid[0]))
            if update_del_rows:
                co.executemany('''UPDATE fav_category SET del_flag = 1 WHERE gid = ?''', update_del_rows)
            if update_current_rows:
                co.executemany('''UPDATE eh_data SET current_gid = ?, current_token = ? WHERE gid = ?''',
                               update_current_rows)
            co.commit()

        if len(gid_token) != 0:
            await self.deep_check(gid_token, max_depth - 1)

    async def post_fav_data(self, url_params="?f_search=&inline_set=fs_f", get_all=True):
        """
        url_params: 默认按照收藏时间排序
        ?f_search=&inline_set=fs_p / ?f_search=&inline_set=fs_f

        get_all=True: 获取所有数据
        get_all=False: 只获取新画廊(按收藏时间排序与更新时间)

        提醒下：deep_check 深度检查是依赖于网页爬取的数据(gid&token)，并不是根据数据库的数据去检查。
        如果需要根据数据库中的数据去更新画廊，需更新全部 Meta 数据
        """
        logger.info(f'Get favorite data (url_params={url_params})...')
        all_gid = []
        next_gid = 0
        instant_count = 0

        # get_all=True replaces the whole favorites list, so pages are collected first and written in a single
        # transaction at the end. Nothing is marked del_flag=1 up front: if any page cannot be read, the database
        # is left unchanged and clear_del_flag() cannot move downloaded galleries away.
        collected_eh_data = []
        collected_fav_data = []

        while True:
            if next_gid is None:
                break
            elif next_gid == 0:
                url = f'https://{self.base_url}/favorites.php{url_params}'
            else:
                url = f'https://{self.base_url}/favorites.php{url_params}&next={next_gid}'

            raw_data = await self.fetch_data(url)
            try:
                hx_res = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    hx_res = raw_data.decode('gbk')
                except UnicodeDecodeError:
                    import chardet
                    detected = chardet.detect(raw_data)
                    hx_res = raw_data.decode(detected['encoding'])

            hx_res_bs = BeautifulSoup(hx_res, 'html.parser')
            if get_all is True and hx_res_bs.select_one('#favform') is None:
                raise FavoritesFetchError(
                    f"Not a favorites list page (login, maintenance or rate-limit page?): {url}")
            search_data = self.format_fav_page_info(hx_res_bs)
            await asyncio.sleep(0.5)

            eh_data = []
            fav_category_data = []
            if len(search_data[0]) != 0:
                for item_data in search_data[0]:
                    _gid = int(item_data['gid'])
                    _token = str(item_data['token'])
                    fav_id = int(item_data['fav_id'])
                    eh_data.append((_gid, _token))
                    fav_category_data.append((_gid, _token, fav_id))
                    all_gid.append(_gid)
                    instant_count += 1
                    print("Instant count of galleries: %d\r" % instant_count, end="")

            if get_all is False:
                gid_list = [gid for gid, _ in eh_data]
                if len(gid_list) == 0:
                    next_gid = search_data[1]
                    continue
                with sqlite3.connect(self.dbs_name) as co:
                    query = f"SELECT COUNT(*) FROM eh_data WHERE gid IN ({','.join(['?'] * len(gid_list))})"
                    count = co.execute(query, gid_list).fetchone()[0]
                if count == 0:
                    logger.error("因当前页面所有画廊均为新画廊，无法进行更新。")
                    logger.error("The current page has all new galleries, unable to update.")
                    logger.error("Please run 2. Update Gallery Metadata >>> 1. Update User Fav Info")
                    sys.exit(1)
                if count == len(gid_list):
                    break
                elif url_params == "?f_search=&inline_set=fs_p":
                    await self.deep_check(gid_token=eh_data)
            if get_all is True:
                collected_eh_data.extend(eh_data)
                collected_fav_data.extend(fav_category_data)
            else:
                self.wirte_fav_data({'eh_data': eh_data, 'fav_category_data': fav_category_data})

            next_gid = search_data[1]

        if get_all is True:
            if not collected_fav_data:
                with self.database.connection() as co:
                    known = co.execute('SELECT COUNT(*) FROM fav_category').fetchone()[0]
                if known:
                    raise FavoritesFetchError(
                        f"The favorites list is empty but {known} galleries are recorded locally; "
                        "refusing to sync. Check your cookies and the favorites page.")
            self.wirte_fav_data(
                {'eh_data': collected_eh_data, 'fav_category_data': collected_fav_data}, replace_all=True)
        return all_gid

    async def clear_del_flag(self):
        """
        1. 清理 del_falg=1 并且没有下载的画廊
        2. 移动旧画廊到 `del` 目录
        3. 返回存在更新的画廊
        """
        with sqlite3.connect(self.dbs_name) as co:
            co.execute('''
            DELETE
            FROM
                fav_category
            WHERE
                del_flag = 1
                AND original_flag = 0
                AND web_1280x_flag = 0
            ''')
            co.commit()

            del_list = co.execute('''
            SELECT
                fc.gid,
                fc.token,
                eh.current_gid,
                eh.current_token
            FROM
                fav_category AS fc,
                eh_data AS eh
            WHERE
                fc.del_flag = 1
                AND fc.gid = eh.gid
                AND ( fc.original_flag = 1 OR fc.web_1280x_flag = 1 )
                AND eh.gid == eh.current_gid
                AND eh.current_gid IN ( SELECT gid FROM eh_data )
            ''').fetchall()
            clear_old_file(self.database, self.gallery_path, self.del_path, [i[0] for i in del_list])

            del_list = co.execute('''
            SELECT
                fc.gid,
                fc.token,
                eh.current_gid,
                eh.current_token
            FROM
                fav_category AS fc,
                eh_data AS eh
            WHERE
                fc.del_flag = 1
                AND fc.gid = eh.gid
                AND ( fc.original_flag = 1 OR fc.web_1280x_flag = 1 )
                AND eh.gid != eh.current_gid
                AND eh.current_gid IN ( SELECT gid FROM eh_data )
                AND eh.current_gid IN ( SELECT gid FROM fav_category WHERE del_flag = 0 AND (original_flag = 1 OR web_1280x_flag = 1) )
            ''').fetchall()
            clear_old_file(self.database, self.gallery_path, self.del_path, [i[0] for i in del_list])

            update_list = co.execute('''
            SELECT
                fc.gid,
                fc.token,
                eh.current_gid,
                eh.current_token
            FROM
                fav_category AS fc,
                eh_data AS eh
            WHERE
                fc.del_flag = 1
                AND fc.gid = eh.gid
                AND ( fc.original_flag = 1 OR fc.web_1280x_flag = 1 )
                AND eh.gid != eh.current_gid
                AND eh.current_gid IN ( SELECT gid FROM eh_data )
                AND eh.current_gid IN ( SELECT gid FROM fav_category WHERE del_flag = 0 AND original_flag = 0 AND web_1280x_flag = 0 )
                AND eh.copyright_flag = 0
            ''').fetchall()
            if len(update_list) > 0:
                logger.warning(f"下列画廊存在新版本可用/The current gallery has a new version available.: ")
                for gid_token in update_list:
                    logger.warning(
                        f"https://exhentai.org/g/{gid_token[0]}/{gid_token[1]}>>>https://exhentai.org/g/{gid_token[2]}/{gid_token[3]}")
                return update_list
            return []

    async def apply(self):
        await self.update_category()
        await self.post_fav_data()
        await self.update_meta_data()
        return await self.clear_del_flag()
