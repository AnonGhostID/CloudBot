#!/usr/bin/env python3
from asyncio import CancelledError
from os import path as ospath
from os import walk
from re import fullmatch

from aiofiles.os import path as aiopath
from aiohttp import ClientError, ClientSession, ClientTimeout

from bot.helper.ext_utils.bot_utils import sync_to_async


class Gofile:
    def __init__(self, uploader=None, token=None):
        self.api_url = "https://api.gofile.io/"
        self.uploader = uploader
        self.token = token

    @staticmethod
    def _response_data(response):
        if not isinstance(response, dict):
            raise RuntimeError("GoFile returned an invalid response.")
        status = response.get("status")
        if status != "ok":
            if isinstance(status, str) and fullmatch(r"error-[A-Za-z0-9_-]+", status):
                raise RuntimeError(f"GoFile: {status}")
            raise RuntimeError("GoFile returned an invalid response.")
        data = response.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("GoFile returned an invalid response.")
        return data

    @staticmethod
    async def is_goapi(token):
        if not token:
            return False
        timeout = ClientTimeout(total=60, connect=15, sock_read=30)
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with ClientSession(timeout=timeout, headers=headers) as session:
                async def get_data(url):
                    async with session.get(url) as response:
                        if response.status in (401, 403):
                            return None
                        if response.status != 200:
                            raise RuntimeError("GoFile validation failed: HTTP error.")
                        payload = await response.json(content_type=None)
                        if not isinstance(payload, dict):
                            raise RuntimeError("GoFile validation failed: invalid response.")
                        status = payload.get("status")
                        if isinstance(status, str) and status.startswith("error-"):
                            return None
                        return Gofile._response_data(payload)

                account = await get_data("https://api.gofile.io/accounts/getid")
                if account is None:
                    return False
                account_id = account.get("id")
                if not isinstance(account_id, str) or not account_id:
                    raise RuntimeError("GoFile validation failed: invalid response.")
                return await get_data(f"https://api.gofile.io/accounts/{account_id}") is not None
        except (ClientError, TimeoutError, ValueError):
            raise RuntimeError("GoFile validation failed: transport or response error.") from None

    def _check_cancelled(self):
        if self.uploader.is_cancelled:
            raise CancelledError

    @property
    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    async def __getAccount(self):
        self._check_cancelled()
        account = self._response_data(await self.uploader.request_json(
            "GET", f"{self.api_url}accounts/getid", headers=self._headers
        ))
        account_id = account.get("id")
        if not isinstance(account_id, str) or not account_id:
            raise RuntimeError("GoFile returned an invalid account response.")
        self._check_cancelled()
        return self._response_data(await self.uploader.request_json(
            "GET", f"{self.api_url}accounts/{account_id}", headers=self._headers
        ))

    async def upload_folder(self, path):
        if not await aiopath.isdir(path):
            raise RuntimeError("GoFile source is not a directory.")
        account = await self.__getAccount()
        root_id = account.get("rootFolder")
        if not isinstance(root_id, str) or not root_id:
            raise RuntimeError("GoFile returned an invalid root folder.")
        folder = await self.create_folder(root_id, ospath.basename(ospath.normpath(path)))
        folder_id, code = folder.get("id"), folder.get("code")
        if not isinstance(folder_id, str) or not folder_id or not isinstance(code, str) or not code:
            raise RuntimeError("GoFile returned an invalid folder response.")

        def collect_tree():
            def fail(error):
                raise error
            entries = []
            for root, dirs, files in walk(path, onerror=fail):
                dirs.sort()
                entries.append((root, sorted(files)))
            return entries

        try:
            entries = await sync_to_async(collect_tree)
        except OSError:
            raise RuntimeError("GoFile could not read the source directory.") from None
        folder_ids = {".": folder_id}
        for root, files in entries:
            self._check_cancelled()
            rel_path = ospath.relpath(root, path)
            if rel_path != ".":
                parent_id = folder_ids[ospath.dirname(rel_path) or "."]
                child = await self.create_folder(parent_id, ospath.basename(rel_path))
                child_id = child.get("id")
                if not isinstance(child_id, str) or not child_id:
                    raise RuntimeError("GoFile returned an invalid folder response.")
                folder_ids[rel_path] = child_id
                self.uploader.total_folders += 1
            for name in files:
                self._check_cancelled()
                await self.upload_file(ospath.join(root, name), folder_ids[rel_path])
        self._check_cancelled()
        return code

    async def upload_file(self, path, folderId=""):
        self._check_cancelled()
        fields = {"folderId": folderId} if folderId else {}
        response = await self.uploader.upload_aiohttp(
            "https://upload.gofile.io/uploadfile", path, "file", fields,
            headers=self._headers,
        )
        data = self._response_data(response)
        self._check_cancelled()
        self.uploader.total_files += 1
        return data

    async def upload(self, file_path):
        if not self.token:
            raise RuntimeError("GoFile requires a saved API key.")
        self._check_cancelled()
        if await aiopath.isfile(file_path):
            data = await self.upload_file(file_path)
            link = data.get("downloadPage")
            if isinstance(link, str) and link:
                return link
            raise RuntimeError("GoFile returned an invalid upload response.")
        if await aiopath.isdir(file_path):
            code = await self.upload_folder(file_path)
            self._check_cancelled()
            return f"https://gofile.io/d/{code}"
        raise RuntimeError("GoFile source path does not exist or is not a regular file.")

    async def create_folder(self, parentFolderId, folderName):
        self._check_cancelled()
        return self._response_data(await self.uploader.request_json(
            "POST", f"{self.api_url}contents/createFolder", headers=self._headers,
            json={"parentFolderId": parentFolderId, "folderName": folderName, "public": True},
        ))
