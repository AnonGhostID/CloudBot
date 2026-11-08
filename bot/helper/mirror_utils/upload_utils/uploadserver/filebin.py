import asyncio
from pathlib import Path
from secrets import token_hex
from urllib.parse import quote

import aiofiles
from aiofiles.os import path as aiopath
from aiohttp import ClientError, ClientSession, ClientTimeout, payload


class _FilePayload(payload.Payload):
    def __init__(self, file_path, size, uploader):
        super().__init__(None, content_type='application/octet-stream')
        self._size = size
        self.file_path = file_path
        self.uploader = uploader

    def decode(self, encoding='utf-8', errors='strict'):
        with open(self.file_path, 'rb') as file:
            return file.read().decode(encoding, errors)

    async def write(self, writer):
        sent = 0
        async with aiofiles.open(self.file_path, 'rb') as file:
            while sent < self._size:
                if self.uploader.is_cancelled:
                    raise asyncio.CancelledError
                chunk = await file.read(min(1024 * 1024, self._size - sent))
                if not chunk:
                    raise RuntimeError('Filebin: file changed during upload.')
                await writer.write(chunk)
                sent += len(chunk)
                self.uploader.report_progress(sent)


class Filebin:
    def __init__(self, uploader, credential=None):
        self.uploader = uploader

    async def upload(self, file_path):
        if not await aiopath.isfile(file_path):
            raise RuntimeError('Filebin accepts a single regular file, not a folder.')
        if self.uploader.is_cancelled:
            raise asyncio.CancelledError

        filename = Path(file_path).name
        size = await aiopath.getsize(file_path)
        bin_id = token_hex(16)
        url = f'https://filebin.net/{bin_id}/{quote(filename, safe="")}'
        timeout = ClientTimeout(total=7200, connect=60, sock_read=300)
        try:
            async with ClientSession(timeout=timeout) as session:
                async with session.post(
                    url, data=_FilePayload(file_path, size, self.uploader),
                    allow_redirects=False,
                ) as response:
                    if response.status != 201:
                        raise RuntimeError(f'Filebin upload failed with HTTP {response.status}.')
                    try:
                        result = await response.json(content_type=None)
                    except (ValueError, UnicodeDecodeError):
                        raise RuntimeError('Filebin returned invalid JSON.') from None
        except (ClientError, OSError, asyncio.TimeoutError):
            raise RuntimeError('Filebin upload failed.') from None

        bin_data = result.get('bin') if isinstance(result, dict) else None
        file_data = result.get('file') if isinstance(result, dict) else None
        if (not isinstance(bin_data, dict) or bin_data.get('id') != bin_id
                or not isinstance(file_data, dict) or file_data.get('filename') != filename
                or file_data.get('bytes') != size):
            raise RuntimeError('Filebin returned an invalid upload response.')
        if self.uploader.is_cancelled:
            raise asyncio.CancelledError
        self.uploader.total_files += 1
        return f'https://filebin.net/{bin_id}'
