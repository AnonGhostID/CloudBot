from asyncio import CancelledError
from threading import Event
from uuid import uuid4

from bot import download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import MirrorStatus, sync_to_async
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.mirror_utils.download_utils.direct_link_generator import direct_link_generator


class ResolverTask:
    def __init__(self, message):
        self.message = message
        self.upload_details = {'mode': '-'}
        self.cancel_event = Event()
        self._gid = uuid4().hex[:12]

    def gid(self):
        return self._gid

    def name(self):
        return 'Resolving Real-Debrid magnet'

    def status(self):
        return MirrorStatus.STATUS_DOWNLOADING

    def size(self):
        return '0B'

    def processed_bytes(self):
        return '0B'

    def progress(self):
        return '0%'

    def speed(self):
        return '0B/s'

    def eta(self):
        return '-'

    def eng(self):
        return 'Real-Debrid'

    def download(self):
        return self

    async def cancel_download(self):
        self.cancel_event.set()


async def resolve_magnet(message, link):
    task = ResolverTask(message)
    async with download_dict_lock:
        download_dict[message.id] = task
    try:
        result = await sync_to_async(direct_link_generator, link, task.cancel_event)
        async with download_dict_lock:
            if task.cancel_event.is_set():
                raise DirectDownloadLinkException('ERROR: Real-Debrid resolution cancelled')
            if download_dict.get(message.id) is task:
                del download_dict[message.id]
        return result
    except CancelledError:
        task.cancel_event.set()
        raise
    finally:
        async with download_dict_lock:
            if download_dict.get(message.id) is task:
                del download_dict[message.id]
