import asyncio
import json
import re
import sys
from pathlib import Path

from aiofiles.os import path as aiopath


class TransferIt:
    def __init__(self, uploader=None):
        self.uploader = uploader

    async def upload(self, file_path):
        if not await aiopath.exists(file_path):
            raise RuntimeError('Transfer.it: file not found.')
        if await aiopath.isdir(file_path):
            raise RuntimeError('Transfer.it does not support folder uploads.')
        if not await aiopath.isfile(file_path):
            raise RuntimeError('Transfer.it: path is not a regular file.')
        if self.uploader.is_cancelled:
            return None

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(Path(__file__).resolve()), str(Path(file_path).resolve()),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            )
        except OSError as error:
            raise RuntimeError('Transfer.it: could not start upload worker.') from error

        result = None
        error_message = None
        try:
            while line := await process.stdout.readline():
                try:
                    message = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    raise RuntimeError('Transfer.it: invalid response from upload worker.') from None
                if not isinstance(message, dict):
                    raise RuntimeError('Transfer.it: invalid response from upload worker.')
                if 'progress' in message and type(message['progress']) is int and message['progress'] >= 0:
                    self.uploader.report_progress(message['progress'])
                elif 'url' in message:
                    result = message['url']
                elif 'error' in message:
                    error_message = message['error']
            status = await process.wait()
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()

        if self.uploader.is_cancelled:
            return None
        if error_message:
            raise RuntimeError(f'Transfer.it: {error_message}')
        if status != 0:
            raise RuntimeError('Transfer.it: upload worker failed.')
        if not isinstance(result, str) or not re.fullmatch(r'https://transfer\.it/t/[A-Za-z0-9_-]{12}', result):
            raise RuntimeError('Transfer.it: invalid upload link.')
        self.uploader.total_files += 1
        return result


def _worker(file_path):
    if sys.path and Path(sys.path[0]).resolve() == Path(__file__).resolve().parent:
        sys.path.pop(0)

    def send(message):
        print(json.dumps(message), flush=True)

    try:
        from transferit import MegaAPIError, Transferit
    except ImportError:
        send({'error': 'transferit-py dependency is not installed.'})
        return 1

    try:
        with Transferit() as client:
            result = client.upload(file_path, on_progress=lambda sent, total: send({'progress': sent}))
        send({'url': result.url})
        return 0
    except MegaAPIError as error:
        if error.code is not None:
            send({'error': f'API error {error.code}.'})
        else:
            send({'error': 'upload failed in the Transfer.it client.'})
    except Exception as error:
        send({'error': f'upload failed ({type(error).__name__}).'})
    return 1


if __name__ == '__main__':
    sys.exit(_worker(sys.argv[1]))
