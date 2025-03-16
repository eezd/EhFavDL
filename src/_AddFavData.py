import ast
import asyncio
from datetime import datetime

from src.Utils import *


class _AddFavData(Config):
    def __init__(self):
        super().__init__()

    def write_data(self, post_data):
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

    def format_fav_page_info(self, res):
        """
        格式化页面数据获取 gid 和 token 以及 Next_Gid
        Format page data to get gid and token and Next_Gid

        Returns: [
            [
                {'gid': gid, 'token': token, 'published_time': time},
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
                mylist.append({
                    'gid': gid,
                    'token': token,
                    'published_time': published_time
                    # 'fav_time': fav_time
                })
        next_gid = res.select_one('a#dnext[href]')
        if next_gid is not None:
            next_gid = re.match('.*=([0-9].*)', next_gid.get('href'))[1].replace("/", "").replace(" ", "")
            # next_gid = int(next_gid)
        mylist = remove_duplicates_2d_array(mylist)
        return [mylist, next_gid]

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
                    self.write_data(post_data)
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

    async def deep_check(self, max_depth=4):
        pass
