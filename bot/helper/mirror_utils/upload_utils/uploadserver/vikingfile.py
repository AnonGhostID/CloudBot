#!/usr/bin/env python3
from aiofiles.os import path as aiopath


class VikingFile:
    def __init__(self, uploader=None, user_hash=None):
        self.api_url = 'https://vikingfile.com/api'
        self.uploader = uploader
        self.user_hash = user_hash if isinstance(user_hash, str) else ''

    async def upload(self, file_path):
        if not await aiopath.exists(file_path):
            raise RuntimeError('VikingFile: file not found.')
        if await aiopath.isdir(file_path):
            raise RuntimeError('VikingFile does not support folder uploads.')
        if not await aiopath.isfile(file_path):
            raise RuntimeError('VikingFile: path is not a regular file.')
        if self.uploader.is_cancelled:
            return None
        server = await self.uploader.request_json('GET', f'{self.api_url}/get-server')
        upload_url = server.get('server')
        if not isinstance(upload_url, str) or not upload_url.startswith('https://'):
            raise RuntimeError('VikingFile returned an invalid upload server.')
        result = await self.uploader.upload_aiohttp(
            upload_url,
            file_path,
            req_file='file',
            data={'user': self.user_hash},
            expected_statuses=(200,),
            response_mode='json',
        )
        link = result.get('url')
        if not isinstance(link, str) or not link.startswith('https://'):
            if self.uploader.is_cancelled:
                return None
            raise RuntimeError('VikingFile returned an invalid upload response.')
        if self.uploader.is_cancelled:
            return None
        self.uploader.total_files += 1
        return link
