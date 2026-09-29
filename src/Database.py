import sqlite3
from contextlib import contextmanager


class Database:
    def __init__(self, path):
        self.path = str(path)

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path)
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self):
        with self.connection() as co:
            co.execute('''
            CREATE TABLE IF NOT EXISTS "eh_data" (
                "gid" INTEGER PRIMARY KEY NOT NULL,
                "token" TEXT NOT NULL,
                "title" TEXT,
                "title_jpn" TEXT,
                "category" TEXT,
                "thumb" TEXT,
                "uploader" TEXT,
                "posted" TEXT,
                "filecount" INTEGER,
                "filesize" INTEGER,
                "expunged" INTEGER NOT NULL DEFAULT 0,
                "copyright_flag" INTEGER NOT NULL DEFAULT 0,
                "rating" TEXT,
                "current_gid" INTEGER,
                "current_token" TEXT
            )''')
            co.execute('''
            CREATE TABLE IF NOT EXISTS "fav_name" (
                "fav_id" INTEGER PRIMARY KEY NOT NULL,
                "fav_name" TEXT NOT NULL
            )''')
            co.execute('''
            CREATE TABLE IF NOT EXISTS "fav_category" (
                "gid" INTEGER PRIMARY KEY NOT NULL,
                "token" TEXT NOT NULL,
                "fav_id" INTEGER NOT NULL,
                "del_flag" INTEGER NOT NULL DEFAULT 0,
                "original_flag" INTEGER NOT NULL DEFAULT 0,
                "web_1280x_flag" INTEGER NOT NULL DEFAULT 0
            )''')
            co.execute('''
            CREATE TABLE IF NOT EXISTS tag_list (
                "tid" INTEGER PRIMARY KEY AUTOINCREMENT,
                "tag" TEXT UNIQUE NOT NULL,
                "translated_tag" TEXT
            )''')
            co.execute('''
            CREATE TABLE IF NOT EXISTS gid_tid (
                "gid" INTEGER UNSIGNED NOT NULL,
                "tid" INTEGER UNSIGNED NOT NULL,
                PRIMARY KEY (gid, tid),
                UNIQUE(gid, tid)
            )''')
            co.commit()
