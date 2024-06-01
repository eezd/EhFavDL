import sys

from bs4 import BeautifulSoup

from .Config import Config
from .common import *


class AddFavData(Config):
    def __init__(self):
        super().__init__()

    def update_category(self):
        """
        添加收藏夹分类名称
        Add Favorites Category Name
        """

        logger.info(f'[Running] Get Favorites Category...')

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

        logger.info(f'[OK] Get Favorites Category...')

    def get_fav_page_info(self, res):
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

    def add_fav_data(self):
        """
        获取收藏夹数据, 向数据库写入 gid, token, fav_id.
        Retrieve favorite data and write gid, token, fav_id to the database.
        """
        logger.info(f'[Running] Add Favorite gid and token...')

        fav_id = 0
        next_gid = None

        while fav_id < 10:
            if next_gid is None:
                logger.info(f'[Running] Fetching the {fav_id}th favorite data...')
                url = f'https://{self.base_url}/favorites.php?favcat={fav_id}'
            else:
                url = f'https://{self.base_url}/favorites.php?favcat={fav_id}&f_search=&next={next_gid}'

            hx_res = self.request.get(url)

            hx_res_bs = BeautifulSoup(hx_res, 'html.parser')
            search_data = self.get_fav_page_info(hx_res_bs)

            fav_data = []
            fav_category_data = []
            if len(search_data[0]) != 0:
                for item_data in search_data[0]:
                    fav_data.append((int(item_data['gid']), item_data['token']))
                    fav_category_data.append((int(item_data['gid']), fav_id))

            with sqlite3.connect(self.dbs_name) as co:
                co.executemany(
                    'INSERT OR IGNORE INTO fav(gid, token) VALUES (?,?)',
                    fav_data)

                co.commit()

                co.executemany(
                    'INSERT OR IGNORE INTO fav_category(gid, fav_id) VALUES (?,?)',
                    fav_category_data)

                co.commit()

            # 判断切换下一个收藏夹
            # Judgment switch to next favorite
            next_gid = search_data[1]
            if next_gid is None:
                fav_id = fav_id + 1
                logger.info(f'[OK] Fetching the {fav_id}th favorite data...')

        with sqlite3.connect(self.dbs_name) as co:
            count = co.execute('SELECT COUNT(*) FROM fav').fetchone()
        logger.info(f'[OK] Add Favorite gid and token, A Total Of: {count}...')

    def post_eh_api(self, json):
        """
        请求 EH API
        Request EH API
        """
        try:
            eh_api_data = self.request.post("https://api.e-hentai.org/api.php", json=json)
            json_data = eh_api_data.json()['gmetadata']
            time.sleep(0.5)
            return json_data
        except Exception as exc:
            logger.warning("A network error occurred while requesting the API, retrying")
            time.sleep(5)
            return self.post_eh_api(json)

    def add_tags_data(self, get_all=False):
        """
        根据数据库 gid,token 去请求 EH API 数据, 更新数据库数据.
        默认只获取 title 为空的字段, 通过 add_tags_data(True) 即可更新所有字段

        Retrieve EH API data based on database gid and token, and update the database.
        By default, only fetch records with an empty title field.
        Use add_tags_data(True) to update all fields.
        """

        logger.info(f'[Running] Get tags...')

        if not get_all:
            with sqlite3.connect(self.dbs_name) as co:
                gid_token = co.execute('SELECT gid,token FROM fav WHERE title IS "" OR title IS NULL').fetchall()
        else:
            with sqlite3.connect(self.dbs_name) as co:
                gid_token = co.execute('SELECT gid,token FROM fav').fetchall()

        if len(gid_token) != 0:
            # logger.warning("add_tags_data() >>> gid does not exist")

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
                        'UPDATE fav SET title=?, title_jpn=?, category=?, thumb=?, uploader=?, posted=?, pages=?, rating=?, tags=? WHERE gid=?',
                        format_data
                    )
                    co.commit()
        logger.info(f'[OK] Get tags...')

    def checkout_local_state(self):
        """
        防止当数据库被删除时重复下载图片

        note: 判断 文件夹中的图片个数 和 数据库中对应的pages值是否相同.
        Note: Determine whether the number of pictures in the folder
         is the same as the corresponding pages value in the database
        """
        logger.info('[Running] Checkout Local Data State...')

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
                co = co.execute(f'SELECT pages FROM fav WHERE gid="{gid}"')
                db_pages = co.fetchone()[0]

                if db_pages is not None:
                    db_pages = db_pages[0]
                else:
                    logger.error(f"在 FAV 中找不到该gid>>>{gid}")
                    db_pages = 0
                    sys.exit(1)

            if int(local_pages) == int(db_pages):
                with sqlite3.connect(self.dbs_name) as co:
                    co.execute(f'UPDATE fav SET state = 2 WHERE gid = {gid}')
                    co.commit()

        logger.info('[OK] Checkout Local Data State...')

    def apply(self):
        self.update_category()

        # 先获取 gid 和 token
        # First, obtain gid and token.
        self.add_fav_data()

        # 再根据数据库的 gid 和 token, 通过 EH API 获取剩余信息
        # Retrieve additional information based on the database's gid and token using the EH API.
        self.add_tags_data()
