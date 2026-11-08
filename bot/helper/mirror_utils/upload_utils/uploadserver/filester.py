#!/usr/bin/env python3
from urllib.parse import urlsplit

from aiofiles.os import path as aiopath


class Filester:
    def __init__(self, uploader=None, api_key=None):
        self.uploader = uploader
        self.api_key = api_key if isinstance(api_key, str) else ''

    async def upload(self, file_path):
        if not await aiopath.exists(file_path):
            raise RuntimeError('Filester: file not found.')
        if await aiopath.isdir(file_path):
            raise RuntimeError('Filester does not support folder uploads.')
        if not await aiopath.isfile(file_path):
            raise RuntimeError('Filester: path is not a regular file.')
        if self.uploader.is_cancelled:
            return None

        headers = {'Authorization': f'Bearer {self.api_key}'} if self.api_key else None
        result = await self.uploader.upload_aiohttp(
            'https://u1.filester.me/api/v1/upload',
            file_path,
            req_file='file',
            headers=headers,
            expected_statuses=(200,),
            response_mode='json',
        )
        if self.uploader.is_cancelled:
            return None
        if result.get('success') is not True:
            message = result.get('message')
            if isinstance(message, str) and message.strip():
                raise RuntimeError(f'Filester upload failed: {message.strip()}')
            raise RuntimeError('Filester upload failed.')

        link = result.get('url')
        try:
            parsed = urlsplit(link) if isinstance(link, str) else None
            valid_link = (parsed and parsed.scheme == 'https' and parsed.hostname
                          and not parsed.username and not parsed.password
                          and not any(char.isspace() for char in link))
        except ValueError:
            valid_link = False
        if not valid_link:
            raise RuntimeError('Filester returned an invalid upload URL.')
        self.uploader.total_files += 1
        return link
