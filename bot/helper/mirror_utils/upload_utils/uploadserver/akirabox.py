from math import ceil
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import quote

from aiofiles.os import path as aiopath
from aiohttp import FormData


class AkiraBox:
    MAX_SIZE = 5 * 1024 ** 3

    def __init__(self, uploader):
        self.uploader = uploader
        self.api_url = 'https://akirabox.to/api/upload'

    async def upload(self, file_path):
        if not await aiopath.isfile(file_path):
            raise RuntimeError('AkiraBox accepts a single regular file, not a folder.')
        size = await aiopath.getsize(file_path)
        if size > self.MAX_SIZE:
            raise RuntimeError('AkiraBox guest uploads are limited to 5 GB per file.')
        if not size:
            raise RuntimeError('AkiraBox does not accept empty files.')

        path = Path(file_path)
        extension = path.suffix.lstrip('.')
        content_type = guess_type(path.name)[0] or 'application/octet-stream'
        fields = {
            'name': path.stem, 'visibility': 'public', 'password': '',
            'description': '', 'filename': path.name, 'size': str(size), 'type': content_type,
        }
        form = FormData()
        for key, value in fields.items():
            form.add_field(key, value, content_type='text/plain')
        upload = await self.uploader.request_json('POST', self.api_url, data=form)
        if upload.get('ok') is not True or not isinstance(upload.get('key'), str) or not upload['key']:
            raise RuntimeError('AkiraBox returned an invalid upload session.')
        params = {'key': upload['key'], 'providerId': upload.get('providerId', '')}
        if upload.get('bucket'):
            params['bucket'] = upload['bucket']

        if upload.get('simple') and upload.get('putUrl'):
            await self.uploader.upload_chunk(upload['putUrl'], file_path, 0, size)
            payload = {'metadata': upload.get('metadata'), 'filesize': size}
        else:
            upload_id = upload.get('uploadId')
            if not isinstance(upload_id, str) or not upload_id:
                raise RuntimeError('AkiraBox returned an invalid upload session.')
            mib = 1024 * 1024
            groups = max(1, ceil(size / (192 * mib)))
            chunk_size = max(6 * mib, mib * ceil(size / (6 * groups * mib)), mib * ceil(size / (10000 * mib)))
            parts = []
            for index, offset in enumerate(range(0, size, chunk_size), 1):
                query = dict(params, uploadId=upload_id, **{'part-number': str(index)})
                signed = await self.uploader.request_json('GET', f'{self.api_url}/chunk-url', params=query)
                url = signed.get('url')
                if not isinstance(url, str) or not url:
                    raise RuntimeError('AkiraBox returned an invalid chunk URL.')
                etag = await self.uploader.upload_chunk(url, file_path, offset, min(chunk_size, size - offset))
                parts.append({'PartNumber': index, 'ETag': etag})
            payload = {
                'UploadId': upload_id, 'metadata': upload.get('metadata'),
                'MultipartUpload': {'Parts': parts}, 'filename': path.stem,
                'filesize': size, 'fileExtension': extension, 'filetype': content_type,
                'visibility': 1, 'password': '', 'description': '',
            }
        result = await self.uploader.request_json('POST', f'{self.api_url}/complete', params=params, json=payload)
        file_id = result.get('id')
        if not isinstance(file_id, str) or not file_id:
            raise RuntimeError('AkiraBox returned an invalid upload response.')
        self.uploader.total_files += 1
        return f'https://akirabox.to/{quote(file_id, safe="")}/file'
