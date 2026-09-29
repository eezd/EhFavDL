class Service:
    """Small dependency holder for application services."""

    def __init__(self, config, database, eh_client=None, quota=None):
        self.config = config
        self.database = database
        self.eh_client = eh_client
        self.quota = quota

    @property
    def base_url(self):
        return self.config.base_url

    @property
    def data_path(self):
        return self.config.data_path

    @property
    def gallery_path(self):
        return self.config.gallery_path

    @property
    def web_path(self):
        return self.config.web_path

    @property
    def del_path(self):
        return self.config.del_path

    @property
    def duplicate_del_path(self):
        return self.config.duplicate_del_path

    @property
    def dbs_name(self):
        return self.database.path

    @property
    def tags_translation(self):
        return self.config.tags_translation

    @property
    def prefer_japanese_title(self):
        return self.config.prefer_japanese_title

    @property
    def connect_limit(self):
        return self.config.connect_limit

    @property
    def lan_url(self):
        return self.config.lan_url

    @property
    def lan_api_psw(self):
        return self.config.lan_api_psw

    @property
    def watch_fav_ids(self):
        return self.config.watch_fav_ids

    @property
    def watch_lan_status(self):
        return self.config.watch_lan_status

    async def fetch_data(self, *args, **kwargs):
        return await self.eh_client.fetch_data(*args, **kwargs)

    async def get_image_limits(self):
        return await self.quota.get_limits()

    async def wait_image_limits(self):
        return await self.quota.wait_until_available()

    def get_db_connection(self):
        return self.database.connection()
