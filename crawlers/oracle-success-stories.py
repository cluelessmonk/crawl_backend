import asyncio
import time

async def crawl(url):
    # Simulate URL crawling by sending URLs every 2 seconds
    for i in range(1, 6):
        crawled_url = f"{url}/page{i}"
        print("inside" + crawled_url)
        yield crawled_url
        await asyncio.sleep(2)
