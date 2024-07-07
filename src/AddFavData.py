import sqlite3
import sys

from bs4 import BeautifulSoup
from loguru import logger
from tqdm import tqdm

from .Config import Config
from .common import *


class AddFavData(Config):
    def __init__(self):
        super().__init__()

    @logger.catch()
    def update_category(self):
        logger.info(f'Get Favorite Category Name...')

        hx_res = self.request.get(f'https://{self.base_url}/uconfig.php')
        hx_res_bs = BeautifulSoup(hx_res, 'html.parser')
        hx_res_bs = hx_res_bs.select('#favsel > div input')

        fav_category = []
        for index, i in enumerate(hx_res_bs):
            fav_category.append((index, i.get('value')))

        with sqlite3.connect(self.dbs_name) as co:
            co.executemany(
                'INSERT OR REPLACE INTO fav_name(fav_id, fav_name) VALUES (?,?)',
                fav_category)

            co.commit()

    @logger.catch()
    def format_fav_page_info(self, res):
        """
        格式化页面数据获取 gid 和 token 以及 Next_Gid
        Format page data to get gid and token and Next_Gid

        Returns:[
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

    @logger.catch()
    def add_fav_data(self):
        logger.info(f'Get User Favorite gid and token...')

        fav_id = 0
        all_gid = []
        next_gid = None

        # 先将删除标志设置为 1, 如果后续收藏夹存在则设置为 0
        with sqlite3.connect(self.dbs_name) as co:
            co.execute('UPDATE fav_category SET del_flag = 1')
            co.commit()

        while fav_id < 10:
            if next_gid is None:
                logger.info(f'Get [{fav_id}th]...')
                url = f'https://{self.base_url}/favorites.php?favcat={fav_id}'
            else:
                url = f'https://{self.base_url}/favorites.php?favcat={fav_id}&f_search=&next={next_gid}'

            hx_res = self.request.get(url)

            hx_res_bs = BeautifulSoup(hx_res, 'html.parser')
            search_data = self.format_fav_page_info(hx_res_bs)
            time.sleep(0.5)

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
                    "INSERT OR IGNORE INTO eh_data(gid, token) VALUES (?,?)",
                    eh_data)
                co.commit()

                co.executemany(
                    "INSERT OR IGNORE INTO fav_category(gid, token, fav_id, del_flag) VALUES (?,?,?,0)",
                    fav_category_data)
                co.commit()

                for gid, token, fav_id in fav_category_data:
                    co.execute('UPDATE fav_category SET fav_id = ?, del_flag = 0 WHERE gid = ?', (fav_id, gid))
                co.commit()

            # 判断切换下一个收藏夹
            # Judgment switch to next favorite
            next_gid = search_data[1]
            if next_gid is None:
                fav_id = fav_id + 1
                if fav_id < 10:
                    logger.info(f'Switch to [{fav_id}th] ...')

        with sqlite3.connect(self.dbs_name) as co:
            count = co.execute('SELECT COUNT(*) FROM fav_category').fetchone()[0]
        logger.info(f' User Favorite, A Total Of: {count}...')

        return all_gid

    @logger.catch()
    def post_eh_api(self, json):
        try:
            eh_api_data = self.request.post("https://api.e-hentai.org/api.php", json=json)
            json_data = eh_api_data.json()['gmetadata']
            time.sleep(0.5)
            return json_data
        except Exception as exc:
            logger.warning("A network error occurred while requesting the API, retrying")
            time.sleep(5)
            return self.post_eh_api(json)

    @logger.catch()
    def add_tags_data(self, get_all=False):
        logger.info(f'Get EH tags...')

        if not get_all:
            with sqlite3.connect(self.dbs_name) as co:
                gid_token = co.execute('SELECT gid,token FROM eh_data WHERE title IS "" OR title IS NULL').fetchall()
        else:
            with sqlite3.connect(self.dbs_name) as co:
                gid_token = co.execute('SELECT gid,token FROM eh_data').fetchall()

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
                    post_data = self.post_eh_api(post_json)
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
                            str(sub_post_data.get('current_token', token)),
                            gid
                        ))

                    for data in format_data:
                        co.execute(
                            "UPDATE eh_data SET title=?, title_jpn=?, "
                            "category=?, thumb=?, uploader=?, posted=?, filecount=?, "
                            "filesize=?, expunged=?, rating=?, tags=?, current_gid=?, "
                            "current_token=? WHERE gid=?",
                            (data[0], data[1], data[2], data[3], data[4], data[5],
                             data[6], data[7], data[8], data[9], data[10], data[11],
                             data[12], data[13])
                        )
                    co.commit()

                    progress_bar.update(piece)

    def delete_fav_category_del_flag(self):
        """
        删除 del_flag = 1 的字段
        """
        with sqlite3.connect(self.dbs_name) as co:
            count = co.execute('DELETE FROM fav_category WHERE del_flag = 1').fetchone()[0]
            co.commit()
            logger.info(f"Delete del_flag = 1: {count}...")

    @logger.catch()
    def apply(self):
        self.update_category()

        self.add_fav_data()

        self.add_tags_data()

        with sqlite3.connect(self.dbs_name) as co:
            del_flag_list = co.execute('SELECT gid,token FROM fav_category WHERE del_flag = 1').fetchall()

            if len(del_flag_list) > 0:
                logger.warning(f"del_flag = 1:")
                for gid_token in del_flag_list:
                    logger.warning(f"https://exhentai.org/g/{gid_token[0]}/{gid_token[1]}")

                del_enter = input("Delete data where del_flag = 1? (y/n):")
                if del_enter.lower() == 'y':
                    self.delete_fav_category_del_flag()
