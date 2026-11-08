#!/usr/bin/env python3
import asyncio
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

import aiofiles
from aiofiles.os import path as aiopath
from aiohttp import ClientError, ClientSession, ClientTimeout, FormData

from bot import LOGGER, user_data
from bot.helper.ext_utils.fs_utils import get_mime_type
from bot.helper.ext_utils.upload_hosts import HOST_CREDENTIAL_VARS, upload_host_credential
from bot.helper.mirror_utils.upload_utils.progress_file_reader import ProgressFileReader
from bot.helper.mirror_utils.upload_utils.uploadserver.akirabox import AkiraBox
from bot.helper.mirror_utils.upload_utils.uploadserver.buzzheavier import BuzzHeavier
from bot.helper.mirror_utils.upload_utils.uploadserver.filester import Filester
from bot.helper.mirror_utils.upload_utils.uploadserver.filemirage import FileMirage
from bot.helper.mirror_utils.upload_utils.uploadserver.filebin import Filebin
from bot.helper.mirror_utils.upload_utils.uploadserver.gofile import Gofile
from bot.helper.mirror_utils.upload_utils.uploadserver.pixeldrain import PixelDrain
from bot.helper.mirror_utils.upload_utils.uploadserver.streamtape import Streamtape
from bot.helper.mirror_utils.upload_utils.uploadserver.storageto import StorageTo
from bot.helper.mirror_utils.upload_utils.uploadserver.transferit import TransferIt
from bot.helper.mirror_utils.upload_utils.uploadserver.vikingfile import VikingFile


class HostUploader:
    def __init__(self, listener=None, name=None, path=None, *, host: str | None = None):
        self.name = name
        self.__listener = listener
        self.__path = path
        self.__host = host
        self.__user_id = listener.message.from_user.id
        self.__upload_hosts = {}
        self.__processed_bytes = 0
        self.__file_base = 0
        self.__file_offset = 0
        self.__start_time = monotonic()
        self.total_files = 0
        self.total_folders = 0
        self.is_cancelled = False
        self.__engine = 'UploadHost'
        self.__asyncSession = None
        self.__task = None
        self.__terminal = False

    def report_progress(self, current):
        if current > self.__file_offset:
            self.__file_offset = current
            self.__processed_bytes = self.__file_base + current

    async def request_json(self, method, url, *, headers=None, params=None, json=None,
                           data=None, expected_statuses=(200,)):
        method = method.upper()
        timeout = ClientTimeout(total=60, connect=15, sock_read=30)
        try:
            async with self.__asyncSession.request(
                method, url, headers=headers, params=params, json=json, data=data,
                timeout=timeout,
            ) as response:
                if response.status not in expected_statuses:
                    raise RuntimeError(f'{method} failed with HTTP {response.status}.')
                try:
                    result = await response.json(content_type=None)
                except (ValueError, UnicodeDecodeError):
                    raise RuntimeError(f'{method} returned invalid JSON.') from None
                if not isinstance(result, dict):
                    raise RuntimeError(f'{method} returned an invalid JSON object.')
                return result
        except asyncio.TimeoutError:
            raise RuntimeError(f'{method} request timed out.') from None
        except (ClientError, OSError):
            raise RuntimeError(f'{method} request failed.') from None

    async def upload_aiohttp(self, url, file_path, req_file=None, data=None, headers=None,
                             method='POST', *, params=None, expected_statuses=(200,),
                             response_mode='json'):
        method = method.upper()
        if method not in ('POST', 'PUT'):
            raise ValueError('Upload method must be POST or PUT.')
        if response_mode not in ('json', 'none'):
            raise ValueError('Upload response mode must be json or none.')
        if method == 'POST' and not req_file:
            raise ValueError('A multipart file field is required for POST uploads.')
        timeout = ClientTimeout(total=7200, connect=60, sock_read=300)
        self.__file_base = self.__processed_bytes
        self.__file_offset = 0
        try:
            with ProgressFileReader(filename=file_path, read_callback=self.report_progress) as reader:
                if method == 'POST':
                    body = FormData()
                    for key, value in (data or {}).items():
                        if key != req_file:
                            body.add_field(key, value)
                    body.add_field(req_file, reader, filename=Path(file_path).name,
                                   content_type='application/octet-stream')
                else:
                    body = reader
                async with self.__asyncSession.request(
                    method, url, data=body, headers=headers, params=params, timeout=timeout,
                ) as response:
                    if response.status not in expected_statuses:
                        raise RuntimeError(f'{method} failed with HTTP {response.status}.')
                    if response_mode == 'none':
                        response.release()
                        return None
                    try:
                        result = await response.json(content_type=None)
                    except (ValueError, UnicodeDecodeError):
                        raise RuntimeError(f'{method} returned invalid JSON.') from None
                    if not isinstance(result, dict):
                        raise RuntimeError(f'{method} returned an invalid JSON object.')
                    return result
        except asyncio.TimeoutError:
            raise RuntimeError(f'{method} upload timed out.') from None
        except (ClientError, OSError):
            raise RuntimeError(f'{method} upload failed.') from None

    async def upload_chunk(self, url, file_path, offset, length):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.r2.cloudflarestorage.com'):
            raise RuntimeError('AkiraBox returned an invalid storage URL.')

        async def body():
            async with aiofiles.open(file_path, 'rb') as file:
                await file.seek(offset)
                remaining = length
                while remaining:
                    chunk = await file.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise RuntimeError('AkiraBox: file changed during upload.')
                    remaining -= len(chunk)
                    self.report_progress(offset + length - remaining)
                    yield chunk

        try:
            async with self.__asyncSession.put(
                url, data=body(), headers={'Content-Length': str(length)},
                allow_redirects=False,
                timeout=ClientTimeout(total=7200, connect=60, sock_read=300),
            ) as response:
                if response.status != 200 or not response.headers.get('ETag'):
                    raise RuntimeError('AkiraBox storage upload failed.')
                return response.headers['ETag']
        except (ClientError, OSError, asyncio.TimeoutError):
            raise RuntimeError('AkiraBox storage upload failed.') from None

    async def __upload_to_hosts(self, file_path):
        links = {}
        errors = []
        first_counts = None
        last_success_progress = None
        enabled = False
        names = {
            'gofile': 'GoFile',
            'streamtape': 'StreamTape',
            'pixeldrain': 'PixelDrain',
            'buzzheavier': 'BuzzHeavier',
            'akirabox': 'AkiraBox',
            'vikingfile': 'VikingFile',
            'filester': 'Filester',
            'filemirage': 'FileMirage',
            'transferit': 'Transfer.it',
            'storageto': 'storage.to',
            'filebin': 'Filebin',
        }
        for service, settings in self.__upload_hosts.items():
            if self.is_cancelled:
                raise asyncio.CancelledError
            if not settings[0]:
                continue
            enabled = True
            credential = settings[1]
            display = names.get(service)
            self.__engine = f'UploadHost ({display})' if display else 'UploadHost'
            self.total_files = self.total_folders = 0
            self.__processed_bytes = self.__file_base = self.__file_offset = 0
            self.__start_time = monotonic()
            try:
                if service == 'gofile':
                    adapter = Gofile(self, credential)
                elif service == 'streamtape':
                    login, separator, key = credential.partition(':') if isinstance(credential, str) else ('', '', '')
                    if not separator or not login or not key:
                        raise RuntimeError('StreamTape requires saved login:key credentials.')
                    adapter = Streamtape(self, login, key)
                elif service == 'pixeldrain':
                    if not isinstance(credential, str) or not credential:
                        raise RuntimeError('PixelDrain requires a saved API key.')
                    adapter = PixelDrain(self, credential)
                elif service == 'buzzheavier':
                    adapter = BuzzHeavier(self, credential)
                elif service == 'akirabox':
                    adapter = AkiraBox(self)
                elif service == 'vikingfile':
                    adapter = VikingFile(self, credential)
                elif service == 'filester':
                    adapter = Filester(self, credential)
                elif service == 'filemirage':
                    adapter = FileMirage(self, credential)
                elif service == 'transferit':
                    adapter = TransferIt(self)
                elif service == 'storageto':
                    adapter = StorageTo(self, credential)
                elif service == 'filebin':
                    adapter = Filebin(self)
                else:
                    safe_service = ''.join(c for c in str(service) if c.isascii() and (c.isalnum() or c in '_-'))[:40]
                    raise RuntimeError(f'Unsupported upload host: {safe_service or "unknown"}.')
                link = await adapter.upload(file_path)
                if self.is_cancelled:
                    raise asyncio.CancelledError
                try:
                    parsed = urlsplit(link) if isinstance(link, str) else None
                    valid_link = parsed and parsed.scheme.lower() in ('http', 'https') and parsed.hostname
                except ValueError:
                    valid_link = False
                if not valid_link:
                    raise RuntimeError('Provider returned an invalid upload link.')
                links[display] = link
                if first_counts is None:
                    first_counts = (self.total_files, self.total_folders)
                last_success_progress = (self.__processed_bytes, self.__file_base,
                                         self.__file_offset, self.__start_time)
            except RuntimeError as error:
                message = str(error).replace('<', '').replace('>', '')
                LOGGER.error('Upload Hosts %s: %s', display or 'unknown provider', message)
                errors.append(f'{display or "Upload Host"}: {message}')
            except Exception:
                LOGGER.error('Upload Hosts %s: upload failed.', display or 'unknown provider')
                errors.append(f'{display or "Upload Host"}: upload failed.')
        if self.is_cancelled:
            raise asyncio.CancelledError
        if not links:
            raise RuntimeError(' | '.join(errors) if enabled else 'No upload hosts are enabled.')
        self.total_files, self.total_folders = first_counts
        if last_success_progress is not None:
            (self.__processed_bytes, self.__file_base,
             self.__file_offset, self.__start_time) = last_success_progress
        return links

    async def __provider_work(self, item_path):
        async with ClientSession() as session:
            self.__asyncSession = session
            try:
                return await self.__upload_to_hosts(item_path)
            finally:
                self.__asyncSession = None

    async def upload(self, file_name, size):
        if self.__terminal:
            return
        try:
            if self.is_cancelled:
                raise asyncio.CancelledError
            settings = user_data.get(self.__user_id, {})
            saved = settings.get('upload_hosts', {})
            self.__upload_hosts = {
                key: (value[0], upload_host_credential(key, settings))
                for key, value in saved.items() if key in HOST_CREDENTIAL_VARS
            }
            if self.__host is not None:
                credential = upload_host_credential(self.__host, settings)
                self.__upload_hosts = {self.__host: (True, credential)}
            item_path = str(Path(self.__path) / file_name)
            mime_type = get_mime_type(item_path) if await aiopath.isfile(item_path) else 'Folder'
            if self.is_cancelled:
                raise asyncio.CancelledError
            self.__task = asyncio.create_task(self.__provider_work(item_path))
            links = await self.__task
            if self.is_cancelled:
                raise asyncio.CancelledError
        except asyncio.CancelledError:
            if not self.is_cancelled:
                raise
            self.__terminal = True
            await self.__listener.onUploadError('Your upload has been stopped!')
            return
        except Exception as error:
            self.__terminal = True
            message = str(error).replace('<', '').replace('>', '') if isinstance(error, RuntimeError) else 'Upload Hosts upload failed.'
            await self.__listener.onUploadError(message)
            return
        finally:
            self.__task = None
        self.__terminal = True
        await self.__listener.onUploadComplete(
            links, size, self.total_files, self.total_folders, mime_type, file_name,
        )

    @property
    def speed(self):
        elapsed = monotonic() - self.__start_time
        return self.__processed_bytes / elapsed if elapsed > 0 else 0

    @property
    def processed_bytes(self):
        return self.__processed_bytes

    @property
    def engine(self):
        return self.__engine

    async def cancel_download(self):
        if self.__terminal or self.is_cancelled:
            return
        self.is_cancelled = True
        if self.__task is not None and not self.__task.done():
            self.__task.cancel()
