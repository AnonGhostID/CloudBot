import asyncio
import re
from mimetypes import guess_type
from pathlib import Path
from secrets import token_hex
from urllib.parse import urlsplit

import aiofiles
from aiofiles.os import path as aiopath
from aiohttp import ClientError, ClientSession, ClientTimeout, payload
from yarl import URL


class _FilePayload(payload.Payload):
    def __init__(self, path, offset, length, uploader, content_type):
        super().__init__(None, content_type=content_type)
        self._size = length
        self.path = path
        self.offset = offset
        self.uploader = uploader

    def decode(self, encoding='utf-8', errors='strict'):
        with open(self.path, 'rb') as file:
            file.seek(self.offset)
            return file.read(self._size).decode(encoding, errors)

    async def write(self, writer):
        remaining = self._size
        async with aiofiles.open(self.path, 'rb') as file:
            await file.seek(self.offset)
            while remaining:
                if self.uploader.is_cancelled:
                    raise asyncio.CancelledError
                chunk = await file.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise RuntimeError('storage.to: file changed during upload.')
                await writer.write(chunk)
                remaining -= len(chunk)
                self.uploader.report_progress(self.offset + self._size - remaining)


class StorageTo:
    API_URL = 'https://storage.to/api'

    def __init__(self, uploader, token=None):
        self.uploader = uploader
        self.token = token or ''
        self.visitor_token = token_hex(32)

    def _check_cancelled(self):
        if self.uploader.is_cancelled:
            raise asyncio.CancelledError

    def _headers(self, owner_token=None):
        headers = {'X-Visitor-Token': self.visitor_token}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        if owner_token:
            headers['X-Owner-Token'] = owner_token
        return headers

    async def _api(self, session, endpoint, data, owner_token=None):
        async with session.post(
            f'{self.API_URL}/{endpoint}', json=data,
            headers=self._headers(owner_token), allow_redirects=False,
            timeout=ClientTimeout(total=60, connect=15, sock_read=30),
        ) as response:
            if response.status not in (200, 201):
                raise RuntimeError(f'storage.to API request failed with HTTP {response.status}.')
            try:
                result = await response.json(content_type=None)
            except (ValueError, UnicodeDecodeError):
                raise RuntimeError('storage.to returned invalid JSON.') from None
            if not isinstance(result, dict) or result.get('success') is not True:
                raise RuntimeError('storage.to API request failed.')
            return result

    @staticmethod
    def _storage_url(url):
        try:
            parsed = urlsplit(url) if isinstance(url, str) else None
            host = parsed.hostname if parsed else None
            valid = (parsed and parsed.scheme == 'https' and host
                     and re.fullmatch(r'(?:[a-z0-9-]+\.)*r2\.cloudflarestorage\.com', host)
                     and '@' not in parsed.netloc
                     and parsed.port in (None, 443) and not parsed.fragment
                     and not any(ord(c) < 33 or ord(c) == 127 for c in url))
        except ValueError:
            valid = False
        if not valid:
            raise RuntimeError('storage.to returned an invalid storage URL.')
        return URL(url, encoded=True)

    async def _put(self, session, url, path, offset, length, content_type, require_etag):
        self._check_cancelled()
        body = _FilePayload(path, offset, length, self.uploader, content_type)
        async with session.put(
            self._storage_url(url), data=body, allow_redirects=False,
            timeout=ClientTimeout(total=7200, connect=60, sock_read=300),
        ) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f'storage.to storage upload failed with HTTP {response.status}.')
            etag = response.headers.get('ETag')
            if require_etag and not etag:
                raise RuntimeError('storage.to storage upload returned no ETag.')
            return etag

    async def _multipart(self, session, init, path, size):
        upload_id = init.get('upload_id')
        owner = init.get('owner_token')
        if not isinstance(upload_id, str) or not upload_id:
            raise RuntimeError('storage.to returned an invalid multipart session.')
        if owner is not None and (not isinstance(owner, str) or not owner):
            raise RuntimeError('storage.to returned an invalid owner token.')
        completed = False
        try:
            part_size = init.get('part_size')
            total = init.get('total_parts')
            urls = init.get('initial_urls', {})
            if (type(part_size) is not int or part_size < 1
                    or type(total) is not int or total < 1 or total > 10000
                    or total != (size + part_size - 1) // part_size
                    or not isinstance(urls, dict)):
                raise RuntimeError('storage.to returned invalid multipart metadata.')
            urls = dict(urls)
            parts = []
            for number in range(1, total + 1):
                self._check_cancelled()
                if str(number) not in urls:
                    numbers = list(range(number, min(total + 1, number + 50)))
                    result = await self._api(session, 'upload/parts', {
                        'upload_id': upload_id, 'part_numbers': numbers,
                    }, owner)
                    entries = result.get('part_urls')
                    if not isinstance(entries, list):
                        raise RuntimeError('storage.to returned invalid part URLs.')
                    for entry in entries:
                        if (not isinstance(entry, dict) or type(entry.get('partNumber')) is not int
                                or entry['partNumber'] not in numbers or not isinstance(entry.get('url'), str)):
                            raise RuntimeError('storage.to returned invalid part URLs.')
                        urls[str(entry['partNumber'])] = entry['url']
                offset = (number - 1) * part_size
                etag = await self._put(session, urls.get(str(number)), path, offset,
                                       min(part_size, size - offset), 'application/octet-stream', True)
                parts.append({'partNumber': number, 'etag': etag})
            self._check_cancelled()
            await self._api(session, 'upload/complete-multipart', {
                'upload_id': upload_id, 'parts': parts,
            }, owner)
            completed = True
        finally:
            if not completed:
                try:
                    await self._api(session, 'upload/abort', {'upload_id': upload_id}, owner)
                except (Exception, asyncio.CancelledError):
                    pass

    async def upload(self, file_path):
        self._check_cancelled()
        if not await aiopath.isfile(file_path):
            raise RuntimeError('storage.to accepts a single regular file, not a folder.')
        size = await aiopath.getsize(file_path)
        if not size:
            raise RuntimeError('storage.to does not accept empty files.')
        filename = Path(file_path).name
        content_type = guess_type(filename)[0] or 'application/octet-stream'
        metadata = {'filename': filename, 'content_type': content_type, 'size': size}
        try:
            async with ClientSession() as session:
                self._check_cancelled()
                init = await self._api(session, 'upload/init', metadata)
                r2_key = init.get('r2_key')
                if not isinstance(r2_key, str) or not r2_key:
                    raise RuntimeError('storage.to returned an invalid upload session.')
                if init.get('type') == 'single':
                    await self._put(session, init.get('upload_url'), file_path, 0, size,
                                    content_type, False)
                elif init.get('type') == 'multipart':
                    await self._multipart(session, init, file_path, size)
                else:
                    raise RuntimeError('storage.to returned an invalid upload type.')
                self._check_cancelled()
                result = await self._api(session, 'upload/confirm', dict(metadata, r2_key=r2_key))
                file = result.get('file')
                file_id = file.get('id') if isinstance(file, dict) else None
                owner_token = result.get('owner_token')
                if isinstance(file_id, str) and file_id and isinstance(owner_token, str) and owner_token:
                    await self._api(session, f'file/{file_id}/expiry', {'days': 7}, owner_token)
        except (ClientError, OSError, asyncio.TimeoutError):
            raise RuntimeError('storage.to upload failed.') from None
        file = result.get('file')
        link = file.get('url') if isinstance(file, dict) else None
        try:
            parsed = urlsplit(link) if isinstance(link, str) else None
            valid = (parsed and parsed.scheme == 'https' and parsed.hostname == 'storage.to'
                     and '@' not in parsed.netloc and parsed.port in (None, 443)
                     and parsed.path not in ('', '/') and not parsed.query and not parsed.fragment)
        except ValueError:
            valid = False
        if not valid:
            raise RuntimeError('storage.to returned an invalid share URL.')
        self.uploader.total_files += 1
        return link
