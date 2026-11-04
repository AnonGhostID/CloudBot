from mimetypes import guess_extension
from os import path
from uuid import uuid4


def safe_filename(name, fallback='file'):
    """Turn an untrusted Telegram or user-supplied name into one path component."""
    name = (name or '').replace('\x00', '').replace('/', '_').replace('\\', '_')
    return name if name not in ('', '.', '..') else fallback


def media_filename(message):
    media = getattr(message, message.media.value) if message.media else None
    if media is None:
        raise ValueError('Message has no downloadable media')
    name = getattr(media, 'file_name', None)
    if not name or name in ('.', '..'):
        extension = guess_extension(getattr(media, 'mime_type', None) or '') or ''
        if not extension and getattr(message, 'photo', None):
            extension = '.jpg'
        name = f"{getattr(media, 'file_unique_id', None) or 'file'}{extension}"
    return safe_filename(name)


def download_path(directory, name):
    destination = path.abspath(path.join(directory, safe_filename(name)))
    if path.isdir(destination):
        raise IsADirectoryError(f'Download destination is a directory: {destination}')
    return destination


def temporary_download_path(message):
    extension = path.splitext(media_filename(message))[1]
    if len(extension) > 16:
        extension = ''
    return download_path('downloads', f'{uuid4().hex}{extension}')
