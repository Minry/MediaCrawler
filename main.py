import sys
import asyncio
import argparse

import config
from media_platform.xhs.client import XHSClient
from media_platform.xhs.login import XHSLogin
from tools import utils
from base import proxy_account_pool
from media_platform.douyin import DouYinCrawler
from media_platform.xhs import XiaoHongShuCrawler
from aiohttp import web
from playwright.async_api import Page
from playwright.async_api import Cookie
from playwright.async_api import BrowserContext
from playwright.async_api import async_playwright

class CrawlerFactory:
    @staticmethod
    def create_crawler(platform: str):
        if platform == "xhs":
            return XiaoHongShuCrawler()
        elif platform == "dy":
            return DouYinCrawler()
        else:
            raise ValueError("Invalid Media Platform Currently only supported xhs or douyin ...")

crawler = CrawlerFactory().create_crawler(platform=config.PLATFORM)
utils.init_loging_config()
# define command line params ...
parser = argparse.ArgumentParser(description='Media crawler program.')
parser.add_argument('--platform', type=str, help='Media platform select (xhs|dy)...', default=config.PLATFORM)
parser.add_argument('--lt', type=str, help='Login type (qrcode | phone | cookie)', default=config.LOGIN_TYPE_COOKIE)
# init account pool
account_pool = proxy_account_pool.create_account_pool()
args = parser.parse_args()
crawler.init_config(
    command_args=args,
    account_pool=account_pool
)
account_phone, playwright_proxy, httpx_proxy = crawler.create_proxy_info()
if not config.ENABLE_IP_PROXY:
            playwright_proxy, httpx_proxy = None, None

async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8081)
    await site.start()
    async with async_playwright() as playwright:
            # launch browser and create single browser context
            chromium = playwright.chromium
            browser = await chromium.launch(headless=config.HEADLESS, proxy=playwright_proxy)
            crawler.browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=crawler.user_agent
            )

            # execute JS to bypass anti automation/crawler detection
            await crawler.browser_context.add_init_script(path="libs/stealth.min.js")
            crawler.context_page = await crawler.browser_context.new_page()
            await crawler.context_page.goto(crawler.index_url)

            # begin login
            login_obj = XHSLogin(
                login_type=crawler.command_args.lt,
                login_phone=account_phone,
                browser_context=crawler.browser_context,
                context_page=crawler.context_page,
                cookie_str=config.COOKIES
            )
            await login_obj.begin()

            # update cookies
            await crawler.update_cookies()

            # init request client
            cookie_str, cookie_dict = utils.convert_cookies(crawler.cookies)
            crawler.xhs_client = XHSClient(
                proxies=httpx_proxy,
                headers={
                    "User-Agent": crawler.user_agent,
                    "Cookie": cookie_str,
                    "Origin": "https://www.xiaohongshu.com",
                    "Referer": "https://www.xiaohongshu.com",
                    "Content-Type": "application/json;charset=UTF-8"
                },
                playwright_page=crawler.context_page,
                cookie_dict=cookie_dict,
            )

            # Search for notes and retrieve their comment information.
            # await self.search_posts()
            print(await crawler.xhs_client.get_note_by_id("648912e70000000012033f1a"))

            # block main crawler coroutine
            await asyncio.Event().wait()


async def handle(request):
    name = request.match_info.get('name', "Anonymous")
    # await crawler.start()
    # s=await crawler.start2(name)
    s=await crawler.xhs_client.get_note_by_id(name)
    print(s)
    return web.json_response(s)

app = web.Application()
app.add_routes([web.get('/{name}', handle)])


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        await crawler.close()
        sys.exit()
    except Exception as e:
        print(f"Unexpected error: {e}")
        await crawler.close()
