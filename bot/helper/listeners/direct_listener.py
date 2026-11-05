from ntpath import splitdrive
from pathlib import Path
from time import sleep

from bot import LOGGER, aria2
from bot.helper.ext_utils.bot_utils import async_to_sync, sync_to_async


def safe_download_path(root, directory, filename):
    if (not isinstance(directory, str) or not isinstance(filename, str)
            or not filename or filename in ('.', '..')
            or '/' in filename or '\\' in filename or '\0' in filename
            or splitdrive(filename)[0]):
        raise ValueError('Invalid download filename')
    if ('\\' in directory or '\0' in directory or directory.startswith('/')
            or splitdrive(directory)[0] or '..' in directory.split('/')):
        raise ValueError('Invalid download directory')
    root = Path(root).resolve()
    target = (root / directory / filename).resolve()
    if not target.is_relative_to(root) or target == root:
        raise ValueError('Download path escapes its destination')
    return root / directory / filename


class DirectListener:
    def __init__(self, foldername, total_size, path, listener, a2c_opt):
        self.__path = Path(path).resolve()
        self.__listener = listener
        self.__is_cancelled = False
        self.__a2c_opt = a2c_opt
        self.__proc_bytes = 0
        self.__failed = []
        self.task = None
        self.name = foldername
        self.total_size = total_size

    @property
    def processed_bytes(self):
        if self.task:
            return self.__proc_bytes + self.task.completed_length
        return self.__proc_bytes

    @property
    def speed(self):
        return self.task.download_speed if self.task else 0

    def download(self, contents):
        self.is_downloading = True
        for content in contents:
            if self.__is_cancelled:
                break
            filename = content['filename']
            try:
                target = safe_download_path(self.__path, content['path'], filename)
                safe_download_path(self.__path, content['path'], filename + '.aria2')
                self.__a2c_opt['dir'] = str(target.parent)
                self.__a2c_opt['out'] = filename
                self.task = aria2.add_uris([content['url']], self.__a2c_opt, position=0)
            except Exception as e:
                self.__failed.append(str(filename))
                LOGGER.error(f'Unable to download {filename} due to: {e}')
                continue
            self.task = self.task.live
            while True:
                if self.__is_cancelled:
                    if self.task:
                        self.task.remove(True, True)
                    break
                self.task = self.task.live
                if error_message:= self.task.error_message:
                    self.__failed.append(filename)
                    LOGGER.error(f'Unable to download {self.task.name} due to: {error_message}')
                    self.task.remove(True, True)
                    break
                elif self.task.is_complete:
                    self.__proc_bytes += self.task.total_length
                    self.task.remove(True)
                    break
                sleep(1)
            self.task = None
        if self.__is_cancelled:
            return
        if self.__failed:
            async_to_sync(
                self.__listener.onDownloadError,
                f"Failed to download {len(self.__failed)} file(s): " + ", ".join(self.__failed),
            )
            return
        async_to_sync(self.__listener.onDownloadComplete)

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f"Cancelling Download: {self.name}")
        await self.__listener.onDownloadError("Download Cancelled by User!")
        if self.task:
            await sync_to_async(self.task.remove, force=True, files=True)
