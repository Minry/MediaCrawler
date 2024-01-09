import json
import os
import random
import sys
import asyncio
import argparse
from urllib.parse import urlparse

import config
import media_platform
from media_platform.douyin.login import DouYinLogin
from media_platform.xhs.client import XHSClient
from media_platform.xhs.exception import DataFetchError as XhsDataFetchError, IPBlockError as XhsIPBlockError
from media_platform.douyin.exception import DataFetchError as DouyinDataFetchError, IPBlockError as DouyinIPBlockError
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
from media_platform.xhs import field
import time
import subprocess

xhs_creator_info = None
dy_creator_info = None
routes = web.RouteTableDef()


async def on_response(response):
    if '/web/api/media/aweme/post' in response.url and response.status == 200:
        print(response.url)
        global dy_creator_info
        dy_creator_info = await response.json()
        return
    if '/api/galaxy/creator/note/user/posted' in response.url and response.status == 200:
        print(response.url)
        global xhs_creator_info
        xhs_creator_info = await response.json()
        return


class CrawlerFactory:
    @staticmethod
    def create_crawler(platform: str):
        if platform == "xhs":
            return XiaoHongShuCrawler()
        elif platform == "dy":
            return DouYinCrawler()
        else:
            raise ValueError("Invalid Media Platform Currently only supported xhs or douyin ...")


utils.init_loging_config()
# define command line params ...
parser = argparse.ArgumentParser(description='Media crawler program.')
parser.add_argument('--platform', type=str, help='Media platform select (xhs|dy)...', default=config.PLATFORM)
parser.add_argument('--lt', type=str, help='Login type (qrcode | phone | cookie)', default=config.LOGIN_TYPE_COOKIE)
# init account pool
account_pool = proxy_account_pool.create_account_pool()
args = parser.parse_args()

dy_crawler = CrawlerFactory().create_crawler(platform="dy")
dy_crawler.init_config(
    platform="dy",
    login_type="qrcode",
    account_pool=account_pool
)
dy_account_phone, dy_playwright_proxy, dy_httpx_proxy = dy_crawler.create_proxy_info()

xhs_crawler = CrawlerFactory().create_crawler(platform="xhs")
xhs_crawler.init_config(
    platform="xhs",
    # login_type="qrcode",
    login_type="cookie",
    account_pool=account_pool
)
xhs_account_phone, xhs_playwright_proxy, xhs_httpx_proxy = xhs_crawler.create_proxy_info()

# 获取谷歌浏览器中的cookie
async def get_xhs_cookie_value():
    async with async_playwright() as p:
        chromium = p.chromium
        #chrome右键属性-快捷方式-目标 中添加启动参数 --remote - debugging - port = 5003
        browser = await chromium.connect_over_cdp('http://localhost:5003')
        context = browser.contexts[0]
        # 设置你要获取 cookie 的域名
        target_domain = '.xiaohongshu.com'
        # 获取所有 cookies
        cookies = await context.cookies()
        # 查找目标域名的 cookie
        target_cookie = next((cookie for cookie in cookies if target_domain in cookie['domain'] and cookie['name'] == 'web_session'), None)
        if target_cookie:
            print(f"Value of 'web_session' cookie for {target_domain}: {target_cookie['value']}")
            return f"web_session={target_cookie['value']};"
        else:
            print(f"Cookie 'web_session' not found for {target_domain}")
            return config.COOKIES

# 判断小红书创作平台的cookie是否有效
async def xhs_creator_cookie_auth(xhs_creator_path):
    async with async_playwright() as playwright:
        # launch browser and create single browser context
        chromium = playwright.chromium
        # 为playwright操作小红书页面专门创建一个context

        # xhs_data_dir ="C:\\study\\python\\MediaCrawler\\browser_data\\xhs_user_data_dir" # type: ignore
        xhs_playwright_contex = await chromium.launch_persistent_context(
            user_data_dir=xhs_creator_path,
            headless=True,
        )
        page = await xhs_playwright_contex.new_page()
        await page.goto("https://creator.xiaohongshu.com/publish/publish")
        await page.wait_for_url("https://creator.xiaohongshu.com/publish/publish")
        # await page.goto("https://www.xiaohongshu.com")
        # await page.wait_for_url("https://www.xiaohongshu.com")
        # await page.get_by_text("上传图文").click()
        try:
            # await page.wait_for_selector("div.boards-more h3:text('抖音排行榜')", timeout=5000)  # 等待5秒
            await page.wait_for_selector("span.btn-content:text(' 登 录 ')", timeout=5000)
            print("cookie 失效")
            return False
        except:
            print("[+] cookie有效")
            return True
        finally:
            await page.close()
            await xhs_playwright_contex.close()


# 生成小红书创作中心cookie
async def xhs_creator_cookie_gen(xhs_creator_path):
    async with async_playwright() as playwright:
        # launch browser and create single browser context
        chromium = playwright.chromium
        # 为playwright操作小红书页面专门创建一个context
        # xhs_data_dir ="C:\\study\\python\\MediaCrawler\\browser_data\\xhs_user_data_dir" # type: ignore
        xhs_playwright_contex = await chromium.launch_persistent_context(
            user_data_dir=xhs_creator_path,
            headless=False,
        )
        page = await xhs_playwright_contex.new_page()
        await page.goto("https://creator.xiaohongshu.com/publish/publish")
        # await page.goto("https://www.xiaohongshu.com")
        # await page.wait_for_url("https://www.xiaohongshu.com")
        # await page.get_by_text("上传图文").click()
        await page.pause()
        # 点击调试器的继续，保存cookie
        await page.close()
        await xhs_playwright_contex.close()


# 判断抖音创作平台cookie是否有效
async def dy_creator_cookie_auth(dy_creator_path):
    async with async_playwright() as playwright:
        # launch browser and create single browser context
        chromium = playwright.chromium
        # 为playwright操作小红书页面专门创建一个context
        # xhs_data_dir ="C:\\study\\python\\MediaCrawler\\browser_data\\xhs_user_data_dir" # type: ignore
        dy_playwright_contex = await chromium.launch_persistent_context(
            user_data_dir=dy_creator_path,
            headless=True,
        )
        page = await dy_playwright_contex.new_page()
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        await page.wait_for_timeout(5000)
        # await page.goto("https://www.xiaohongshu.com")
        # await page.wait_for_url("https://www.xiaohongshu.com")
        # await page.get_by_text("上传图文").click()
        try:
            # await page.wait_for_selector("div.boards-more h3:text('抖音排行榜')", timeout=5000)  # 等待5秒
            await page.wait_for_selector("span.login:text('登录')", timeout=5000)
            print("抖音创作平台cookie 失效")
            return False
        except:
            print("[+] 抖音创作平台cookie有效")
            return True
        finally:
            await page.close()
            await dy_playwright_contex.close()


# 生成小抖音创作中心cookie
async def dy_creator_cookie_gen(dy_creator_path):
    async with async_playwright() as playwright:
        # launch browser and create single browser context
        chromium = playwright.chromium
        # 为playwright操作小红书页面专门创建一个context
        # xhs_data_dir ="C:\\study\\python\\MediaCrawler\\browser_data\\xhs_user_data_dir" # type: ignore
        xhs_playwright_contex = await chromium.launch_persistent_context(
            user_data_dir=dy_creator_path,
            headless=False,
        )
        page = await xhs_playwright_contex.new_page()
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        # await page.goto("https://www.xiaohongshu.com")
        # await page.wait_for_url("https://www.xiaohongshu.com")
        # await page.get_by_text("上传图文").click()
        await page.pause()
        # 点击调试器的继续，保存cookie
        await page.close()
        await xhs_playwright_contex.close()


async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8081)
    await site.start()
    async with async_playwright() as playwright:
        # launch browser and create single browser context
        chromium = playwright.chromium

        xhs_crawler.browser_context = await xhs_crawler.launch_browser(
            chromium,
            xhs_playwright_proxy,
            xhs_crawler.user_agent,
            headless=config.HEADLESS
        )

        # execute JS to bypass anti automation/crawler detection
        await xhs_crawler.browser_context.add_init_script(path="libs/stealth.min.js")
        # add a cookie attribute webId to avoid the appearance of a sliding captcha on the webpage
        if xhs_crawler.platform == "xhs" and xhs_crawler.login_type != "cookie":
            await xhs_crawler.browser_context.add_cookies([{
                'name': "webId",
                'value': "xxx123",  # any value
                'domain': ".xiaohongshu.com",
                'path': "/"
            }])
        xhs_crawler.context_page = await xhs_crawler.browser_context.new_page()
        await xhs_crawler.context_page.goto(xhs_crawler.index_url)

        # Create a client to interact with the xiaohongshu website.
        time.sleep(3)
        xhs_crawler.xhs_client = await xhs_crawler.create_xhs_client(xhs_httpx_proxy)
        if (
                xhs_crawler.platform == "xhs" and xhs_crawler.login_type == "cookie") or not await xhs_crawler.xhs_client.ping():
            xhs_cookie=await get_xhs_cookie_value()
            login_obj = XHSLogin(
                login_type=xhs_crawler.login_type,
                login_phone=xhs_account_phone,
                browser_context=xhs_crawler.browser_context,
                context_page=xhs_crawler.context_page,
                cookie_str=xhs_cookie
            )
            await login_obj.begin()
            await xhs_crawler.xhs_client.update_cookies(browser_context=xhs_crawler.browser_context)

        # Search for notes and retrieve their comment information.
        # await crawler.search_posts()
        try:
            print(await xhs_crawler.xhs_client.get_note_by_id("648912e70000000012033f1a"))
        except Exception as e:
            print(e)
        # ================为playwright操作小红书页面专门创建一个context
        # xhs_creator_data_dir = os.path.join(os.getcwd(), "browser_data",
        #                                     config.USER_DATA_DIR % "xhs_creator")
        # if not os.path.exists(xhs_creator_data_dir) or not await xhs_creator_cookie_auth(xhs_creator_data_dir):
        #     await xhs_creator_cookie_gen(xhs_creator_data_dir)

        dy_crawler.browser_context = await dy_crawler.launch_browser(
            chromium,
            dy_playwright_proxy,
            dy_crawler.user_agent,
            headless=config.HEADLESS
        )

        # execute JS to bypass anti automation/crawler detection
        await dy_crawler.browser_context.add_init_script(path="libs/stealth.min.js")
        dy_crawler.context_page = await dy_crawler.browser_context.new_page()
        await dy_crawler.context_page.goto(dy_crawler.index_url)
        dy_crawler.dy_client = await dy_crawler.create_douyin_client(dy_httpx_proxy)
        if not await dy_crawler.dy_client.ping(browser_context=dy_crawler.browser_context):
            login_obj = DouYinLogin(
                login_type=dy_crawler.login_type,
                login_phone=dy_account_phone,
                browser_context=dy_crawler.browser_context,
                context_page=dy_crawler.context_page,
                cookie_str=config.COOKIES
            )
            await login_obj.begin()
            await dy_crawler.dy_client.update_cookies(browser_context=dy_crawler.browser_context)
        # search_posts
        # s=await crawler.dy_client.get_video_by_id(aweme_id="7211398361495211264")
        # print(s)
        # await crawler.search()
        utils.logger.info("Douyin Crawler finished ...")

        # 为playwright操作抖音页面专门创建一个context
        # dy_creator_data_dir = os.path.join(os.getcwd(), "browser_data",
        #                                    config.USER_DATA_DIR % "dy_creator")
        # if not os.path.exists(dy_creator_data_dir) or not await dy_creator_cookie_auth(dy_creator_data_dir):
        #     await dy_creator_cookie_gen(dy_creator_data_dir)
        # block main crawler coroutine
        await asyncio.Event().wait()


class ResponseObject:
    def __init__(self, code, msg, data=None):
        self.code = code
        self.msg = msg
        self.data = data

    def to_dict(self):
        return {
            'code': self.code,
            'msg': self.msg,
            'data': self.data,
        }


@routes.get("/dy/{id}")
async def handle_dyid(request):
    id = request.match_info['id']
    # await crawler.start()
    # s=await crawler.start2(name)
    try:
        s = await dy_crawler.dy_client.get_video_by_id(id)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success", s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except DouyinDataFetchError as e:
        response = ResponseObject(1, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except DouyinIPBlockError as e:
        response = ResponseObject(2, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e:
        # print(f"Unexpected error: {e}")
        response = ResponseObject(3, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())


@routes.post("/create/dy/img")
async def create_dy_img(request):
    data = await request.json()
    title = data.get('title')
    position = data.get('position')
    music_theme = data.get('music_theme')
    desc = data.get('desc')
    print("desc:", desc)
    images = data.get('images')
    topics = data.get('topics')
    if title is None or title.strip() == '':
        response = ResponseObject(3, f"发布抖音图文的标题不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    if position is None or position.strip() == '':
        response = ResponseObject(3, f"发布抖音图文的定位不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    if music_theme is None or music_theme.strip() == '':
        response = ResponseObject(3, f"发布抖音图文的音乐主题不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    # 暂时不知道笔记内容能不能为空,暂时设为不得为空
    if desc is None or desc.strip() == '':
        response = ResponseObject(3, f"抖音图文内容不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    # 发布图文笔记,必须要有图片
    if images is None or not isinstance(images, list) or len(images) == 0:
        response = ResponseObject(3, "抖音图文图片数量不得为0")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    if any(not i or not isinstance(i, str) or i.strip() == '' for i in images):
        response = ResponseObject(3, "抖音图文的图片路径都不得为空或空串")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
        # 发布图文笔记,必须要有图片
    if topics is None or not isinstance(topics, list) or len(topics) == 0:
        response = ResponseObject(3, "抖音图文必须录入话题")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    if any(not i or not isinstance(i, str) or i.strip() == '' for i in topics):
        response = ResponseObject(3, "抖音图文的话题不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    desc_lines = desc.split('\n')
    async with async_playwright() as playwright:
        # launch browser and create single browser context
        chromium = playwright.chromium
        #chrome右键属性-快捷方式-目标 中添加启动参数 --remote - debugging - port = 5003
        browser = await chromium.connect_over_cdp('http://localhost:5003')
        dy_creator_context = browser.contexts[0]
        # dy_creator_data_dir = os.path.join(os.getcwd(), "browser_data",
        #                                    config.USER_DATA_DIR % "dy_creator")
        # dy_creator_context = await chromium.launch_persistent_context(
        #     user_data_dir=dy_creator_data_dir,
        #     headless=True,
        # )
        page = await dy_creator_context.new_page()
        page.set_default_timeout(180000)
        # images = [
        #     "C:\\study\\files\\genImg\\10.jpg",
        #     "C:\\study\\files\\genImg\\11.jpg",
        #     "C:\\study\\files\\genImg\\12.jpg",
        # ]
        # title="背景真不错"
        # desc = "很好看的背景图\n你值得拥有\n哈哈"
        # desc_lines = desc.split('\n')
        # topics=["租房","转租"]
        try:
            await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload")
            await page.locator('//div[text()="发布图文"]').click()
            await page.wait_for_timeout(100)
            async with page.expect_file_chooser() as fc_info:
                await page.locator('//div[contains(@class, "container--157qa")]').click()  # 点击上传附件按钮
                await page.wait_for_timeout(500)
                file_chooser = await fc_info.value
                await file_chooser.set_files(images)
            await page.wait_for_url(
                "https://creator.douyin.com/creator-micro/content/publish-media/image-text?enter_from=publish_page")
            # 等待图片上传结束
            await page.wait_for_timeout(10000)
            await page.fill('input[placeholder="添加作品标题"]', title)
            await page.wait_for_timeout(1000)
            await page.locator(".zone-container").click()
            for index, item in enumerate(desc_lines):
                if index != 0:
                    await page.keyboard.press("Enter")
                await page.keyboard.type(item)
            await page.keyboard.press("Enter")
            for tag in topics:
                await page.type(".zone-container", "#" + tag)
                await page.press(".zone-container", "Space")

            # await page.keyboard.type("很好看的背景图")
            # await page.keyboard.press("Enter")
            # await page.keyboard.type("你值得拥有")
            # await page.type(".zone-container", "#" + "背景图")
            # await page.press(".zone-container", "Space")
            await page.locator('//span[text()="选择音乐"]').click()
            await page.wait_for_timeout(2000)
            await page.fill('input[placeholder="搜索音乐"]', music_theme)
            await page.wait_for_timeout(4000)
            button_locator = page.locator('//button/span[text()="使用"]')
            music_amount = await button_locator.count()
            if music_amount > 0:
                # 获取第一个元素并点击
                await button_locator.nth(random.randint(0, music_amount - 1)).click()
            else:
                # 执行一次 选择乡村音乐
                await page.fill('input[placeholder="搜索音乐"]', "粤语")
                await page.wait_for_timeout(4000)
                button_locator = page.locator('//button/span[text()="使用"]')
                music_amount2 = await button_locator.count()
                if music_amount2 > 0:
                    # 获取第一个元素并点击
                    await button_locator.nth(random.randint(0, music_amount2 - 1)).click()
            await page.wait_for_timeout(2000)
            # await page.locator('//span[text()="输入相关位置，让更多人看到你的作品"]').click()
            await page.click('div.semi-select-selection >> text="输入相关位置，让更多人看到你的作品"')
            await page.wait_for_timeout(2000)
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type(position)
            await page.wait_for_timeout(2000)
            position_options = page.locator('div[role="listbox"] [role="option"]')
            if await position_options.count() > 0:
                await position_options.first.click()
            else:
                await page.keyboard.press("Backspace")
                await page.keyboard.press("Control+KeyA")
                await page.keyboard.press("Delete")
                await page.keyboard.type("武汉")
                await page.wait_for_timeout(2000)
                position_options2 = page.locator('div[role="listbox"] [role="option"]')
                if await position_options2.count() > 0:
                    await position_options2.first.click()
            # 判断图文是否发布成功
            page.on('response', on_response)
            publish_button = page.get_by_role('button', name="发布", exact=True)
            if await publish_button.count():
                await publish_button.click()
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage",
                                    timeout=30000)  # 如果自动跳转到作品页面，则代表发布成功
            await page.wait_for_timeout(20000)
            # 总是拿不到拦截请求的数据,因此重新访问一次
            await page.goto("https://creator.douyin.com/creator-micro/content/manage",
                                    timeout=30000)
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage",
                                    timeout=30000)
            await page.wait_for_timeout(20000)
            response = ResponseObject(0, "Success", dy_creator_info)
            return web.json_response(response.to_dict())
        except Exception as e:
            response = ResponseObject(3, f"{e}")
            return web.json_response(response.to_dict())
        finally:
            await page.close()



@routes.post("/create/xhs/img")
async def create_xhs_img(request):
    data = await request.json()
    title = data.get('title')
    position = data.get('position')
    desc = data.get('desc')
    images = data.get('images')
    topics = data.get('topics')
    if title is None or title.strip() == '':
        response = ResponseObject(3, f"发布小红书图文的标题不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    if position is None or position.strip() == '':
        response = ResponseObject(3, f"发布小红书图文的定位不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    # 暂时不知道笔记内容能不能为空,暂时设为不得为空
    if desc is None or desc.strip() == '':
        response = ResponseObject(3, f"抖音小红书内容不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    # 发布图文笔记,必须要有图片
    if images is None or not isinstance(images, list) or len(images) == 0:
        response = ResponseObject(3, "小红书图片数量不得为0")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    if any(not i or not isinstance(i, str) or i.strip() == '' for i in images):
        response = ResponseObject(3, "小红书图文的图片路径都不得为空或空串")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
        # 发布图文笔记,必须要有图片
    if topics is None or not isinstance(topics, list) or len(topics) == 0:
        response = ResponseObject(3, "小红书图文必须录入话题")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    if any(not i or not isinstance(i, str) or i.strip() == '' for i in topics):
        response = ResponseObject(3, "小红书图文的话题不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    desc_lines = desc.split('\n')

    async with async_playwright() as playwright:
        # launch browser and create single browser context
        chromium = playwright.chromium
        #chrome右键属性-快捷方式-目标 中添加启动参数 --remote - debugging - port = 5003
        browser = await chromium.connect_over_cdp('http://localhost:5003')
        xhs_creator_context = browser.contexts[0]
        # xhs_creator_data_dir = os.path.join(os.getcwd(), "browser_data",
        #                                     config.USER_DATA_DIR % "xhs_creator")
        # xhs_creator_context = await chromium.launch_persistent_context(
        #     user_data_dir=xhs_creator_data_dir,
        #     headless=True,
        # )
        page = await xhs_creator_context.new_page()
        page.set_default_timeout(180000)
        # images = [
        #     "C:\\study\\files\\genImg\\10.jpg",
        #     "C:\\study\\files\\genImg\\11.jpg",
        #     "C:\\study\\files\\genImg\\12.jpg",
        # ]
        # title="背景真不错"
        # desc = "很好看的背景图\n你值得拥有\n哈哈"
        # desc_lines = desc.split('\n')
        # topics=["租房","转租"]
        try:
            await page.goto("https://creator.xiaohongshu.com/publish/publish")
            await page.wait_for_url("https://creator.xiaohongshu.com/publish/publish")
            await page.get_by_text("上传图文").click()
            await page.wait_for_timeout(100)
            await page.locator('div.upload-container input.upload-input').set_input_files(images)
            await page.wait_for_timeout(10000)
            # input_locator = page.locator('.c-input_inner')
            # if await input_locator.count() == 0:
            #     print("页面变化失败")
            #     return
            await page.locator('.c-input_inner').fill(title)
            await page.wait_for_timeout(100)
            await page.locator('#post-textarea').click()
            await page.wait_for_timeout(100)
            for index, item in enumerate(desc_lines):
                if index != 0:
                    await page.keyboard.press("Enter")
                await page.keyboard.type(item)
            await page.keyboard.press("Enter")
            for tag in topics:
                await page.keyboard.press("Space")
                await page.keyboard.type("#" + tag)
                await page.wait_for_timeout(2000)
                li_locator = page.locator('li.publish-highlight')
                if await li_locator.count():
                    await li_locator.click()
                    await page.wait_for_timeout(100)
            await page.locator('.single-input[type="text"]').click()
            await page.locator('.single-input[type="text"]').click()
            await page.wait_for_timeout(100)
            await page.locator('.single-input[type="text"]').fill(position)
            await page.wait_for_timeout(2000)
            ul_locator = page.locator('ul.dropdown')
            # 检查 ul 是否存在
            if await ul_locator.count():
                # 选择第一个 li 元素并点击
                await page.locator('ul.dropdown li').nth(0).click()
            else:
                await page.locator('.single-input[type="text"]').fill("武汉")
                await page.wait_for_timeout(2000)
                ul_locator2 = page.locator('ul.dropdown')
                if await ul_locator2.count():
                    await page.locator('ul.dropdown li').nth(0).click()
            await page.locator('.publishBtn').click()
            await page.wait_for_url("https://creator.xiaohongshu.com/publish/publish", timeout=15000)
            page.on('response', on_response)
            await page.goto('https://creator.xiaohongshu.com/creator/notemanage', timeout=30000)
            await page.wait_for_url("https://creator.xiaohongshu.com/creator/notemanage", timeout=30000)
            await page.wait_for_timeout(15000)
            response = ResponseObject(0, "Success", xhs_creator_info)
            return web.json_response(response.to_dict())
        except Exception as e:
            response = ResponseObject(3, f"{e}")
            return web.json_response(response.to_dict())
        finally:
            await page.close()


@routes.get("/note/{id}")
async def handle_noteid(request):
    id = request.match_info['id']
    # await crawler.start()
    # s=await crawler.start2(name)
    try:
        s = await xhs_crawler.xhs_client.get_note_by_id(id)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success", s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e:
        # print(f"Unexpected error: {e}")
        response = ResponseObject(3, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())


@routes.get("/notes/keyword")
async def handle_keyword(request):
    # 获取查询参数，request.query是一个MultiDictProxy对象，我们可以向字典一样操作它
    params = request.query
    keyword = params.get("keyword")  # 使用get方法，如果不存在该key值，会返回None
    page = params.get("page")  # 使用get方法，如果不存在该key值，会返回None
    if keyword is None:
        response = ResponseObject(3, "参数非法")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    if page is None:
        response = ResponseObject(3, "参数非法")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    try:
        s = await xhs_crawler.xhs_client.get_note_by_keyword(keyword=keyword, page=page,
                                                             sort=field.SearchSortType.LATEST)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success", s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e:
        # print(f"Unexpected error: {e}")
        response = ResponseObject(3, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())


@routes.get("/xhs/img/none/wm")
async def xhs_no_wm_img(request):
    # 获取查询参数，request.query是一个MultiDictProxy对象，我们可以向字典一样操作它
    params = request.query
    link = params.get("link")  # 使用get方法，如果不存在该key值，会返回None
    if link is None:
        response = ResponseObject(3, "参数非法")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())

    async with async_playwright() as playwright:
        chromium = playwright.chromium
        # chrome右键属性-快捷方式-目标 中添加启动参数 --remote - debugging - port = 5003
        browser = await chromium.connect_over_cdp('http://localhost:5003')
        context = browser.contexts[0]
        # xhs_data_dir = os.path.join(os.getcwd(), "browser_data",
        #                                     config.USER_DATA_DIR % "xhs")
        # context = await chromium.launch_persistent_context(
        #     user_data_dir=xhs_data_dir,
        #     headless=True,
        # )
        page = await context.new_page()
        # 定义要监听的域名
        target_domain = 'sns-webpic-qc.xhscdn.com'
        # 存储拦截到的URL的数组
        intercepted_urls = []
        # 监听页面的所有响应
        def response_handler(response):
            url = response.url
            # 检查响应的 URL 是否包含目标域名
            if target_domain in url:
                # 在这里可以处理符合条件的响应，比如获取内容、存储数据等操作
                # 将URL添加到数组中
                intercepted_urls.append(url)

        page.on('response', response_handler)
        try:
            await page.goto(link, timeout=18000)
            await page.wait_for_timeout(10000)
            redirect_url= urlparse(page.url)
            if '/explore' == redirect_url.path :
                intercepted_urls = []
            response = ResponseObject(0, "Success", intercepted_urls)
            # 转换为 JSON 字符串
            return web.json_response(response.to_dict())
        except Exception as e:
            # print(f"Unexpected error: {e}")
            response = ResponseObject(3, f"{e}")
            # 转换为 JSON 字符串
            return web.json_response(response.to_dict())
        finally:
            await page.close()


@routes.post("/notes/comment")
async def comment_note(request):
    data = await request.json()
    note_id = data.get('note_id')
    content = data.get('content')
    # await crawler.start()
    # s=await crawler.start2(name)
    try:
        s = await xhs_crawler.xhs_client.comment_note(note_id, content)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success", s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e:
        # print(f"Unexpected error: {e}")
        response = ResponseObject(3, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())


@routes.post("/api/create/xhs/img")
async def create_img_note(request):
    data = await request.json()
    title = data.get('title')
    desc = data.get('desc')
    images = data.get('images')

    if title is None or title.strip() == '':
        response = ResponseObject(3, f"发布笔记的标题不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    # 暂时不知道笔记内容能不能为空,暂时设为不得为空
    if desc is None or desc.strip() == '':
        response = ResponseObject(3, f"笔记内容不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    # 发布图文笔记,必须要有图片
    if images is None or not isinstance(images, list) or len(images) == 0:
        response = ResponseObject(3, "图片数量不得为0")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    if any(not i or not isinstance(i, str) or i.strip() == '' for i in images):
        response = ResponseObject(3, "所有的图片路径都不得为空或空串")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    is_private = data.get('is_private', False)
    # 没有找到键值时默认就会返回 None，时间格式为2023-07-25 23:59:59
    post_time = data.get('post_time')
    ats = data.get('ats')
    topics = data.get('topics')
    try:
        s = await xhs_crawler.xhs_client.create_image_note(title, desc, images, is_private=is_private,
                                                           post_time=post_time, ats=ats, topics=topics)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success", s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e:
        # print(f"Unexpected error: {e}")
        response = ResponseObject(3, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())


@routes.get("/notes/topic")
async def get_note_topic(request):
    # 获取查询参数，request.query是一个MultiDictProxy对象，我们可以向字典一样操作它
    params = request.query
    keyword = params.get("keyword")  # 使用get方法，如果不存在该key值，会返回None
    if keyword is None:
        response = ResponseObject(3, "参数非法")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    try:
        s = await xhs_crawler.xhs_client.get_suggest_topic(keyword)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success", s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e:
        # print(f"Unexpected error: {e}")
        response = ResponseObject(3, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())


@routes.get("/notes/at")
async def get_note_at(request):
    # 获取查询参数，request.query是一个MultiDictProxy对象，我们可以向字典一样操作它
    params = request.query
    keyword = params.get("keyword")  # 使用get方法，如果不存在该key值，会返回None
    if keyword is None:
        response = ResponseObject(3, "参数非法")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    try:
        s = await xhs_crawler.xhs_client.get_suggest_ats(keyword)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success", s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e:
        # print(f"Unexpected error: {e}")
        response = ResponseObject(3, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())



@routes.get("/start/colab/{account}")
async def start_colab(request):
    account = request.match_info['account']
    command = [
        'chrome',
        '--remote-debugging-port=5005',
        '--disable-web-security',
        '--profile-directory="Default"',
    ]
    remote_url = "http://localhost:5005"
    colab_url = "https://colab.research.google.com/drive/1Z_Ucp_IHlrzGSNoxBlNFQUQNgQL2y-FM"
    if account == "2018" :
        command = [
            'chrome',
            '--remote-debugging-port=5005',
            '--disable-web-security',
            '--profile-directory="Profile 2"',
        ]
        remote_url = "http://localhost:5005"
        colab_url = "https://colab.research.google.com/drive/1grScLTMBQuUm6UvCw6dSY5jfkNashT6E"
    # 使用 subprocess 启动 Chrome，不等待进程结束
    subprocess.Popen(' '.join(command), shell=True)
    time.sleep(10)
    async with async_playwright() as p:
        try:
            chromium = p.chromium
            browser = await chromium.connect_over_cdp(remote_url)
            context = browser.contexts[0]
            # 设置你要获取 cookie 的域名
            page = await context.new_page()
            cdp_session = await context.new_cdp_session(page)
            # 发送 CDP 命令来设置下载路径
            await cdp_session.send('Browser.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': "C:\\study\\files\\audio",
            })
            await page.goto(colab_url)
            await page.wait_for_url(colab_url)
            # 使用 id 选择器找到元素
            element = page.locator('#connect')
            while element is None:
                print('等待元素...')
                await page.wait_for_timeout(3000)
                element = page.locator('#connect')
            await page.click('#connect')
            await page.wait_for_timeout(10000)
            tooltip_text =await element.get_attribute('tooltiptext')
            while '已连接' not in tooltip_text:
                await page.click('#connect')
                await page.wait_for_timeout(10000)
                tooltip_text =await element.get_attribute('tooltiptext')
            await page.click('paper-input[aria-labelledby="formwidget-1-label"]')
            await page.wait_for_timeout(2000)
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type("你好啊啊啊啊啊")
            await page.wait_for_timeout(2000)
            await page.click('paper-input[aria-labelledby="formwidget-3-label"]')
            await page.wait_for_timeout(2000)
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type("start")
            await page.wait_for_timeout(2000)
            # 执行全部代码大约需要四分钟
            await page.keyboard.press("Control+F9")
            # 只执行最后一步生成音频大约需要1分钟
            # await page.keyboard.press("Control+Enter")
            #通过判断下载文件夹是否存在文件确认是否执行结束
            response = ResponseObject(0, "Success")
            return web.json_response(response.to_dict())
        except Exception as e:
            response = ResponseObject(3, f"{e}")
            return web.json_response(response.to_dict())


@routes.post("/generate/audio")
async def generate_audio(request):
    data = await request.json()
    text = data.get('text')
    file_name = data.get('file_name')
    if text is None or text.strip() == '':
        response = ResponseObject(3, f"语音内容不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    if file_name is None or file_name.strip() == '':
        response = ResponseObject(3, f"语音文件名称不得为空")
        # 转换为 JSON 字符串
        return web.json_response(response.to_dict())
    async with async_playwright() as p:
        try:
            chromium = p.chromium
            browser = await chromium.connect_over_cdp("http://localhost:5005")
            context = browser.contexts[0]
            # 获取所有页面
            all_pages = context.pages
            # 选择包含特定域名的页面
            selected_pages = [page for page in all_pages if 'colab.research.google.com' in page.url]
            # 如果有符合条件的页面，取第一个页面进行操作
            if not selected_pages:
                response = ResponseObject(3, f"没有colab页面可供生成语音")
                # 转换为 JSON 字符串
                return web.json_response(response.to_dict())
            page = selected_pages[0]
            await page.click('paper-input[aria-labelledby="formwidget-1-label"]')
            await page.wait_for_timeout(2000)
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type(text)
            await page.wait_for_timeout(2000)
            await page.click('paper-input[aria-labelledby="formwidget-3-label"]')
            await page.wait_for_timeout(2000)
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type(file_name)
            await page.wait_for_timeout(2000)
            # 执行全部代码大约需要四分钟
            # await page.keyboard.press("Control+F9")
            # 只执行最后一步生成音频大约需要1分钟
            await page.keyboard.press("Control+Enter")
            #通过判断下载文件夹是否存在文件确认是否执行结束
            response = ResponseObject(0, "Success")
            return web.json_response(response.to_dict())
        except Exception as e:
            response = ResponseObject(3, f"{e}")
            return web.json_response(response.to_dict())




app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    try:
        command = [
            'chrome',
            '--remote-debugging-port=5003',
            '--disable-web-security',
            '--profile-directory="Default"',
        ]
        # 使用 subprocess 启动 Chrome，不等待进程结束
        subprocess.Popen(' '.join(command), shell=True)
        time.sleep(10)
        asyncio.run(main())
    except KeyboardInterrupt:
        asyncio.run(dy_crawler.close())
        asyncio.run(xhs_crawler.close())
        sys.exit()
    except Exception as e:
        print(f"Unexpected error: {e}")
        asyncio.run(dy_crawler.close())
        asyncio.run(xhs_crawler.close())
        sys.exit()
