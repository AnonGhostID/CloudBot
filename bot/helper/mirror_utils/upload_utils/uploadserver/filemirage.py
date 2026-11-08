import asyncio
import time
from pathlib import Path
from secrets import token_hex
from urllib.parse import urlsplit

import aiofiles
from aiofiles.os import path as aiopath
from aiohttp import ClientError, ClientSession, ClientTimeout, FormData, payload


class _ChunkPayload(payload.Payload):
    def __init__(self, file_path, offset, length, uploader):
        super().__init__(None, content_type='application/octet-stream')
        self._size = length
        self.file_path = file_path
        self.offset = offset
        self.uploader = uploader

    def decode(self, encoding='utf-8', errors='strict'):
        with open(self.file_path, 'rb') as file:
            file.seek(self.offset)
            return file.read(self._size).decode(encoding, errors)

    async def write(self, writer):
        remaining = self._size
        async with aiofiles.open(self.file_path, 'rb') as file:
            await file.seek(self.offset)
            while remaining:
                if self.uploader.is_cancelled:
                    raise asyncio.CancelledError
                chunk = await file.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise RuntimeError('FileMirage: file changed during upload.')
                await writer.write(chunk)
                remaining -= len(chunk)
                self.uploader.report_progress(self.offset + self._size - remaining)


class FileMirage:
    CHUNK_SIZE = 99 * 1024 * 1024
    MAX_SIZE = 50 * 1024 ** 3

    def __init__(self, uploader, token=None):
        self.uploader = uploader
        self.token = token or ''

    async def upload(self, file_path):
        if not await aiopath.isfile(file_path):
            raise RuntimeError('FileMirage accepts a single regular file, not a folder.')
        size = await aiopath.getsize(file_path)
        if not size:
            raise RuntimeError('FileMirage does not upload empty files.')
        if size > self.MAX_SIZE:
            raise RuntimeError('FileMirage uploads are limited to 50 GB per file.')
        if self.uploader.is_cancelled:
            raise asyncio.CancelledError

        headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
        discovery = await self.uploader.request_json(
            'GET', 'https://filemirage.com/api/servers', headers=headers,
        )
        data = discovery.get('data')
        server = data.get('server') if isinstance(data, dict) else None
        try:
            parsed = urlsplit(server) if isinstance(server, str) else None
            valid = (parsed and parsed.scheme == 'https' and parsed.hostname
                     and parsed.hostname.endswith('.filemirage.com')
                     and not parsed.username and not parsed.password
                     and parsed.port in (None, 443) and not parsed.query and not parsed.fragment)
        except ValueError:
            valid = False
        if not valid:
            raise RuntimeError('FileMirage returned an invalid upload server.')

        upload_id = f'{int(time.time() * 1000):x}{token_hex(8)}'
        total_chunks = (size + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE
        filename = Path(file_path).name
        timeout = ClientTimeout(total=7200, connect=60, sock_read=300)
        result = None
        try:
            async with ClientSession(timeout=timeout) as session:
                for index in range(total_chunks):
                    if self.uploader.is_cancelled:
                        raise asyncio.CancelledError
                    offset = index * self.CHUNK_SIZE
                    length = min(self.CHUNK_SIZE, size - offset)
                    form = FormData()
                    form.add_field('file', _ChunkPayload(file_path, offset, length, self.uploader),
                                   filename='blob', content_type='application/octet-stream')
                    form.add_field('filename', filename)
                    form.add_field('upload_id', upload_id)
                    form.add_field('chunk_number', str(index))
                    form.add_field('total_chunks', str(total_chunks))
                    async with session.post(f'{server.rstrip("/")}/upload.php', data=form,
                                            headers=headers, allow_redirects=False) as response:
                        if not 200 <= response.status < 300:
                            raise RuntimeError(f'FileMirage upload failed with HTTP {response.status}.')
                        if index == total_chunks - 1:
                            try:
                                result = await response.json(content_type=None)
                            except (ValueError, UnicodeDecodeError):
                                raise RuntimeError('FileMirage returned invalid JSON.') from None
                        else:
                            await response.read()
        except (ClientError, OSError, asyncio.TimeoutError):
            raise RuntimeError('FileMirage upload failed.') from None

        data = result.get('data') if isinstance(result, dict) else None
        link = data.get('url') if isinstance(data, dict) else None
        try:
            parsed = urlsplit(link) if isinstance(link, str) else None
            valid = parsed and parsed.scheme == 'https' and parsed.hostname
        except ValueError:
            valid = False
        if not valid:
            raise RuntimeError('FileMirage returned an invalid upload link.')
        self.uploader.total_files += 1
        return link
