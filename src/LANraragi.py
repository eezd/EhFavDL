import aiohttp

from .Utils import *


class LANraragi(Config):
    def __init__(self, watch_status=False):
        super().__init__()
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

            with tqdm(total=len(all_archives)) as progress_bar:
                with sqlite3.connect(self.dbs_name) as co:
                    for sub_archives in all_archives:
                        try:
                            gid = re.compile('.*gid:([0-9]*),.*').match(str(sub_archives['tags']))
                            if gid is not None:
                                gid = int(gid.group(1))
                            else:
                                gid = int(str(sub_archives['title']).split('-')[0])
                        except ValueError:
                            logger.warning(
                                f"The ID does not exist>> arcid: {str(sub_archives['arcid'])}, title: {str(sub_archives['title'])}")
                            sys.exit(1)

                        # 根据 gid 查询数据库
                        co = co.execute(f'''
                        SELECT
                            eh.gid,
                            eh.token,
                            eh.title,
                            eh.title_jpn,
                            eh.category,
                            eh.posted,
                            fn.fav_name 
                        FROM
                            eh_data AS eh,
                            fav_category AS fc,
                            fav_name AS fn 
                        WHERE
                            eh.gid = "{gid}" 
                            AND fc.gid = "{gid}" 
                            AND fc.fav_id = fn.fav_id
                        ''')
                        fav_info = co.fetchone()

                        # 如果fav_category表中不存在该 gid , 则在eh_data表中查询↓↓↓
                        # If the `gid` does not exist in the `fav_category` table, then query the `eh_data` table.
                        if fav_info is None:
                            co = co.execute(f'''
                            SELECT
                                eh.gid,
                                eh.token,
                                eh.title,
                                eh.title_jpn,
                                eh.category,
                                eh.posted 
                            FROM
                                eh_data AS eh 
                            WHERE
                                eh.gid = "{gid}"
                            ''')
                            fav_info = co.fetchone()

                            if fav_info is None:
                                logger.warning(f"The ID does not exist>> {gid}")
                                continue
                            else:
                                fav_info = fav_info + ("no_category",)
                                logger.warning(
                                    f"The data does not exist in fav_category, but it exists in eh_data. The data has been "
                                    f"written.>> {gid}")

                        token = str(fav_info[1])

                        # 优先使用 title_jpn 作为标题
                        # title = str(gid) + "-" + str(fav_info[2])
                        if fav_info[3] is not None and fav_info[3] != "":
                            title = str(fav_info[3])
                        else:
                            title = str(fav_info[2])

                        source = f"exhentai.org/g/{gid}/{token}"

                        category = str(fav_info[4])

                        # posted = str(datetime.datetime.fromtimestamp(int(db_tags[3]))).split(" ")[0].replace("-", "/")
                        posted = fav_info[5]

                        # 使用 LANraragi 生成的 pages
                        # https://github.com/Difegue/LANraragi/issues/586
                        pages = int(sub_archives['pagecount'])

                        fav_name = ""
                        if len(fav_info) > 6:
                            fav_name = "fav_name:" + str(fav_info[6])

                        # 获取 tid 列表 / Get tid_list
                        tid_list = co.execute(f'''SELECT tid FROM gid_tid WHERE gid="{gid}"''').fetchall()
                        tid_list = [tid[0] for tid in tid_list]

                        # 在 tag_list 中查询对应 tag
                        placeholders = ','.join(['?'] * len(tid_list))
                        tag_list = co.execute(f'''
                        SELECT tag, translated_tag 
                        FROM
                            tag_list 
                        WHERE
                            tid IN ( {placeholders} )
                        ''', tid_list).fetchall()
                        db_tags = []
                        for tag in tag_list:
                            if tag[1] is not None and tag[1] != "" and self.tags_translation == True:
                                db_tags.append(tag[1])
                            else:
                                db_tags.append(tag[0])
                        tags = ','.join(db_tags)
                        lan_tags = f"gid:{gid},token:{token},source:{source},category:{category},date_added:{posted},pages:{pages},{fav_name}," + tags

                        async with session.put(f"{lan_url}/{sub_archives['arcid']}/metadata",
                                               data={"title": title, "tags": lan_tags.strip()}) as response:
                            await response.read()
                            progress_bar.update(1)

        logger.info("[OK] LANraragi Add Tags")

# <ComicInfo xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
# <Manga/>
# <Title>(C74)</Title>
# <Summary/>
# <Genre>doujinshi</Genre>
# <Tags>A,B</Tags>
# <BlackAndWhite/>
# <Year>2023</Year>
# <Month>6</Month>
# <Day>12</Day>
# <LanguageISO/>
# <Writer>ABCABC</Writer>
# <Series/>
# <PageCount/>
# <URL/>
# <Characters/>
# <Translated>Yes</Translated>
# </ComicInfo>
