#!/usr/bin/env python3
from asyncio import CancelledError
from html import escape
from pathlib import Path
from urllib.parse import quote

from aiofiles.os import scandir, path as aiopath

from bot import config_dict
from bot.helper.ext_utils.telegraph_helper import telegraph

ALLOWED_EXTS = [
    '.avi', '.mkv', '.mpg', '.mpeg', '.vob', '.wmv', '.flv', '.mp4', '.mov', '.m4v',
    '.m2v', '.divx', '.3gp', '.webm', '.ogv', '.ogg', '.ts', '.ogm'
]


class Streamtape:
    def __init__(self, uploader, login, key):
        self.__userLogin = login
        self.__passKey = key
        self.uploader = uploader
        self.base_url = 'https://api.streamtape.com'

    def _check_cancelled(self):
        if self.uploader.is_cancelled:
            raise CancelledError

    async def _request(self, endpoint, **params):
        self._check_cancelled()
        params.update(login=self.__userLogin, key=self.__passKey)
        response = await self.uploader.request_json(
            'GET', f'{self.base_url}{endpoint}', params=params
        )
        result = response.get('result')
        if type(response.get('status')) not in (int, float) or response['status'] != 200 or not isinstance(result, dict):
            raise RuntimeError('Invalid StreamTape response.')
        return result

    async def list_folder(self, folder=None):
        params = {} if folder is None else {'folder': folder}
        result = await self._request('/file/listfolder', **params)
        if not isinstance(result.get('files'), list) or not isinstance(result.get('folders'), list):
            raise RuntimeError('Invalid StreamTape folder listing.')
        if any(not isinstance(item, dict) for item in result['files'] + result['folders']):
            raise RuntimeError('Invalid StreamTape folder listing.')
        if any(not isinstance(item.get('linkid'), str) or not item['linkid'] for item in result['files']):
            raise RuntimeError('Invalid StreamTape folder listing.')
        return result

    async def create_folder(self, name, parent=None):
        contents = await self.list_folder(parent)
        names = {folder.get('name') for folder in contents['folders'] if isinstance(folder.get('name'), str)}
        original = name
        index = 1
        while name in names:
            name = f'{index} {original}'
            index += 1
        params = {'name': name}
        if parent is not None:
            params['pid'] = parent
        result = await self._request('/file/createfolder', **params)
        if not isinstance(result.get('folderid'), str) or not result['folderid']:
            raise RuntimeError('Invalid StreamTape folder response.')
        return result

    async def upload_file(self, file_path, folder_id=None):
        path = Path(file_path)
        if path.suffix.lower() not in ALLOWED_EXTS:
            raise RuntimeError('StreamTape does not support this file extension.')
        self._check_cancelled()
        if folder_id is None:
            folder = await self.create_folder(path.stem)
            folder_id = folder['folderid']
        before = await self.list_folder(folder_id)
        old_ids = {item.get('linkid') for item in before['files'] if isinstance(item.get('linkid'), str)}
        size = await aiopath.getsize(file_path)
        upload_info = await self._request('/file/ul', folder=folder_id)
        upload_url = upload_info.get('url')
        if not isinstance(upload_url, str) or not upload_url:
            raise RuntimeError('Invalid StreamTape upload response.')
        self._check_cancelled()
        await self.uploader.upload_aiohttp(
            upload_url, file_path, req_file='file1',
            expected_statuses=(200, 201), response_mode='none'
        )
        self._check_cancelled()
        after = await self.list_folder(folder_id)
        matches = [item['linkid'] for item in after['files']
                   if isinstance(item.get('linkid'), str) and item['linkid']
                   and item['linkid'] not in old_ids
                   and item.get('name') == path.name and item.get('size') == size]
        if len(matches) != 1:
            raise RuntimeError('Unable to identify the uploaded StreamTape file.')
        self._check_cancelled()
        self.uploader.total_files += 1
        return f'https://streamtape.to/v/{quote(matches[0], safe="")}'

    async def _upload_tree(self, folder_path, folder_id, fragments):
        for entry in sorted(await scandir(folder_path), key=lambda item: item.name):
            self._check_cancelled()
            if entry.is_dir():
                folder = await self.create_folder(entry.name, folder_id)
                self.uploader.total_folders += 1
                fragments.append(f'<aside><b>🗂 {escape(entry.name)}</b></aside>')
                await self._upload_tree(entry.path, folder['folderid'], fragments)
            elif entry.is_file() and Path(entry.name).suffix.lower() in ALLOWED_EXTS:
                link = await self.upload_file(entry.path, folder_id)
                fragments.append(
                    f'<ol><li><code>{escape(entry.name)}</code><br>🔗 '
                    f'<a href="{escape(link, quote=True)}">StreamTape URL</a></li></ol>'
                )

    async def upload_folder(self, folder_path):
        self._check_cancelled()
        folder = await self.create_folder(Path(folder_path).name)
        fragments = []
        initial_files = self.uploader.total_files
        await self._upload_tree(folder_path, folder['folderid'], fragments)
        if self.uploader.total_files == initial_files:
            raise RuntimeError('No supported video files were uploaded to StreamTape.')
        self._check_cancelled()
        cover = escape(config_dict['COVER_IMAGE'], quote=True)
        content = f'<figure><img src="{cover}"></figure>' + ''.join(fragments)
        page = await telegraph.create_page(title='StreamTape X', content=content)
        self._check_cancelled()
        if not isinstance(page, dict) or not isinstance(page.get('path'), str) or not page['path']:
            raise RuntimeError('Unable to create StreamTape Telegraph page.')
        return f"https://te.legra.ph/{page['path']}"

    async def upload(self, file_path):
        self._check_cancelled()
        if await aiopath.isfile(file_path):
            return await self.upload_file(file_path)
        if await aiopath.isdir(file_path):
            return await self.upload_folder(file_path)
        raise RuntimeError('StreamTape upload path does not exist or is not a regular file or directory.')
