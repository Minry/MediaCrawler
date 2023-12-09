import json
import sys
import asyncio
import argparse

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


routes = web.RouteTableDef()
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
    login_type="qrcode",
    account_pool=account_pool
)
xhs_account_phone, xhs_playwright_proxy, xhs_httpx_proxy = xhs_crawler.create_proxy_info()




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
        if xhs_crawler.platform =="xhs" and xhs_crawler.login_type != "cookie"  :
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
        if (xhs_crawler.platform =="xhs" and xhs_crawler.login_type == "cookie" ) or not await xhs_crawler.xhs_client.ping():
            login_obj = XHSLogin(
                login_type=xhs_crawler.login_type,
                login_phone=xhs_account_phone,
                browser_context=xhs_crawler.browser_context,
                context_page=xhs_crawler.context_page,
                cookie_str=config.COOKIES
            )
            await login_obj.begin()
            await xhs_crawler.xhs_client.update_cookies(browser_context=xhs_crawler.browser_context)

        # Search for notes and retrieve their comment information.
        # await crawler.search_posts()
        print(await xhs_crawler.xhs_client.get_note_by_id("648912e70000000012033f1a"))

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
    try :
        s=await dy_crawler.dy_client.get_video_by_id(id)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success",s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except DouyinDataFetchError as e:
        response = ResponseObject(1,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except DouyinIPBlockError as e:
        response = ResponseObject(2,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e :
        # print(f"Unexpected error: {e}")
        response = ResponseObject(3, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())



@routes.get("/note/{id}")
async def handle_noteid(request):
    id = request.match_info['id']
    # await crawler.start()
    # s=await crawler.start2(name)
    try :
        s=await xhs_crawler.xhs_client.get_note_by_id(id)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success",s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e :
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
    try :
        s=await xhs_crawler.xhs_client.get_note_by_keyword(keyword=keyword,page=page,sort=field.SearchSortType.LATEST)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success",s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e :
        # print(f"Unexpected error: {e}")
        response = ResponseObject(3, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())



@routes.post("/notes/comment")
async def comment_note(request):
    data = await request.json()
    note_id = data.get('note_id')
    content = data.get('content')
    # await crawler.start()
    # s=await crawler.start2(name)
    try :
        s=await xhs_crawler.xhs_client.comment_note(note_id,content)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success",s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e :
        # print(f"Unexpected error: {e}")
        response = ResponseObject(3, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())



@routes.post("/notes/img/create")
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
    ats=data.get('ats')
    topics=data.get('topics')
    try:
        s = await xhs_crawler.xhs_client.create_image_note(title, desc, images, is_private=is_private, post_time=post_time,ats=ats,topics=topics)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success", s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e :
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
    try :
        s=await xhs_crawler.xhs_client.get_suggest_topic(keyword)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success",s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e :
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
    try :
        s=await xhs_crawler.xhs_client.get_suggest_ats(keyword)
        # 创建 ResponseObject 对象
        response = ResponseObject(0, "Success",s)
        # 转换为 JSON 字符串
        # json_str = json.dumps(response.__dict__)
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsDataFetchError as e:
        response = ResponseObject(1,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except XhsIPBlockError as e:
        response = ResponseObject(2,f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())
    except Exception as e :
        # print(f"Unexpected error: {e}")
        response = ResponseObject(3, f"{e}")
        # 转换为 JSON 字符串
        print(response.to_dict())
        return web.json_response(response.to_dict())



app = web.Application()
app.add_routes(routes)

if __name__ == '__main__':
    try:
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
