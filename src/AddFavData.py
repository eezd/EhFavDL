import ast
import asyncio

from bs4 import BeautifulSoup

from src.Utils import *


class AddFavData(Config):
    def __init__(self):
        super().__init__()

    async def translate_tags(self):
        """
        对 tag_list 表中的标签进行中文翻译
        Translate the tags in the `tag_list` table into Chinese.
        """
        logger.info(f"Downloading translation database...")
        translate_tag_url = "https://github.com/EhTagTranslation/Database/releases/latest/download/db.text.json"
        translate_tag_name = "db.text.json"
        r = await self.fetch_data(translate_tag_url)
        # download file
        with open(translate_tag_name, 'wb') as f:
            f.write(r)
        # read file
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
            for entry in result:
                tid = entry[0]
                tag = entry[1]
                try:
                    namespace, tagcontent = tag.split(":", 1)
                except ValueError:
                    # 忽略部分tag不存在命名空间的错误
                    # Ignore errors related to some tags lacking a namespace.
                    logger.warning(f"Invalid tag: {tag}")
                    continue
                if namespace in namespace_data and tagcontent in namespace_data[namespace]:
                    translated_tag = namespace + ":" + namespace_data[namespace][tagcontent]["name"]
                    co.execute('''UPDATE tag_list SET translated_tag = ? WHERE tid = ?''', (translated_tag, tid))
                    # print(f"{tag.ljust(50)} -> {translated_tag}")
                    co.commit()
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
                'INSERT OR REPLACE INTO fav_name(fav_id, fav_name) VALUES (?,?)''',
                fav_category)
            co.commit()

    def format_fav_page_info(self, res):
        """
        格式化页面数据获取 gid 和 token 以及 Next_Gid
        Format page data to get gid and token and Next_Gid

        Returns: [
            [
                {'gid': gid, 'token': token},
                ...
            ],
            Next_gid
        ]
        """
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
                mylist.append({
                    'gid': gid,
                    'token': token
                })
        next_gid = res.select_one('a#dnext[href]')
        if next_gid is not None:
            next_gid = re.match('.*=([0-9].*)', next_gid.get('href'))[1].replace("/", "").replace(" ", "")
            # next_gid = int(next_gid)
        mylist = remove_duplicates_2d_array(mylist)
        return [mylist, next_gid]

    async def add_fav_data(self):
        logger.info(f'Get User Favorite gid and token...')
        fav_id = 0
        all_gid = []
        next_gid = None
        # 先将删除标志设置为 1, 如果后续收藏夹存在则设置为 0
        # First, set the delete flag to 1; if there are subsequent favorite categories, set it to 0.
        with sqlite3.connect(self.dbs_name) as co:
            co.execute('UPDATE fav_category SET del_flag = 1')
            co.commit()

        while fav_id < 10:
            if next_gid is None:
                logger.info(f'Get [{fav_id}th]...')
                url = f'https://{self.base_url}/favorites.php?favcat={fav_id}'
            else:
                url = f'https://{self.base_url}/favorites.php?favcat={fav_id}&f_search=&next={next_gid}'

            hx_res = await self.fetch_data(url)
            hx_res_bs = BeautifulSoup(hx_res, 'html.parser')
            search_data = self.format_fav_page_info(hx_res_bs)
            await asyncio.sleep(0.5)

            eh_data = []
            fav_category_data = []
            if len(search_data[0]) != 0:
                for item_data in search_data[0]:
                    _gid = int(item_data['gid'])
                    _token = str(item_data['token'])
                    eh_data.append((_gid, _token))
                    fav_category_data.append((_gid, _token, fav_id))
                    all_gid.append(_gid)
            with sqlite3.connect(self.dbs_name) as co:
                co.executemany(
                    '''INSERT OR IGNORE INTO eh_data(gid, token) VALUES (?,?)''',
                    eh_data)
                co.commit()
                co.executemany(
                    '''INSERT OR IGNORE INTO fav_category(gid, token, fav_id, del_flag) VALUES (?,?,?,0)''',
                    fav_category_data)
                co.commit()
                for gid, token, fav_id in fav_category_data:
                    co.execute('''UPDATE fav_category SET fav_id = ?, del_flag = 0 WHERE gid = ?''', (fav_id, gid))
                co.commit()

            # 判断切换下一个收藏夹
            # Judgment switch to next favorite
            next_gid = search_data[1]
            if next_gid is None:
                fav_id = fav_id + 1
                if fav_id < 10:
                    logger.info(f'Switch to [{fav_id}th] ...')

        with sqlite3.connect(self.dbs_name) as co:
            count = co.execute('SELECT COUNT(*) FROM fav_category WHERE del_flag = 0').fetchone()[0]
        logger.info(f' User Favorite, A Total Of: {count}...')
        if count == 0:
            logger.error(f'User Favorite is empty, Please add favorite first! (Update Cookies?)')
            sys.exit(1)
        return all_gid

    async def post_eh_api(self, json):
        eh_api_data = await self.fetch_data(url="https://api.e-hentai.org/api.php", json=json)
        json_data = eh_api_data['gmetadata']
        await asyncio.sleep(0.5)
        return json_data

    async def add_tags_data(self, get_all=False):
        """
        默认get_all=False只更新标题为空或NULL的TAG
        The default behavior `get_all=False` only updates TAGs where the title is empty or NULL.

        以 `eh_data` 表为准, 更新字段数据及其tag( `gid_tid` & `tag_list` )
        Based on the `eh_data` table, update the field data and its tags (`gid_tid` and `tag_list`).
        """
        logger.info(f'Get EH tags...')
        if not get_all:
            with sqlite3.connect(self.dbs_name) as co:
                gid_token = co.execute(
                    '''
                    SELECT gid, token 
                    FROM eh_data 
                    WHERE title = "" OR title IS NULL
                    '''
                ).fetchall()
        else:
            with sqlite3.connect(self.dbs_name) as co:
                gid_token = co.execute('''SELECT gid,token FROM eh_data''').fetchall()

        total = len(gid_token)
        # 每次请求 25 个数据
        # Fetching 25 data items per request
        piece = 25

        if total != 0:
            gid_token = [list(t) for t in gid_token]
            # 分片
            # Fragmentation
            gid_token = [gid_token[i:i + piece] for i in range(0, len(gid_token), piece)]
            post_json_arr = []
            for i in gid_token:
                post_json_arr.append({
                    "method": "gdata",
                    "gidlist": i,
                    "namespace": 1
                })
            with tqdm(total=total) as progress_bar:
                for post_json in post_json_arr:
                    post_data = await self.post_eh_api(post_json)
                    format_data = []
                    for sub_post_data in post_data:
                        gid = sub_post_data.get('gid')
                        token = sub_post_data.get('token')
                        try:
                            expunged = sub_post_data.get('expunged')
                            if expunged == False or expunged == 0:
                                expunged = 0
                            else:
                                expunged = 1
                        except Exception:
                            logger.error(f"expunged error: {expunged}")
                            logger.error(f"https://exhentai.org/g/{gid}/{token}")
                            sys.exit(1)
                        format_data.append((
                            sub_post_data.get('title', ''),
                            sub_post_data.get('title_jpn', ''),
                            sub_post_data.get('category', ''),
                            sub_post_data.get('thumb', ''),
                            sub_post_data.get('uploader', ''),
                            sub_post_data.get('posted', ''),
                            int(sub_post_data.get('filecount', 0)),
                            int(sub_post_data.get('filesize', 0)),
                            expunged,
                            str(sub_post_data.get('rating', '')),
                            str(sub_post_data.get('tags', '')),
                            int(sub_post_data.get('current_gid', gid)),
                            str(sub_post_data.get('current_key', token)),
                            gid
                        ))

                    # 向数据库插入数据 / Insert data into the database.
                    for data in format_data:
                        gid = data[13]
                        # Add data to the eh_data table.
                        co.execute('''
                            UPDATE eh_data 
                            SET title =?,
                            title_jpn =?,
                            category =?,
                            thumb =?,
                            uploader =?,
                            posted =?,
                            filecount =?,
                            filesize =?,
                            expunged =?,
                            rating =?,
                            current_gid =?,
                            current_token =? 
                            WHERE
                                gid =?
                            ''',
                                   (data[0], data[1], data[2], data[3], data[4], data[5],
                                    data[6], data[7], data[8], data[9], data[11],
                                    data[12], gid)
                                   )

                        # Clear tag data
                        co.execute('DELETE FROM gid_tid WHERE gid =?', (gid,))
                        co.commit()

                        # Add tag data
                        tags = ast.literal_eval(data[10])
                        for tag in tags:
                            result = co.execute('''SELECT tid FROM tag_list WHERE tag =?''', (tag,)).fetchone()
                            if result:
                                tid = result[0]
                            else:
                                co.execute('''INSERT INTO tag_list (tag) VALUES (?)''', (tag,))
                                tid = co.execute('''SELECT tid FROM tag_list WHERE tag =?''', (tag,)).fetchone()[0]
                            co.execute('''INSERT OR IGNORE INTO gid_tid (gid, tid) VALUES (?, ?)''', (gid, tid))
                    co.commit()
                    progress_bar.update(piece)

            # 检查遗漏数据 / Check for missing data
            missed_tag = co.execute('''
                SELECT
                    gid 
                FROM
                    eh_data 
                WHERE
                    gid NOT IN ( SELECT gid FROM gid_tid WHERE gid IS NOT NULL )
                ''').fetchall()
            if len(missed_tag) > 0:
                logger.warning(f"Missed data: {missed_tag}")
                logger.warning("Retry in 3 seconds")
                await asyncio.sleep(3)
                await self.add_tags_data()

    async def clear_del_flag(self):
        """
        1. 清理 del_falg=1 并且没有下载的画廊
        2. 移动旧画廊到 `del` 目录
        3. 返回存在更新的画廊
        1. Clean up galleries with `del_flag=1` that have not been downloaded.
        2. Move old galleries to the `del` directory.
        3. Return galleries with updates.

        :return: [] | [
        [gid, token, current_gid, current_token]
        ...
        ]
        """
        with sqlite3.connect(self.dbs_name) as co:
            # 清除所有 del_flag=1 并且没有下载的画廊 original_flag = 0 AND web_1280x_flag = 0
            # Clear all items where del_flag=1 and have not been downloaded, with original_flag=0 and web_1280x_flag=0.
            # co.execute('''
            # DELETE
            # FROM
            #     eh_data
            # WHERE
            #     gid IN ( SELECT gid FROM fav_category WHERE del_flag = 1 AND original_flag = 0 AND web_1280x_flag = 0 )
            # ''')
            # co.commit()
            # co.execute('''
            # DELETE
            # FROM
            #     gid_tid
            # WHERE
            #     gid IN ( SELECT gid FROM fav_category WHERE del_flag = 1 AND original_flag = 0 AND web_1280x_flag = 0 )
            # ''')
            # co.commit()
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

            # 移动所有旧画廊到 del 目录 (gid==current_gid)
            # Move all old galleries to the "del" directory (gid==current_gid).
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
            ''')
            clear_old_file([i[0] for i in del_list])

            # 移动已下载的旧画廊到 del 目录 (其新画廊已下载)
            # Move the downloaded old galleries to the "del" directory (their new galleries have already been downloaded).
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
                AND eh.current_gid IN ( SELECT gid FROM fav_category WHERE del_flag = 0 AND original_flag = 1 OR web_1280x_flag = 1 )
            ''')
            clear_old_file([i[0] for i in del_list])

            # 搜索 del_flag=1 并且 已下载 并且 当前字段的current_gid=其他字段的gid (并且current_gid的画廊未下载为del_flag=0)
            # 就可以得出结论, 当前画廊存在更新
            # Search for records where `del_flag=1` and `already downloaded`,
            # and where the current field's `current_gid` matches another field's `gid`.
            # This indicates that the current gallery has updates.
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

        await self.add_fav_data()

        await self.add_tags_data()

        return await self.clear_del_flag()
