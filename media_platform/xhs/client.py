import asyncio
import json
import time
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

import aiofiles
import httpx
from playwright.async_api import BrowserContext, Page

from tools import utils

from .exception import DataFetchError, IPBlockError
from .field import SearchNoteType, SearchSortType
from .help import get_search_id, sign

class NoteType(Enum):
    NORMAL = "normal"
    VIDEO = "video"

class XHSClient:
    def __init__(
            self,
            timeout=10,
            proxies=None,
            *,
            headers: Dict[str, str],
            playwright_page: Page,
            cookie_dict: Dict[str, str],
    ):
        self.proxies = proxies
        self.timeout = timeout
        self.headers = headers
        self._host = "https://edith.xiaohongshu.com"
        self.IP_ERROR_STR = "网络连接异常，请检查网络设置或重启试试"
        self.IP_ERROR_CODE = 300012
        self.NOTE_ABNORMAL_STR = "笔记状态异常，请稍后查看"
        self.NOTE_ABNORMAL_CODE = -510001
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict

    async def _pre_headers(self, url: str, data=None):
        encrypt_params = await self.playwright_page.evaluate("([url, data]) => window._webmsxyw(url,data)", [url, data])
        local_storage = await self.playwright_page.evaluate("() => window.localStorage")
        signs = sign(
            a1=self.cookie_dict.get("a1", ""),
            b1=local_storage.get("b1", ""),
            x_s=encrypt_params.get("X-s", ""),
            x_t=str(encrypt_params.get("X-t", ""))
        )

        headers = {
            "X-S": signs["x-s"],
            "X-T": signs["x-t"],
            "x-S-Common": signs["x-s-common"],
            "X-B3-Traceid": signs["x-b3-traceid"]
        }
        self.headers.update(headers)
        return self.headers

    async def request(self, method, url, **kwargs) -> Dict:
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request(
                method, url, timeout=self.timeout,
                **kwargs
            )
        try:
            data: Dict = response.json()
            if data["success"]:
                return data.get("data", data.get("success", {}))
            elif data["code"] == self.IP_ERROR_CODE:
                raise IPBlockError(self.IP_ERROR_STR)
            else:
                raise DataFetchError(data.get("msg", None))
        except Exception:
            # 可以在这里处理或记录错误, 例如：
            # logging.exception("Failed to decode JSON")
            # 或者返回一个空的字典或其他默认值
            return {}

    async def get(self, uri: str, params=None) -> Dict:
        final_uri = uri
        if isinstance(params, dict):
            final_uri = (f"{uri}?"
                         f"{'&'.join([f'{k}={v}' for k, v in params.items()])}")
        headers = await self._pre_headers(final_uri)
        return await self.request(method="GET", url=f"{self._host}{final_uri}", headers=headers)

    # async def post(self, uri: str, data: dict) -> Dict:
    #     headers = await self._pre_headers(uri, data)
    #     json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    #     return await self.request(method="POST", url=f"{self._host}{uri}",
    #                               data=json_str, headers=headers)

    async def post(self, uri: str, data: dict, **kwargs) -> Dict:
        headers = await self._pre_headers(uri, data)
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return await self.request(
            method="POST", url=f"{self._host}{uri}", data=json_str.encode("utf-8"), headers=headers,
            **{k: v for k, v in kwargs.items() if k != 'headers'}
        )

    async def ping(self) -> bool:
        """get a note to check if login state is ok"""
        utils.logger.info("Begin to ping xhs...")
        ping_flag = False
        try:
            note_card: Dict = await self.get_note_by_keyword(keyword="小红书")
            if note_card.get("items"):
                ping_flag = True
        except Exception as e:
            utils.logger.error(f"Ping xhs failed: {e}, and try to login again...")
            ping_flag = False
        return ping_flag

    async def update_cookies(self, browser_context: BrowserContext):
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def get_note_by_keyword(
            self, keyword: str,
            page: int = 1, page_size: int = 20,
            sort: SearchSortType = SearchSortType.GENERAL,
            note_type: SearchNoteType = SearchNoteType.ALL
    ) -> Dict:
        """search note by keyword

        :param keyword: what notes you want to search
        :param page: page number, defaults to 1
        :param page_size: page size, defaults to 20
        :param sort: sort ordering, defaults to SearchSortType.GENERAL
        :param note_type: note type, defaults to SearchNoteType.ALL
        :return: {has_more: true, items: []}
        """
        uri = "/api/sns/web/v1/search/notes"
        data = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": get_search_id(),
            "sort": sort.value,
            "note_type": note_type.value
        }
        return await self.post(uri, data)

    async def get_note_by_id(self, note_id: str) -> Dict:
        """
        :param note_id: note_id you want to fetch
        :return: {"time":1679019883000,"user":{"nickname":"nickname","avatar":"avatar","user_id":"user_id"},"image_list":[{"url":"https://sns-img-qc.xhscdn.com/c8e505ca-4e5f-44be-fe1c-ca0205a38bad","trace_id":"1000g00826s57r6cfu0005ossb1e9gk8c65d0c80","file_id":"c8e505ca-4e5f-44be-fe1c-ca0205a38bad","height":1920,"width":1440}],"tag_list":[{"id":"5be78cdfdb601f000100d0bc","name":"jk","type":"topic"}],"desc":"裙裙","interact_info":{"followed":false,"liked":false,"liked_count":"1732","collected":false,"collected_count":"453","comment_count":"30","share_count":"41"},"at_user_list":[],"last_update_time":1679019884000,"note_id":"6413cf6b00000000270115b5","type":"normal","title":"title"}
        """
        data = {"source_note_id": note_id}
        uri = "/api/sns/web/v1/feed"
        res = await self.post(uri, data)
        res_dict: Dict = res["items"][0]["note_card"]
        return res_dict

    async def get_note_comments(self, note_id: str, cursor: str = "") -> Dict:
        """get note comments
        :param note_id: note id you want to fetch
        :param cursor: last you get cursor, defaults to ""
        :return: {"has_more": true,"cursor": "6422442d000000000700dcdb",comments: [],"user_id": "63273a77000000002303cc9b","time": 1681566542930}
        """
        uri = "/api/sns/web/v2/comment/page"
        params = {
            "note_id": note_id,
            "cursor": cursor
        }
        return await self.get(uri, params)

    async def get_note_sub_comments(
            self, note_id: str,
            root_comment_id: str,
            num: int = 30, cursor: str = ""
    ):
        """
        get note sub comments
        :param note_id: note id you want to fetch
        :param root_comment_id: parent comment id
        :param num: recommend 30, if num greater 30, it only return 30 comments
        :param cursor: last you get cursor, defaults to ""
        :return: {"has_more": true,"cursor": "6422442d000000000700dcdb",comments: [],"user_id": "63273a77000000002303cc9b","time": 1681566542930}
        """
        uri = "/api/sns/web/v2/comment/sub/page"
        params = {
            "note_id": note_id,
            "root_comment_id": root_comment_id,
            "num": num,
            "cursor": cursor,
        }
        return await self.get(uri, params)

    async def get_note_all_comments(self, note_id: str, crawl_interval: float = 1.0, is_fetch_sub_comments=False):
        """
        get note all comments include sub comments
        :param note_id:
        :param crawl_interval:
        :param is_fetch_sub_comments:
        :return:
        """

        result = []
        comments_has_more = True
        comments_cursor = ""
        while comments_has_more:
            comments_res = await self.get_note_comments(note_id, comments_cursor)
            comments_has_more = comments_res.get("has_more", False)
            comments_cursor = comments_res.get("cursor", "")
            comments = comments_res["comments"]
            if not is_fetch_sub_comments:
                result.extend(comments)
                continue
            # handle get sub comments
            for comment in comments:
                result.append(comment)
                cur_sub_comment_count = int(comment["sub_comment_count"])
                cur_sub_comments = comment["sub_comments"]
                result.extend(cur_sub_comments)
                sub_comments_has_more = comment["sub_comment_has_more"] and len(
                    cur_sub_comments) < cur_sub_comment_count
                sub_comment_cursor = comment["sub_comment_cursor"]
                while sub_comments_has_more:
                    page_num = 30
                    sub_comments_res = await self.get_note_sub_comments(note_id, comment["id"], num=page_num,
                                                                        cursor=sub_comment_cursor)
                    sub_comments = sub_comments_res["comments"]
                    sub_comments_has_more = sub_comments_res["has_more"] and len(sub_comments) == page_num
                    sub_comment_cursor = sub_comments_res["cursor"]
                    result.extend(sub_comments)
                    await asyncio.sleep(crawl_interval)
            await asyncio.sleep(crawl_interval)
        return result

    async def comment_note(self, note_id: str, content: str):
        """comment a note

        :rtype: dict
        """
        uri = "/api/sns/web/v1/comment/post"
        data = {"note_id": note_id, "content": content, "at_users": []}
        return await self.post(uri, data)

    async def get_upload_files_permit(self, file_type: str, count: int = 1) -> tuple:
        """获取文件上传的 id

        :param file_type: 文件类型，["images", "video"]
        :param count: 文件数量
        :return:
        """
        uri = "/api/media/v1/upload/web/permit"
        params = {
            "biz_name": "spectrum",
            "scene": file_type,
            "file_count": count,
            "version": "1",
            "source": "web",
        }
        # temp_permit = await self.get(uri, params)["uploadTempPermits"][0]
        response = await self.get(uri, params)
        temp_permit = response["uploadTempPermits"][0]
        file_id = temp_permit["fileIds"][0]
        token = temp_permit["token"]
        return file_id, token

    async def upload_file(
            self,
            file_id: str,
            token: str,
            file_path: str,
            content_type: str = "image/jpeg",
    ):
        """ 将文件上传至指定文件 id 处

        :param file_id: 上传文件 id
        :param token: 上传授权验证 token
        :param file_path: 文件路径，暂只支持本地文件路径
        :param content_type:  【"video/mp4","image/jpeg","image/png"】
        :return:
        """
        url = "https://ros-upload.xiaohongshu.com/" + file_id
        headers = {"X-Cos-Security-Token": token, "Content-Type": content_type}
        async with aiofiles.open(file_path, "rb") as f:
            data = await f.read()
            return await self.request("PUT", url, data=data, headers=headers)
        # with open(file_path, "rb") as f:
        #     return await self.request("PUT", url, data=f, headers=headers)

    async def get_suggest_topic(self, keyword=""):
        """通过关键词获取话题信息，发布笔记用

        :param keyword: 话题关键词，如 Python
        :return:
        """
        uri = "/web_api/sns/v1/search/topic"
        data = {
            "keyword": keyword,
            "suggest_topic_request": {"title": "", "desc": ""},
            "page": {"page_size": 20, "page": 1},
        }
        response = await self.post(uri, data)
        return response["topic_info_dtos"]

    async def get_suggest_ats(self, keyword=""):
        """通过关键词获取用户信息，发布笔记用

        :param keyword: 用户名关键词，如 ReaJason
        :return:
        """
        uri = "/web_api/sns/v1/search/user_info"
        data = {
            "keyword": keyword,
            "search_id": str(time.time() * 1000),
            "page": {"page_size": 20, "page": 1},
        }
        response = await self.post(uri, data)
        return response["user_info_dtos"]

    async def create_note(self, title, desc, note_type, ats: list = None, topics: list = None,
                    image_info: dict = None,
                    video_info: dict = None,
                    post_time: str = None, is_private: bool = False):
        if post_time:
            post_date_time = datetime.strptime(post_time, "%Y-%m-%d %H:%M:%S")
            post_time = round(int(post_date_time.timestamp()) * 1000)
        uri = "/web_api/sns/v2/note"
        business_binds = {
            "version": 1,
            "noteId": 0,
            "noteOrderBind": {},
            "notePostTiming": {
                "postTime": post_time
            },
            "noteCollectionBind": {
                "id": ""
            }
        }

        data = {
            "common": {
                "type": note_type,
                "title": title,
                "note_id": "",
                "desc": desc,
                "source": '{"type":"web","ids":"","extraInfo":"{\\"subType\\":\\"official\\"}"}',
                "business_binds": json.dumps(business_binds, separators=(",", ":")),
                "ats": ats,
                "hash_tag": topics,
                "post_loc": {},
                "privacy_info": {"op_type": 1, "type": int(is_private)},
            },
            "image_info": image_info,
            "video_info": video_info,
        }
        headers = {
            "Referer": "https://creator.xiaohongshu.com/"
        }
        print(data)
        return await self.post(uri, data, headers=headers)

    async def create_image_note(
            self,
            title,
            desc,
            files: list,
            post_time: str = None,
            ats: list = None,
            topics: list = None,
            is_private: bool = False,
    ):
        """发布图文笔记

        :param title: 笔记标题
        :param desc: 笔记详情
        :param files: 文件路径列表，目前只支持本地路径
        :param post_time: 可选，发布时间，例如 "2023-10-11 12:11:11"
        :param ats: 可选，@用户信息
        :param topics: 可选，话题信息
        :param is_private: 可选，是否私密发布
        :return:
        """
        if ats is None:
            ats = []
        if topics is None:
            topics = []

        images = []
        for file in files:
            image_id, token = await self.get_upload_files_permit("image")
            await self.upload_file(image_id, token, file)
            images.append(
                {
                    "file_id": image_id,
                    "metadata": {"source": -1},
                    "stickers": {"version": 2, "floating": []},
                    "extra_info_json": '{"mimeType":"image/jpeg"}',
                }
            )
        return await self.create_note(title, desc, NoteType.NORMAL.value, ats=ats, topics=topics,
                                image_info={"images": images}, is_private=is_private,
                                post_time=post_time)
