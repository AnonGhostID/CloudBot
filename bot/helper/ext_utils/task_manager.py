#!/usr/bin/env python3
from time import time
from asyncio import Event
from functools import wraps

from bot import bot_cache, config_dict, queued_dl, queued_up, non_queued_up, non_queued_dl, queue_dict_lock, LOGGER, user_data, download_dict
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.fs_utils import get_base_name, check_storage_threshold
from bot.helper.ext_utils.bot_utils import get_user_tasks, getdailytasks, sync_to_async, get_telegraph_list, get_readable_file_size, checking_access, get_readable_time
from bot.helper.telegram_helper.message_utils import forcesub, check_botpm
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.themes import BotTheme


async def stop_duplicate_check(name, listener):
    if (
        not config_dict['STOP_DUPLICATE']
        or listener.isLeech
        or listener.upPath != 'gd'
        or listener.select
    ):
        return False, None
    LOGGER.info(f'Checking File/Folder if already in Drive: {name}')
    if listener.compress:
        name = f"{name}.zip"
    elif listener.extract:
        try:
            name = get_base_name(name)
        except Exception:
            name = None
    if name is not None:
        telegraph_content, contents_no = await sync_to_async(GoogleDriveHelper().drive_list, name, stopDup=True)
        if telegraph_content:
            msg = BotTheme('STOP_DUPLICATE', content=contents_no)
            button = await get_telegraph_list(telegraph_content)
            return msg, button
    return False, None
    

async def timeval_check(user_id):
    bot_cache.setdefault('time_interval', {})
    if (time_interval := bot_cache['time_interval'].get(user_id, False)) and (time() - time_interval) < (UTI := config_dict['USER_TIME_INTERVAL']): 
        return UTI - (time() - time_interval)
    bot_cache['time_interval'][user_id] = time()
    return None


def _has_queue_capacity(direction):
    all_limit = config_dict['QUEUE_ALL']
    limit = config_dict['QUEUE_DOWNLOAD' if direction == 'dl' else 'QUEUE_UPLOAD']
    active = non_queued_dl if direction == 'dl' else non_queued_up
    return (not all_limit or len(non_queued_dl) + len(non_queued_up) < all_limit) and (
        not limit or len(active) < limit
    )


def _start_from_queued():
    # Uploads retain priority, but a full upload limit must not block downloads.
    for direction, queued, active in (
        ('up', queued_up, non_queued_up),
        ('dl', queued_dl, non_queued_dl),
    ):
        while queued and _has_queue_capacity(direction):
            uid = next(iter(queued))
            event = queued.pop(uid)
            active.add(uid)
            event.set()


async def is_queued(uid, direction='dl'):
    queued, active = (queued_dl, non_queued_dl) if direction == 'dl' else (queued_up, non_queued_up)
    async with queue_dict_lock:
        if _has_queue_capacity(direction):
            active.add(uid)
            return False, None
        event = Event()
        queued[uid] = event
        return True, event


async def start_from_queued():
    async with queue_dict_lock:
        _start_from_queued()


async def release_queue(uid, direction=None):
    async with queue_dict_lock:
        for phase, queued, active in (
            ('dl', queued_dl, non_queued_dl),
            ('up', queued_up, non_queued_up),
        ):
            if direction is None or direction == phase:
                event = queued.pop(uid, None)
                if event is not None:
                    event.set()
                active.discard(uid)
        _start_from_queued()


async def wait_for_queue(uid, event, direction='dl'):
    try:
        await event.wait()
        async with queue_dict_lock:
            return uid in (non_queued_dl if direction == 'dl' else non_queued_up)
    except BaseException:
        await release_queue(uid, direction)
        raise


def queue_guard(get_uid):
    def decorate(func):
        @wraps(func)
        async def guarded(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BaseException:
                await release_queue(get_uid(*args, **kwargs))
                raise
        return guarded
    return decorate


async def limit_checker(size, listener, isTorrent=False, isDriveLink=False, isYtdlp=False, isPlayList=None):
    LOGGER.info('Checking Size Limit of link/file/folder/tasks...')
    user_id = listener.message.from_user.id 
    if await CustomFilters.sudo('', listener.message):
        return
    limit_exceeded = ''
    if listener.isClone:
        if CLONE_LIMIT := config_dict['CLONE_LIMIT']:
            limit = CLONE_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f'Clone limit is {get_readable_file_size(limit)}.'
    elif isDriveLink:
        if GDRIVE_LIMIT := config_dict['GDRIVE_LIMIT']:
            limit = GDRIVE_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f'Google drive limit is {get_readable_file_size(limit)}'
    elif isYtdlp:
        if YTDLP_LIMIT := config_dict['YTDLP_LIMIT']:
            limit = YTDLP_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f'Ytdlp limit is {get_readable_file_size(limit)}'
        if isPlayList != 0 and (PLAYLIST_LIMIT := config_dict['PLAYLIST_LIMIT']):
            if isPlayList > PLAYLIST_LIMIT:
                limit_exceeded = f'Playlist limit is {PLAYLIST_LIMIT}'
    elif isTorrent:
        if TORRENT_LIMIT := config_dict['TORRENT_LIMIT']:
            limit = TORRENT_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f'Torrent limit is {get_readable_file_size(limit)}'
    elif DIRECT_LIMIT := config_dict['DIRECT_LIMIT']:
        limit = DIRECT_LIMIT * 1024**3
        if size > limit:
            limit_exceeded = f'Direct limit is {get_readable_file_size(limit)}'

    if not limit_exceeded:
        if (LEECH_LIMIT := config_dict['LEECH_LIMIT']) and listener.isLeech:
            limit = LEECH_LIMIT * 1024**3
            if size > limit:
                limit_exceeded = f'Leech limit is {get_readable_file_size(limit)}'
        
        if (STORAGE_THRESHOLD := config_dict['STORAGE_THRESHOLD']) and not listener.isClone:
            arch = any([listener.compress, listener.extract])
            limit = STORAGE_THRESHOLD * 1024**3
            acpt = await sync_to_async(check_storage_threshold, size, limit, arch)
            if not acpt:
                limit_exceeded = f'You must leave {get_readable_file_size(limit)} free storage.'

        if config_dict['DAILY_TASK_LIMIT'] and config_dict['DAILY_TASK_LIMIT'] <= await getdailytasks(user_id):
            limit_exceeded = f"Daily Total Task Limit: {config_dict['DAILY_TASK_LIMIT']}\nYou have exhausted all your Daily Task Limits."
        else:
            ttask = await getdailytasks(user_id, increase_task=True)
            LOGGER.info(f"User: {user_id} | Daily Tasks: {ttask}")
        if (DAILY_MIRROR_LIMIT := config_dict['DAILY_MIRROR_LIMIT']) and not listener.isLeech:
            limit = DAILY_MIRROR_LIMIT * 1024**3
            if (size >= (limit - await getdailytasks(user_id, check_mirror=True)) or limit <= await getdailytasks(user_id, check_mirror=True)):
                limit_exceeded = f'Daily Mirror Limit is {get_readable_file_size(limit)}\nYou have exhausted all your Daily Mirror Limit.'
            elif not listener.isLeech:
                msize = await getdailytasks(user_id, upmirror=size, check_mirror=True)
                LOGGER.info(f"User : {user_id} | Daily Mirror Size : {get_readable_file_size(msize)}")
        if (DAILY_LEECH_LIMIT := config_dict['DAILY_LEECH_LIMIT']) and listener.isLeech:
            limit = DAILY_LEECH_LIMIT * 1024**3
            if (size >= (limit - await getdailytasks(user_id, check_leech=True)) or limit <= await getdailytasks(user_id, check_leech=True)):
                limit_exceeded = f'Daily Leech Limit is {get_readable_file_size(limit)}\nYou have exhausted all your Daily Leech Limit.'
            elif listener.isLeech:
                lsize = await getdailytasks(user_id, upleech=size, check_leech=True)
                LOGGER.info(f"User : {user_id} | Daily Leech Size : {get_readable_file_size(lsize)}")
    if limit_exceeded:
        if size:
            return f"{limit_exceeded}.\nYour List/File/Folder size is {get_readable_file_size(size)}."
        elif isPlayList != 0:
            return f"{limit_exceeded}.\nYour playlist has {isPlayList} files."


async def task_utils(message):
    LOGGER.info('Running Task Manager ...')
    msg = []
    button = None
    if await CustomFilters.sudo('', message):
        return msg, button
    user_id = message.from_user.id
    token_msg, button = await checking_access(user_id, button)
    if token_msg is not None:
        msg.append(token_msg)
    if message.chat.type != message.chat.type.BOT:
        if ids := config_dict['FSUB_IDS']:
            _msg, button = await forcesub(message, ids, button)
            if _msg:
                msg.append(_msg)
        user_dict = user_data.get(user_id, {})
        if config_dict['BOT_PM'] or user_dict.get('bot_pm') or config_dict['SAFE_MODE']:
            _msg, button = await check_botpm(message, button)
            if _msg:
                msg.append(_msg)
    if (uti := config_dict['USER_TIME_INTERVAL']) != 0 and (ut := await timeval_check(user_id)):
        msg.append(f"Please Wait {get_readable_time(ut)}, Users have time interval Restrictions for {get_readable_time(uti)}.")
    if (bmax_tasks := config_dict['BOT_MAX_TASKS']) and len(download_dict) >= bmax_tasks:
        msg.append(f"Bot Max Tasks limit exceeded.\nBot max tasks limit is {bmax_tasks}.\nPlease wait for the completion of other tasks.")
    if (maxtask := config_dict['USER_MAX_TASKS']) and await get_user_tasks(message.from_user.id, maxtask):
        msg.append(f"Your tasks limit exceeded for {maxtask} tasks")
    return msg, button
