import asyncio
import os
import re
import ssl
import sys
import urllib.request

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger
from PIL import Image
from tqdm import tqdm


ssl_context = ssl.create_default_context()
ssl_context.set_ciphers("HIGH:!DH:!aNULL")


class EhClient:
    def __init__(self, config):
        self.config = config
        self._session = None

    async def __aenter__(self):
        await self.get_session()
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        await self.close()

    async def get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self.config.request_headers,
                cookies=self.config.eh_cookies,
                connector=aiohttp.TCPConnector(ssl=ssl_context),
            )
        return self._session

    async def close(self):
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def fetch_data(self, url, json=None, data=None, tqdm_file_path=None, retry_delay=5, retry_attempts=5):
        try:
            session = await self.get_session()
            request_kwargs = {
                "timeout": aiohttp.ClientTimeout(connect=30),
                "proxy": self.config.proxy_url if self.config.proxy_status else None,
            }
            if data is not None:
                async with session.post(url, data=data, **request_kwargs) as response:
                    await self.check_fetch_err(response, url)
                    return await response.read()
            if json is not None:
                async with session.post(url, json=json, **request_kwargs) as response:
                    await self.check_fetch_err(response, url)
                    return await response.json(content_type=None)

            # Use urllib for file downloads; HTML pages still use aiohttp.
            if tqdm_file_path is not None:
                return await self.fetch_file_blocking(url=url, tqdm_file_path=tqdm_file_path)
            async with session.get(url, **request_kwargs) as response:
                await self.check_fetch_err(response, url)
                return await response.read()
        except Exception as exc:
            logger.error(f"{type(exc).__name__}: {exc} | URL: {url}")
            if retry_attempts > 0:
                if "hath.network" in str(url):
                    return "reload_image"
                logger.warning(
                    f"Failed to retrieve data. Retrying in {retry_delay} seconds, "
                    f"{retry_attempts - 1} attempts remaining. {url}"
                )
                await asyncio.sleep(retry_delay)
                return await self.fetch_data(
                    url=url,
                    json=json,
                    data=data,
                    tqdm_file_path=tqdm_file_path,
                    retry_delay=retry_delay,
                    retry_attempts=retry_attempts - 1,
                )
            while True:
                logger.warning("The request limit has been exceeded. Waiting 2 hour...")
                await asyncio.sleep(2 * 60 * 60)
                if "hath.network" in str(url):
                    return "reload_image"
                return await self.fetch_data(
                    url=url,
                    json=json,
                    data=data,
                    tqdm_file_path=tqdm_file_path,
                    retry_delay=retry_delay,
                    retry_attempts=2,
                )

    async def fetch_file_blocking(self, url, tqdm_file_path):
        """Download one image with urllib in a separate thread.

        Some H@H nodes ("Genetic Lifeform and Distributed Open Server 1.6.4",
        using ``Connection: close``) cause aiohttp to lose the trailing bytes of
        the response body, resulting in ContentLengthError or SSLEOFError. The
        same URL returns a complete file with curl and urllib.

        Returns True or "reload_image", or raises an exception handled by fetch_data.
        """
        headers = dict(self.config.request_headers or {})
        if self.config.eh_cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.config.eh_cookies.items() if v)

        temp_file_path = os.path.join(os.path.dirname(tqdm_file_path), "temp_" + os.path.basename(tqdm_file_path))
        desc_name = url.split("/")[-1] + "/" + os.path.basename(tqdm_file_path)

        def _download():
            handlers = [urllib.request.HTTPSHandler(context=ssl.create_default_context())]
            if self.config.proxy_status and self.config.proxy_url:
                handlers.append(urllib.request.ProxyHandler(
                    {"http": self.config.proxy_url, "https": self.config.proxy_url}))
            opener = urllib.request.build_opener(*handlers)
            request = urllib.request.Request(url, headers=headers)
            with opener.open(request, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                with open(temp_file_path, "wb") as file:
                    with tqdm(total=total, unit="B", unit_scale=True, desc=desc_name) as progress:
                        while chunk := resp.read(65536):
                            file.write(chunk)
                            progress.update(len(chunk))

        await asyncio.to_thread(_download)

        if os.path.exists(tqdm_file_path):
            os.remove(tqdm_file_path)
        try:
            image = Image.open(temp_file_path)
            image.verify()
            image.close()
        except Exception as exc:
            os.remove(temp_file_path)
            logger.error(f"Failed to process image: {temp_file_path}. Error: {exc}")
            return "reload_image"
        os.rename(temp_file_path, tqdm_file_path)
        return True

    async def check_fetch_err(self, response, msg):
        content_type = response.headers.get("Content-Type", "").lower()
        if "text" not in content_type and "json" not in content_type and "html" not in content_type:
            return
        try:
            content = await response.text()
            if "text/html" in content_type and content == "":
                logger.error("The content is empty. Please check if the cookies are correct.")
                sys.exit(1)
        except Exception:
            content = await response.text(errors="replace")
        if "IP quota exhausted" in content:
            soup = BeautifulSoup(content, "html.parser")
            for text_node in soup.find_all(string=re.compile(r"IP quota exhausted")):
                if not text_node.find_parent(class_="c6"):
                    logger.warning("IP quota exhausted. wait 360 seconds and try again.")
                    await asyncio.sleep(360)
                    raise Exception("IP quota exhausted")
        elif "This IP address has been temporarily banned due to an excessive request rate" in content:
            hours_match = re.search(r"(\d+) hours?", content)
            minutes_match = re.search(r"(\d+) minutes?", content)
            seconds_match = re.search(r"(\d+) seconds?", content)
            total_seconds = (
                (int(hours_match.group(1)) if hours_match else 0) * 3600
                + (int(minutes_match.group(1)) if minutes_match else 0) * 60
                + (int(seconds_match.group(1)) if seconds_match else 0)
                + 10
            )
            logger.warning(f"This IP address has been temporarily banned. Wait {total_seconds} seconds")
            await asyncio.sleep(total_seconds)
            raise Exception("IP temporarily banned")
        elif "You have clocked too many downloaded bytes on this gallery" in content:
            logger.warning("You have clocked too many downloaded bytes on this gallery.")
            logger.warning("Please open Gallery---Archive Download---Cancel")
            logger.warning(msg)
            raise Exception("Gallery download byte limit reached")
        elif "Your IP address has been temporarily banned for excessive pageloads" in content:
            logger.warning(content)
            await asyncio.sleep(12 * 60 * 60)
            raise Exception("IP temporarily banned for excessive pageloads")
