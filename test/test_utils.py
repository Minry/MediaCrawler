# -*- coding: utf-8 -*-
import os
import random

import pytest
from playwright.async_api import async_playwright

from tools import utils


def test_convert_cookies():
    xhs_cookies = "a1=x000101360; webId=1190c4d3cxxxx125xxx; "
    cookie_dict = utils.convert_str_cookie_to_dict(xhs_cookies)
    assert cookie_dict.get("webId") == "1190c4d3cxxxx125xxx"
    assert cookie_dict.get("a1") == "x000101360"


pytestmark = pytest.mark.asyncio


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
        dy_data_dir = "C:\\study\\python\\MediaCrawler\\browser_data\\dy_user_data_dir"  # type: ignore
        dy_playwright_contex = await chromium.launch_persistent_context(
            user_data_dir=dy_data_dir,
            headless=False,
        )
        page = await dy_playwright_contex.new_page()
        images = ["C:\\study\\files\\genImg\\publish\\640_960\\2023-12-13\\366.png",
                  "C:\\study\\files\\origin_media\\2023-12-13\\366\\0.jpg"]
        title = "【转租群】武汉洪山区湖工大转租"
        position = "洪山区板桥新村"
        music_theme = "乡村音乐"
        desc = "转租洪山区板桥新村(八一桥北200米)的次卧。\n位置在武汉市洪山区南李路。\n之前的租期签到了24年7月10号，可以短租。\n2室2厅1厨1卫，次卧招合租，主卧是本人，可以养宠物，电梯房，楼下有小吃街，药店超市，奶茶店都有，要求合租人爱卫生，无不良嗜好。次卧可以短租2个月或者更长时间。"
        desc_lines = desc.split('\n')
        topics = ["租房", "转租"]
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

            for tag in topics:
                await page.type(".zone-container", "#" + tag)
                await page.press(".zone-container", "Space")

            # await page.keyboard.type("很好看的背景图")
            # await page.keyboard.press("Enter")
            # await page.keyboard.type("你值得拥有")
            # await page.type(".zone-container", "#" + "背景图")
            # await page.press(".zone-container", "Space")
            await page.locator('//span[text()="选择音乐"]').click()
            await page.wait_for_timeout(1000)
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
                    await button_locator.nth(random.randint(0, music_amount - 1)).click()
            await page.wait_for_timeout(1000)
            # await page.locator('//span[text()="输入相关位置，让更多人看到你的作品"]').click()
            await page.click('div.semi-select-selection >> text="输入相关位置，让更多人看到你的作品"')
            await page.wait_for_timeout(1000)
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type(position)
            await page.wait_for_timeout(1500)
            position_options = page.locator('div[role="listbox"] [role="option"]')
            if await position_options.count() > 0:
                await position_options.first.click()
            else:
                await page.keyboard.press("Backspace")
                await page.keyboard.press("Control+KeyA")
                await page.keyboard.press("Delete")
                await page.keyboard.type("武汉")
                await page.wait_for_timeout(1500)
                position_options2 = page.locator('div[role="listbox"] [role="option"]')
                if await position_options2.count() > 0:
                    await position_options2.first.click()
            # page.on('response', on_response)
            # 判断图文是否发布成功
            count = 0
            while True:
                # 判断图文是否发布成功
                try:
                    if count == 10:
                        # response = ResponseObject(3, "尝试10轮依旧无法点击发布")
                        return
                    count = count + 1
                    publish_button = page.get_by_role('button', name="发布", exact=True)
                    if await publish_button.count():
                        await publish_button.click()
                        await page.wait_for_timeout(10000)
                    await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage",
                                            timeout=1500)  # 如果自动跳转到作品页面，则代表发布成功
                    print("  [-]抖音图文发布成功")
                    break
                except:
                    print("  [-] 抖音正在发布中...")
                    await page.screenshot(full_page=True)
                    await page.wait_for_timeout(1500)
            await page.wait_for_load_state('networkidle')
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
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
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
        await page.goto("http://xhslink.com/21sGtx", timeout=18000)
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
