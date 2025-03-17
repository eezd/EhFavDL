import ast
import asyncio
from datetime import datetime

from bs4 import BeautifulSoup

from src.Utils import *


class _AddFavData(Config):
    def __init__(self):
        super().__init__()

    def write_meta_data(self, post_data):
        # 向数据库插入数据 / Insert data into the database.
        with sqlite3.connect(self.dbs_name) as co:
            for item in post_data:
                gid = item.get('gid')
                token = item.get('token')
                tags = item.get('tags', '')
                current_gid = item.get('current_gid', gid)
                current_token = item.get('current_token', token)
                parent_gid = item.get('parent_gid', gid)
                parent_token = item.get('parent_token', token)
                # Add data to the eh_data table.
                co.execute('''
                            INSERT 
                                OR REPLACE INTO eh_data ( 
                                gid, token, title, title_jpn, category, 
                                thumb, uploader, posted, filecount, 
                                filesize, expunged, rating, current_gid, current_token )
                            VALUES
                                ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )
                    ''', item.get('data'))

                # Clear tag data
                co.execute('DELETE FROM gid_tid WHERE gid =?', (gid,))
                co.commit()

                # Add tag data
                tags = ast.literal_eval(tags)
                for tag in tags:
                    result = co.execute('''SELECT tid FROM tag_list WHERE tag =?''', (tag,)).fetchone()
                    if result:
                        tid = result[0]
                    else:
                        co.execute('''INSERT INTO tag_list (tag) VALUES (?)''', (tag,))
                        tid = co.execute('''SELECT tid FROM tag_list WHERE tag =?''', (tag,)).fetchone()[0]
                    co.execute('''INSERT OR IGNORE INTO gid_tid (gid, tid) VALUES (?, ?)''', (gid, tid))
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
                    int(sub_post_data.get('current_gid', gid)),
                    str(sub_post_data.get('current_key', token)),
                ),
            })
        return format_data

    async def meta_data(self, get_all=False):
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
                    WHERE title = '' OR title IS NULL
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
                    self.write_meta_data(post_data)
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
                await self.meta_data()
            elif get_all:
                # 如果更新完所有 metadata, 则更新检查时间(推迟 24 小时)
                with sqlite3.connect(self.dbs_name) as co:
                    co.execute(
                        '''
                        INSERT OR REPLACE INTO watch_record(id, last_check_time) 
                        VALUES (1, datetime('now', '-24 hours', 'localtime'));
                        '''
                    )
                    co.commit()
                pass

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

                # Published Time
                div_tag = res.find('div', id=f'posted_{gid}')
                time_text_updated = div_tag.get_text(strip=True)
                published_time = datetime.strptime(time_text_updated, "%Y-%m-%d %H:%M")

                # Favorited Time
                # 当EH页面布局为 Thumbnail 时会出问题
                # td_tag = res.find('td', class_='glfc glfav')
                # date_text = td_tag.find_all('p')[0].get_text(strip=True)  # 2024-07-25
                # time_text = td_tag.find_all('p')[1].get_text(strip=True)  # 19:46
                # datetime_str = f"{date_text} {time_text}"
                # fav_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")

                # Get Fav ID
                fav_name = div_tag.get('title')
                fav_id = fav_category.get(fav_name)
                if fav_id is None:
                    logger.error(f"Can't find fav id for {fav_name}")
                    sys.exit(1)

                mylist.append({
                    'gid': gid,
                    'token': token,
                    'published_time': published_time,
                    # 'fav_time': fav_time
                    'fav_id': fav_id
                })
        next_gid = res.select_one('a#dnext[href]')
        if next_gid is not None:
            next_gid = re.match('.*=([0-9].*)', next_gid.get('href'))[1].replace("/", "").replace(" ", "")
            # next_gid = int(next_gid)
        mylist = remove_duplicates_2d_array(mylist)
        return [mylist, next_gid]

    def wirte_fav_data(self, data):
        """
        data:{
            'eh_data': eh_data,
            'fav_category_data': fav_category_data
        }
        """
        eh_data = data['eh_data']
        fav_category_data = data['fav_category_data']
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
                # instant_count += 1
                # # 添加了一个实时计数，能大致查看进度
                # print("Instant count of galleries: %d\r" % instant_count, end="")
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
                # 找不到就添加进去, 待会请求
                if status is None:
                    _gid_token.append([gid, token])
                else:
                    continue
            gid_token = _gid_token

            # 每次请求 25 个数据
            # Fetching 25 data items per request
            piece = 25
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
            # 清空数据, 最后作为参数递归调用
            gid_token = []
            for post_json in post_json_arr:
                post_data = await self.post_eh_api(post_json)
                for item in post_data:
                    current_gid = item.get('current_gid')
                    current_token = item.get('current_token')
                    parent_gid = item.get('parent_gid')
                    parent_token = item.get('parent_token')
                    if parent_gid is None: continue
                    with sqlite3.connect(self.dbs_name) as co:
                        p_gid = co.execute(
                            '''
                            SELECT gid, token FROM eh_data WHERE gid = ?
                            ''', (parent_gid,)).fetchone()
                        if p_gid is None:
                            gid_token.append((parent_gid, parent_token))
                        else:
                            co.execute('''UPDATE fav_category SET del_flag = 1 WHERE gid = ?''',
                                       (p_gid[0],))
                            co.commit()
                            co.execute('''UPDATE eh_data SET current_gid = ?, current_token = ? WHERE gid = ?''',
                                       (current_gid, current_token, p_gid[0]))
                            co.commit()
            if len(gid_token) != 0:
                await self.deep_check(gid_token, max_depth - 1)
            else:
                return

    async def post_fav_data(self, url_params="?f_search=&inline_set=fs_f", get_all=True):
        """
        url_params: 默认按照收藏时间排序

        get_all=True: 获取所有数据
        get_all=False: 只获取新画廊(按收藏时间排序与更新时间)
        """
        all_gid = []
        next_gid = 0

        # 先将删除标志设置为 1, 如果后续收藏夹存在则设置为 0
        # First, set the delete flag to 1; if there are subsequent favorite categories, set it to 0.
        if get_all is True:
            with sqlite3.connect(self.dbs_name) as co:
                co.execute('UPDATE fav_category SET del_flag = 1')
                co.commit()

        # 根据收藏时间, 逐步获取收藏夹数据
        while True:
            if next_gid is None:
                break
            elif next_gid == 0:
                url = f'https://{self.base_url}/favorites.php{url_params}'
            else:
                url = f'https://{self.base_url}/favorites.php{url_params}&next={next_gid}'

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
                    fav_id = int(item_data['fav_id'])
                    eh_data.append((_gid, _token))
                    fav_category_data.append((_gid, _token, fav_id))
                    all_gid.append(_gid)

            # 当前没有新画廊时，跳出循环
            if get_all is False:
                gid_list = [gid for gid, _ in eh_data]
                with sqlite3.connect(self.dbs_name) as co:
                    query = f"SELECT COUNT(*) FROM eh_data WHERE gid IN ({','.join(['?'] * len(gid_list))})"
                    count = co.execute(query, gid_list).fetchone()[0]
                if count == len(gid_list):
                    break
                elif url_params == "?f_search=&inline_set=fs_p":
                    # 按照更新时间排序 + get_all is False 时, 需要进行深度检测
                    await self.deep_check(gid_token=eh_data)
            self.wirte_fav_data({'eh_data': eh_data, 'fav_category_data': fav_category_data})

            # 判断切换下一个收藏夹
            # Judgment switch to next favorite
            next_gid = search_data[1]

        # with sqlite3.connect(self.dbs_name) as co:
        #     count = co.execute('SELECT COUNT(*) FROM fav_category WHERE del_flag = 0').fetchone()[0]
        # logger.info(f' User Favorite, A Total Of: {count}...')
        # if count == 0:
        #     logger.error(f'User Favorite is empty, Please add favorite first! (Update Cookies?)')
        #     sys.exit(1)
        return all_gid
