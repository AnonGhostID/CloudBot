#!/usr/bin/env python3
from os.path import basename
from urllib.parse import quote

from aiofiles.os import path as aiopath


class BuzzHeavier:
    def __init__(self, uploader=None, api_key=None):
        self.api_url = 'https://w.buzzheavier.com'
        self.uploader = uploader
        self.api_key = api_key

    async def upload(self, file_path):
        if not await aiopath.exists(file_path):
            raise RuntimeError('BuzzHeavier: file not found.')
        if await aiopath.isdir(file_path):
            raise RuntimeError('BuzzHeavier does not support folder uploads.')
        if not await aiopath.isfile(file_path):
            raise RuntimeError('BuzzHeavier: path is not a regular file.')
        if self.uploader.is_cancelled:
            return None

        headers = {'Authorization': f'Bearer {self.api_key}'} if self.api_key else None
        result = await self.uploader.upload_aiohttp(
            f'{self.api_url}/{quote(basename(file_path), safe="")}',
            file_path,
            headers=headers,
            method='PUT',
            params={'locationId': '12brteedoy0f'},
            expected_statuses=(200, 201),
            response_mode='json',
        )
        code = result.get('code')
        if type(code) not in (int, float) or code not in (200, 201):
            if type(code) is int:
                raise RuntimeError(f'BuzzHeavier upload failed with code {code}.')
            raise RuntimeError('BuzzHeavier returned an invalid upload response.')
        data = result.get('data')
        file_id = data.get('id') if isinstance(data, dict) else None
        if not isinstance(file_id, str) or not file_id:
            raise RuntimeError('BuzzHeavier returned an invalid upload response.')
        if self.uploader.is_cancelled:
            return None
        self.uploader.total_files += 1
        return f'https://buzzheavier.com/{quote(file_id, safe="")}'
