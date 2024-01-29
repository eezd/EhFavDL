import re

from bs4 import BeautifulSoup
import sys
from .common import *
from datetime import datetime


class GetFavData:
    """
    获取收藏夹的信息, 然后录入数据库
    Add favorite data, and then enter the database
    """

    def __init__(self, hx, dbs_name, data_path, base_url):
        self.hx = hx
        self.dbs_name = dbs_name
        self.data_path = data_path
        self.base_url = base_url

    def get_category(self):
        """
        获取收藏夹分类
        Get Favorites Category
        """

        logger.info(f'[Loading] Get Favorites Category...')

        hx_res = self.hx.get(f'https://{self.base_url}/uconfig.php')
        hx_res_bs = BeautifulSoup(hx_res, 'html.parser')
        hx_res_bs = hx_res_bs.select('#favsel > div input')

        fav_category = []
        for index, i in enumerate(hx_res_bs):
            fav_category.append((index, i.get('value')))

        with sqlite3.connect(self.dbs_name) as co:
            co.executemany(
                'INSERT OR REPLACE INTO CATEGORY(ID, NAME) VALUES (?,?)',
                fav_category)

            co.commit()

        logger.info(f'[OK] Get Favorites Category...')

    @logger.catch()
    def get_search_data(self, res):
        """
        格式化页面数据获取 GID 和 TOKEN 以及 Next_Gid
        Format page data to get GID and TOKEN and Next_Gid

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

            check_url = str(url).find("/g/")

            if check_url == -1:
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
    def update_fav_data(self):
        """
        遍历收藏夹, 获取 GID 和 TOKEN, 录入数据库.
        Traverse the favorites, get the GID and TOKEN, and enter the database.
        """
        logger.info(f'[Loading] Get Favorite GID and TOKEN...')

        fav_num = 0
        next_gid = None

        while fav_num < 10:
            if next_gid is None:
                logger.info(f'[Loading] Fetching the {fav_num}th favorite data...')
                url = f'https://{self.base_url}/favorites.php?favcat={fav_num}'
            else:
                url = f'https://{self.base_url}/favorites.php?favcat={fav_num}&f_search=&next={next_gid}'

            hx_res = self.hx.get(url)

            hx_res_bs = BeautifulSoup(hx_res, 'html.parser')
            search_data = self.get_search_data(hx_res_bs)

            # 判断切换下一个收藏夹
            # Judgment switch to next favorite
            next_gid = search_data[1]
            if next_gid is None:
                fav_num = fav_num + 1
                logger.info(f'[OK] Fetching the {fav_num}th favorite data...')

            fav_data = []
            if len(search_data[0]) != 0:
                for item_data in search_data[0]:
                    fav_data.append((int(item_data['gid']), item_data['token'], fav_num))

            with sqlite3.connect(self.dbs_name) as co:
                co.executemany(
                    'INSERT OR IGNORE INTO FAV(GID, TOKEN, FAVORITE) VALUES (?,?,?)',
                    fav_data)

                co.commit()

                co.executemany(
                    'UPDATE FAV SET TOKEN=?, FAVORITE=? WHERE GID=?',
                    [(token, favorite, gid) for gid, token, favorite in fav_data]
                )

                co.commit()

        with sqlite3.connect(self.dbs_name) as co:
            count = co.execute('SELECT COUNT(*) FROM FAV').fetchone()
        logger.info(f'[OK] Get Favorite GID and TOKEN, A Total Of: {count}...')

    def post_eh_api(self, json):
        """
        请求 EH API
        Request EH API
        """
        try:
            eh_api_data = self.hx.post("https://api.e-hentai.org/api.php", json=json)
            json_data = eh_api_data.json()['gmetadata']
            time.sleep(0.5)
            return json_data
        except Exception as exc:
            logger.warning("A network error occurred while requesting the API, retrying")
            time.sleep(2)
            return self.post_eh_api(json)

    def get_tags_data(self):
        """
        向数据库写入 EH API 数据
        Write EH API data to database
        """

        logger.info(f'[Loading] Get tags...')

        with sqlite3.connect(self.dbs_name) as co:
            gid_token = co.execute('SELECT * FROM FAV f WHERE TITLE IS "" OR TITLE IS NULL ').fetchall()

        if len(gid_token) == 0:
            logger.warning("eh_api_label() >>> gid does not exist")
            sys.exit(1)

        gid_token = [list(t) for t in gid_token]

        # 分片, 25个一片
        # Fragmentation, 25 pieces
        gid_token = [gid_token[i:i + 25] for i in range(0, len(gid_token), 25)]

        post_json_arr = []

        for i in gid_token:
            post_json_arr.append({
                "method": "gdata",
                "gidlist": i,
                "namespace": 1
            })

        # 通过 EH API 请求数据
        # Request data through EH API
        for post_json in post_json_arr:
            post_data = self.post_eh_api(post_json)
            format_data = []
            for sub_post_data in post_data:
                format_data.append((
                    sub_post_data['title'],
                    sub_post_data['title_jpn'],
                    sub_post_data['category'],
                    sub_post_data['thumb'],
                    sub_post_data['uploader'],
                    sub_post_data['posted'],
                    int(sub_post_data['filecount']),
                    str(sub_post_data['rating']),
                    str(sub_post_data['tags']),
                    sub_post_data['gid'],
                ))

            with sqlite3.connect(self.dbs_name) as co:
                co.executemany(
                    'UPDATE FAV SET TITLE=?, TITLE_JPN=?, CATEGORY=?, THUMB=?, UPLOADER=?, POSTED=?, PAGES=?, RATING=?, TAGS=? WHERE GID=?',
                    format_data
                )
                co.commit()
        logger.info(f'[OK] Get tags...')

    def checkout_local_state(self):
        """
        防止当数据库被删除时重复下载图片

        note: 判断 文件夹中的图片个数 和 数据库中对应的PAGES值是否相同.
        Note: Determine whether the number of pictures in the folder
         is the same as the corresponding PAGES value in the database
        """
        logger.info('[Loading] Checkout Local Data State...')

        # 遍历本地目录
        # traverse the local directory
        os.makedirs(self.data_path, exist_ok=True)
        for i in os.listdir(self.data_path):
            if i.find('-') == -1:
                continue

            gid = int(str(i).split('-')[0])

            local_pages = 0

            # 遍历二级目录获取文件数量
            # Traverse the secondary directory to get the number of files
            for j in os.listdir(os.path.join(self.data_path, i)):
                if os.path.isfile(os.path.join(self.data_path, i, j)):
                    local_pages = local_pages + 1

            with sqlite3.connect(self.dbs_name) as co:
                co = co.execute(f'SELECT PAGES FROM FAV WHERE GID="{gid}"')
                db_pages = co.fetchone()[0]

                if db_pages is not None:
                    db_pages = db_pages[0]
                else:
                    logger.error(f"在 FAV 中找不到该GID>>>{gid}")
                    db_pages = 0
                    sys.exit(1)

            if int(local_pages) == int(db_pages):
                with sqlite3.connect(self.dbs_name) as co:
                    co.execute(f'UPDATE FAV SET STATE = 2, TIME={get_time()} WHERE gid = {gid}')
                    co.commit()

        logger.info('[OK] Checkout Local Data State...')

    def apply(self):
        self.get_category()

        self.update_fav_data()

        self.get_tags_data()

        # self.checkout_local_state()
