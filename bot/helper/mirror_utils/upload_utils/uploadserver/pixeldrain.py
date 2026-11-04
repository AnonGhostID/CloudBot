#!/usr/bin/env python3
from base64 import b64encode
from os.path import basename
from urllib.parse import quote

from aiofiles.os import path as aiopath


class PixelDrain:
    def __init__(self, uploader=None, api_key=None):
        self.api_url = 'https://pixeldrain.com/api'
        self.uploader = uploader
        if not api_key:
            raise RuntimeError('PixelDrain requires a saved API key.')
        self.auth_header = f"Basic {b64encode(f':{api_key}'.encode()).decode()}"

    async def upload(self, file_path):
        if not await aiopath.exists(file_path):
            raise RuntimeError('PixelDrain: file not found.')
        if await aiopath.isdir(file_path):
            raise RuntimeError('PixelDrain does not support folder uploads.')
        if not await aiopath.isfile(file_path):
            raise RuntimeError('PixelDrain: path is not a regular file.')
        if self.uploader.is_cancelled:
            return None

        result = await self.uploader.upload_aiohttp(
            f'{self.api_url}/file/{quote(basename(file_path), safe="")}',
            file_path,
            headers={
                'Authorization': self.auth_header,
                'Content-Type': 'application/octet-stream',
            },
            method='PUT',
            expected_statuses=(201,),
            response_mode='json',
        )
        file_id = result.get('id')
        if ('success' in result and result['success'] is not True) or not isinstance(file_id, str) or not file_id:
            raise RuntimeError('PixelDrain returned an invalid upload response.')
        if self.uploader.is_cancelled:
            return None
        self.uploader.total_files += 1
        return f'https://pixeldrain.com/u/{quote(file_id, safe="")}'
