# -*- coding: utf-8 -*-
import os
import random
import time
from urllib.parse import urlparse
import subprocess

import pytest
from playwright.async_api import async_playwright

from tools import utils
from pyee import EventEmitter

pytestmark = pytest.mark.asyncio
def test_convert_cookies():
    xhs_cookies = "a1=x000101360; webId=1190c4d3cxxxx125xxx; "
    cookie_dict = utils.convert_str_cookie_to_dict(xhs_cookies)
    assert cookie_dict.get("webId") == "1190c4d3cxxxx125xxx"
    assert cookie_dict.get("a1") == "x000101360"





async def test_example1() -> None:
    # asyncio.run(douyin_setup(account_file, handle=True))
    async with async_playwright() as playwright:
        # launch browser and create single browser context
        chromium = playwright.chromium
        # 为playwright操作小红书页面专门创建一个context
        xhs_data_dir = "C:\\study\\python\\MediaCrawler\\browser_data\\xhs_creator_user_data_dir"  # type: ignore
        xhs_playwright_contex = await chromium.launch_persistent_context(
            user_data_dir=xhs_data_dir,
            headless=True,
        )
        page = await xhs_playwright_contex.new_page()
        await page.goto("https://creator.xiaohongshu.com/publish/publish")
        await page.wait_for_url("https://creator.xiaohongshu.com/publish/publish")
        await page.pause()
        # await page.goto("https://www.xiaohongshu.com")
        # await page.wait_for_url("https://www.xiaohongshu.com")
        # await page.get_by_text("上传图文").click()
        await page.click("span.btn-content:text(' 登 录 ')")


async def test_example2() -> None:
    async with async_playwright() as playwright:
        # launch browser and create single browser context
        chromium = playwright.chromium
        dy_data_dir = os.path.join(os.getcwd(), "browser_data", "dy_user_data_dir")  # type: ignore
        dy_data_dir = "C:\\study\\python\\MediaCrawler\\browser_data\\dy_creator_user_data_dir"  # type: ignore
        dy_playwright_contex = await chromium.launch_persistent_context(
            user_data_dir=dy_data_dir,
            headless=False,
        )
        page = await dy_playwright_contex.new_page()
        page.set_default_timeout(180000)
        images = ["C:\\study\\files\\genImg\\publish\\640_960\\2023-12-19\\386.png"]
        title = "【转租群】三室一厅次卧一口价"
        position = "武汉美的·君兰半岛"
        music_theme = "粤语"
        desc = "【租他人之急，转你我之需】\n\n转租【美的·君兰半岛】的次卧。\n\n位置在武汉市江夏区黄家湖大道地铁8号线。\n\n之前的租期签到了25年12月17号，可以短租。\n\n一口价房租 包水电燃气网络物业费 提供洗发水沐浴露护发素牙膏洗衣液洗手液垃圾袋 全屋软水 即热饮水机 洗烘一体洗衣机 2w冰箱 3k吹风机 家电齐全 拎包入住"
        desc_lines = desc.split('\n')
        topics = ["租房", "转租","武汉租房"]
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
            await page.wait_for_timeout(2000)
            button_locator = page.locator('//button/span[text()="使用"]')
            music_amount = await button_locator.count()
            if music_amount > 0:
                # 获取第一个元素并点击
                await button_locator.nth(random.randint(0, music_amount - 1)).click()
            else:
                # 执行一次 选择乡村音乐
                await page.fill('input[placeholder="搜索音乐"]', "乡村音乐")
                await page.wait_for_timeout(2000)
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
            # input_element = page.locator('//input[@class="semi-input semi-input-default" and @type="text"]')
            # await input_element.fill(position)
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
            # page.on('response', on_response)
            # publish_button = page.get_by_role('button', name="发布", exact=True)
            # if await publish_button.count():
            #     await publish_button.click()
            # await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage",
            #                         timeout=30000)  # 如果自动跳转到作品页面，则代表发布成功
            # await page.wait_for_timeout(20000)
            # # 总是拿不到拦截请求的数据,因此重新访问一次
            # await page.goto("https://creator.douyin.com/creator-micro/content/manage",
            #                 timeout=30000)
            # await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage",
            #                         timeout=30000)
            # await page.wait_for_timeout(20000)
        except:
            print("  [-] 抖音发布失败")


a = None
xhs_creator_info = None
dy_creator_info = None


async def on_response(response):
    if '/web/api/media/aweme/post' in response.url and response.status == 200:
        global dy_creator_info
        dy_creator_info = await response.json()
        return
    if '/api/galaxy/creator/note/user/posted' in response.url and response.status == 200:
        global xhs_creator_info
        xhs_creator_info = await response.json()
        return


async def on_response2(response):
    if '/sugrec' in response.url and response.status == 200:
        global a
        a = await response.json()


async def test_example3() -> None:
    async with async_playwright() as playwright:
        options = {
            'headless': True
        }
        # Make sure to run headed.
        chromium = playwright.chromium
        # Setup context however you like.
        context = await chromium.launch_persistent_context(
            user_data_dir="C:\\study\\python\\MediaCrawler\\browser_data\\xhs_user_data_dir",
            headless=True,
        ) # Pass any options
        # Pause the page, and start recording manually.
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
                print(f'Response URL: {url}')
                # 在这里可以处理符合条件的响应，比如获取内容、存储数据等操作
                # 将URL添加到数组中
                intercepted_urls.append(url)

        page.on('response', response_handler)
        await page.goto("http://xhslink.com/n2dhty", timeout=18000)
        await page.wait_for_timeout(10000)
        s = a
        print("获取到的a的值为:", a)


async def test_example4() -> None:
    async with async_playwright() as playwright:
        # Make sure to run headed.
        browser = playwright.chromium
        # Setup context however you like.
        xhs_creator_context = await browser.launch_persistent_context(
            user_data_dir="C:\\study\\python\\MediaCrawler\\browser_data\\xhs_creator_user_data_dir",
            headless=False,
        )  # Pass any options
        # Pause the page, and start recording manually.
        page = await xhs_creator_context.new_page()
        page.set_default_timeout(180000)
        page.on('response', on_response)
        await page.goto("https://creator.xiaohongshu.com/creator/notemanage")
        await page.wait_for_url("https://creator.xiaohongshu.com/creator/notemanage", timeout=30000)
        await page.wait_for_timeout(15000)
        page.remove_listener("response", on_response)
        s = xhs_creator_info
        print("获取到的a的值为:", s)


async def test_example5() -> None:
    async with async_playwright() as playwright:
        # Make sure to run headed.
        browser = playwright.chromium
        # Setup context however you like.
        dy_creator_context = await browser.launch_persistent_context(
            user_data_dir="C:\\study\\python\\MediaCrawler\\browser_data\\dy_creator_user_data_dir",
            headless=False,
        )  # Pass any options
        # Pause the page, and start recording manually.
        page = await dy_creator_context.new_page()
        page.set_default_timeout(180000)
        page.on('response', on_response)
        await page.goto("https://creator.douyin.com/creator-micro/content/manage")
        await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage", timeout=30000)
        await page.wait_for_timeout(15000)
        page.remove_listener("response", on_response)
        s = dy_creator_info
        print("获取到的a的值为:", s)



async def test_example6_1() -> None:
    async with async_playwright() as p:
        chromium = p.chromium
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

        else:
            print(f"Cookie 'web_session' not found for {target_domain}")
        await browser.close()


async def test_example6_3() -> None:
    async with async_playwright() as p:
        chromium = p.chromium
        browser = await chromium.connect_over_cdp('http://localhost:5003')
        context = browser.contexts[0]
        page = await context.new_page()
        link='http://xhslink.com/fYSlLy'
        await page.goto(link, timeout=18000)
        await page.wait_for_timeout(10000)
        a=page.url
        redirect_url = urlparse(page.url)
        b=redirect_url.path
        print(a,b)

async def test_example6_2() -> None:
    async with async_playwright() as p:
        chromium = p.chromium
        browser = await chromium.connect_over_cdp('http://localhost:5003')
        context = browser.contexts[0]
        # 获取查询参数，request.query是一个MultiDictProxy对象，我们可以向字典一样操作它
        link = 'https://www.xiaohongshu.com/discovery/item/658d8e8e000000001d031c1d'
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
            target_url = 'edith.xiaohongshu.com/api/sns/web/v1/feed'
            def response_handler(response):
                url = response.url
                print(url)
                # 检查响应的 URL 是否包含目标域名
                if target_url in url:
                    # 在这里可以处理符合条件的响应，比如获取内容、存储数据等操作
                    # 将URL添加到数组中
                    print(response.json())
                    print(f"URL: {url}")
            page.on('response', response_handler)
            try:
                await page.goto(link, timeout=18000)
                await page.wait_for_timeout(10000)
                # response = ResponseObject(0, "Success", intercepted_urls)
                # 转换为 JSON 字符串
            except Exception as e:
                print(f"Unexpected error: {e}")
                # response = ResponseObject(3, f"{e}")
                # # 转换为 JSON 字符串
                # return web.json_response(response.to_dict())
            # finally:
                # await page.close()

async def test_example6() -> None:
    dy_creator_data_dir ="C:\\study\\python\\MediaCrawler\\browser_data\\dy_creator_user_data_dir"
    async with async_playwright() as playwright:
        # launch browser and create single browser context
        chromium = playwright.chromium
        # 为playwright操作小红书页面专门创建一个context
        # xhs_data_dir ="C:\\study\\python\\MediaCrawler\\browser_data\\xhs_user_data_dir" # type: ignore
        xhs_playwright_contex = await chromium.launch_persistent_context(
            user_data_dir=dy_creator_data_dir,
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

# 获取派蒙语音
async def test_pimon() -> None:

    # 使用 subprocess 执行命令
    command = [
        'chrome',
        '--remote-debugging-port=5005',
        '--profile-directory="Profile 2"'
    ]

    # 使用 subprocess 启动 Chrome，不等待进程结束
    subprocess.Popen(' '.join(command), shell=True)
    time.sleep(10)
    async with async_playwright() as p:
        chromium = p.chromium
        browser = await chromium.connect_over_cdp('http://localhost:5005')
        context = browser.contexts[0]
        # 设置你要获取 cookie 的域名
        page = await context.new_page()
        cdp_session = await context.new_cdp_session(page)
        # 发送 CDP 命令来设置下载路径
        await cdp_session.send('Browser.setDownloadBehavior', {
            'behavior': 'allow',
            'downloadPath': "C:\\study\\files\\audio",
        })

        # 定义要监听的域名
        target_url = 'https://colab.research.google.com/drive/1grScLTMBQuUm6UvCw6dSY5jfkNashT6E'
        try:
            await page.goto(target_url)
            await page.wait_for_url(target_url)
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
            await page.keyboard.type("test10")
            await page.wait_for_timeout(2000)
            # 执行全部代码大约需要四分钟
            await page.keyboard.press("Control+F9")
            # 只执行最后一步生成音频大约需要1分钟
            # await page.keyboard.press("Control+Enter")
            #通过判断下载文件夹是否存在文件确认是否执行结束

            # await page.pause()
        except Exception as e:
            print(e)
        # await page.pause()


async def test_pimon2() -> None:
    text ="今天天气真不错啊！"
    file_name ="测试"
    async with async_playwright() as p:
        chromium = p.chromium
        browser = await chromium.connect_over_cdp("http://localhost:5005")
        context = browser.contexts[0]
        # 获取所有页面
        all_pages = context.pages
        # 选择包含特定域名的页面
        selected_pages = [page for page in all_pages if 'colab.research.google.com' in page.url]
        # 如果有符合条件的页面，取第一个页面进行操作
        if not selected_pages:
            print( "没有colab页面可供生成语音")
            return
        try:
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
        except Exception as  e :
            print(e)




async def test_pimon3() -> None:
    command = [
        'chrome',
        '--remote-debugging-port=5005',
        '--user-data-dir=C:\\Users\\Administrator\\AppData\\Local\\Google\\Chrome\\AccountInfo',
        # '--profile-directory=C:\\Users\\Administrator\\AppData\\Local\\Google\\Chrome\\AccountInfo\\Default'
        '--profile-directory="Profile 4"'
    ]

    # 使用 subprocess 启动 Chrome，不等待进程结束
    # subprocess.Popen(' '.join(command), shell=True)
    profile_directory="Profile 4"
    print(f'--profile-directory="{profile_directory}"')