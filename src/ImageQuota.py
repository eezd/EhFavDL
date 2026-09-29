from bs4 import BeautifulSoup
from loguru import logger


class ImageQuota:
    def __init__(self, eh_client):
        self.eh_client = eh_client

    async def get_limits(self):
        response = BeautifulSoup(
            await self.eh_client.fetch_data(url="https://e-hentai.org/home.php"),
            "html.parser",
        )
        limits = response.select("div.homebox p strong")
        try:
            if len(limits) == 1:
                return 0, int(limits[0].text.strip().replace(",", ""))
            return (
                int(limits[0].text.strip().replace(",", "")),
                int(limits[1].text.strip().replace(",", "")),
            )
        except Exception:
            logger.warning("Failed to get image limits")
            return 0, 20000

    async def wait_until_available(self):
        while True:
            image_limits, total_limits = await self.get_limits()
            logger.info(f"Image Limits: {image_limits} / ({total_limits}*0.8 = {total_limits * 0.8})")
            if image_limits > total_limits * 0.8:
                lower_value = total_limits * 0.3
                wait_time = (image_limits - lower_value) * 6 + 60
                logger.warning(f"The IP quota has been exceeded. Please try again in {wait_time} Second.")
                import asyncio
                await asyncio.sleep(wait_time)
            else:
                return image_limits, total_limits
