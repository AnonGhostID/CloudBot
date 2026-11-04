#!/usr/bin/env python3
from os.path import basename
from urllib.parse import quote, urlsplit

from aiofiles.os import path as aiopath, stat as aiostat


class Ranoz:
    def __init__(self, uploader=None):
        self.api_url = 'https://ranoz.gg/api/v1'
        self.uploader = uploader

    async def upload(self, file_path):
        if not await aiopath.exists(file_path):
            raise RuntimeError('Ranoz: file not found.')
        if await aiopath.isdir(file_path):
            raise RuntimeError('Ranoz does not support folder uploads.')
        if not await aiopath.isfile(file_path):
            raise RuntimeError('Ranoz: path is not a regular file.')
        if self.uploader.is_cancelled:
            return None

        metadata = await self.uploader.request_json(
            'POST',
            f'{self.api_url}/files/upload_url',
            json={'filename': basename(file_path), 'size': (await aiostat(file_path)).st_size},
            expected_statuses=(200,),
        )
        data = metadata.get('data')
        if not isinstance(data, dict):
            raise RuntimeError('Ranoz returned invalid upload metadata.')
        upload_url = data.get('upload_url')
        file_url = data.get('url')
        file_id = data.get('id')
        if not self._is_https_url(upload_url):
            raise RuntimeError('Ranoz returned invalid upload metadata.')
        if self._is_https_url(file_url):
            download_url = file_url
        elif isinstance(file_id, str) and file_id:
            download_url = f'https://ranoz.gg/file/{quote(file_id, safe="")}'
        else:
            raise RuntimeError('Ranoz returned invalid upload metadata.')
        if self.uploader.is_cancelled:
            return None

        await self.uploader.upload_aiohttp(
            upload_url,
            file_path,
            method='PUT',
            expected_statuses=(200, 201, 204),
            response_mode='none',
        )
        if self.uploader.is_cancelled:
            return None
        self.uploader.total_files += 1
        return download_url

    @staticmethod
    def _is_https_url(value):
        if not isinstance(value, str):
            return False
        try:
            parsed = urlsplit(value)
            return parsed.scheme == 'https' and bool(parsed.hostname)
        except ValueError:
            return False
