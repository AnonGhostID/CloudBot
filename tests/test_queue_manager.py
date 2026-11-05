import asyncio
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import MagicMock, patch


class QueueManagerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        bot = ModuleType('bot')
        bot.bot_cache = {}
        bot.config_dict = {'QUEUE_ALL': '', 'QUEUE_DOWNLOAD': '', 'QUEUE_UPLOAD': ''}
        bot.queued_dl = {}
        bot.queued_up = {}
        bot.non_queued_dl = set()
        bot.non_queued_up = set()
        bot.queue_dict_lock = asyncio.Lock()
        bot.LOGGER = MagicMock()
        bot.user_data = {}
        bot.download_dict = {}
        dependencies = {
            'bot.helper.mirror_utils.upload_utils.gdriveTools': ['GoogleDriveHelper'],
            'bot.helper.ext_utils.fs_utils': ['get_base_name', 'check_storage_threshold'],
            'bot.helper.ext_utils.bot_utils': [
                'get_user_tasks', 'getdailytasks', 'sync_to_async', 'get_telegraph_list',
                'get_readable_file_size', 'checking_access', 'get_readable_time',
            ],
            'bot.helper.telegram_helper.message_utils': ['forcesub', 'check_botpm'],
            'bot.helper.telegram_helper.filters': ['CustomFilters'],
            'bot.helper.themes': ['BotTheme'],
        }
        modules = {'bot': bot}
        for name, attributes in dependencies.items():
            module = ModuleType(name)
            for attribute in attributes:
                setattr(module, attribute, MagicMock())
            modules[name] = module
        path = Path(__file__).resolve().parents[1] / 'bot/helper/ext_utils/task_manager.py'
        spec = importlib.util.spec_from_file_location('_queue_test_task_manager', path)
        self.manager = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(self.manager)
        self.bot = bot

    async def test_concurrent_admission_obeys_total_and_direction_caps(self):
        self.bot.config_dict.update(QUEUE_ALL=3, QUEUE_DOWNLOAD=2, QUEUE_UPLOAD=2)
        requests = [(uid, 'dl' if uid % 2 else 'up') for uid in range(20)]
        results = await asyncio.gather(*(self.manager.is_queued(uid, phase) for uid, phase in requests))
        self.assertEqual(sum(not queued for queued, _ in results), 3)
        self.assertEqual(len(self.bot.non_queued_dl) + len(self.bot.non_queued_up), 3)
        self.assertLessEqual(len(self.bot.non_queued_dl), 2)
        self.assertLessEqual(len(self.bot.non_queued_up), 2)
        self.assertEqual(len(self.bot.queued_dl) + len(self.bot.queued_up), 17)

    async def test_total_cap_applies_even_if_phase_has_spare_capacity(self):
        self.bot.config_dict.update(QUEUE_ALL=1, QUEUE_DOWNLOAD=3, QUEUE_UPLOAD=3)
        self.assertFalse((await self.manager.is_queued(1, 'up'))[0])
        queued, event = await self.manager.is_queued(2, 'dl')
        self.assertTrue(queued)
        self.assertFalse(event.is_set())
        await self.manager.release_queue(1, 'up')
        self.assertTrue(event.is_set())
        self.assertEqual(self.bot.non_queued_dl, {2})

    async def test_wakeups_reserve_slots_before_waiters_run(self):
        self.bot.config_dict.update(QUEUE_ALL=2, QUEUE_DOWNLOAD=2, QUEUE_UPLOAD=1)
        await self.manager.is_queued(1, 'dl')
        await self.manager.is_queued(2, 'dl')
        _, up_event = await self.manager.is_queued(3, 'up')
        _, dl_event = await self.manager.is_queued(4, 'dl')
        await self.manager.release_queue(1, 'dl')
        self.assertTrue(up_event.is_set())
        self.assertFalse(dl_event.is_set())
        self.assertEqual(self.bot.non_queued_up, {3})
        queued, _ = await self.manager.is_queued(5, 'up')
        self.assertTrue(queued)
        await self.manager.start_from_queued()
        self.assertFalse(dl_event.is_set())
        await self.manager.release_queue(2, 'dl')
        self.assertTrue(dl_event.is_set())
        self.assertEqual(len(self.bot.non_queued_dl) + len(self.bot.non_queued_up), 2)

    async def test_direction_only_limits_and_configuration_changes(self):
        self.bot.config_dict.update(QUEUE_DOWNLOAD=1, QUEUE_UPLOAD=1)
        await self.manager.is_queued(1, 'dl')
        await self.manager.is_queued(2, 'up')
        _, dl_event = await self.manager.is_queued(3, 'dl')
        _, up_event = await self.manager.is_queued(4, 'up')
        self.bot.config_dict['QUEUE_UPLOAD'] = ''
        await self.manager.start_from_queued()
        self.assertTrue(up_event.is_set())
        self.assertFalse(dl_event.is_set())
        self.bot.config_dict['QUEUE_DOWNLOAD'] = 2
        await self.manager.start_from_queued()
        self.assertTrue(dl_event.is_set())
        self.assertEqual(self.bot.non_queued_dl, {1, 3})

    async def test_full_upload_limit_does_not_block_queued_download(self):
        self.bot.config_dict.update(QUEUE_ALL=2, QUEUE_UPLOAD=1)
        await self.manager.is_queued(1, 'up')
        await self.manager.is_queued(2, 'dl')
        _, up_event = await self.manager.is_queued(3, 'up')
        _, dl_event = await self.manager.is_queued(4, 'dl')
        await self.manager.release_queue(2, 'dl')
        self.assertFalse(up_event.is_set())
        self.assertTrue(dl_event.is_set())

    async def test_cancel_waiting_task_and_wake_next(self):
        self.bot.config_dict['QUEUE_ALL'] = 1
        await self.manager.is_queued(1)
        _, cancelled = await self.manager.is_queued(2)
        _, next_event = await self.manager.is_queued(3)
        waiter = asyncio.create_task(self.manager.wait_for_queue(2, cancelled))
        await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        self.assertNotIn(2, self.bot.queued_dl)
        await self.manager.release_queue(1, 'dl')
        self.assertTrue(next_event.is_set())
        self.assertEqual(self.bot.non_queued_dl, {3})

    async def test_cancel_after_wakeup_releases_reserved_slot(self):
        self.bot.config_dict['QUEUE_ALL'] = 1
        await self.manager.is_queued(1)
        _, event = await self.manager.is_queued(2)
        _, next_event = await self.manager.is_queued(3)
        waiter = asyncio.create_task(self.manager.wait_for_queue(2, event))
        await asyncio.sleep(0)
        await self.manager.release_queue(1, 'dl')
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        self.assertTrue(next_event.is_set())
        self.assertEqual(self.bot.non_queued_dl, {3})

    async def test_explicit_cancellation_wakes_waiter_without_starting(self):
        self.bot.config_dict['QUEUE_ALL'] = 1
        await self.manager.is_queued(1, 'dl')
        _, event = await self.manager.is_queued(2, 'up')
        await self.manager.release_queue(2)
        self.assertFalse(await self.manager.wait_for_queue(2, event, 'up'))
        self.assertEqual(self.bot.non_queued_dl, {1})
        self.assertFalse(self.bot.non_queued_up)

    async def test_cancel_woken_upload_reservation_advances_queue(self):
        self.bot.config_dict['QUEUE_ALL'] = 1
        await self.manager.is_queued(1, 'dl')
        _, event = await self.manager.is_queued(2, 'up')
        _, next_event = await self.manager.is_queued(3, 'up')
        await self.manager.release_queue(1, 'dl')
        await self.manager.release_queue(2)
        self.assertFalse(await self.manager.wait_for_queue(2, event, 'up'))
        self.assertTrue(next_event.is_set())
        self.assertEqual(self.bot.non_queued_up, {3})

    async def test_cancel_before_queue_wait_releases_reservation(self):
        self.bot.config_dict['QUEUE_ALL'] = 1
        entered = asyncio.Event()

        @self.manager.queue_guard(lambda uid: uid)
        async def starting(uid):
            await self.manager.is_queued(uid)
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(starting(1))
        await entered.wait()
        _, event = await self.manager.is_queued(2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(event.is_set())
        self.assertEqual(self.bot.non_queued_dl, {2})

    async def test_transition_releases_download_before_upload_admission(self):
        self.bot.config_dict['QUEUE_ALL'] = 1
        await self.manager.is_queued(1, 'dl')
        _, dl_event = await self.manager.is_queued(2, 'dl')
        await self.manager.release_queue(1, 'dl')
        self.assertTrue(dl_event.is_set())
        queued, up_event = await self.manager.is_queued(1, 'up')
        self.assertTrue(queued)
        await self.manager.release_queue(2, 'dl')
        self.assertTrue(up_event.is_set())
        self.assertEqual(self.bot.non_queued_up, {1})
        self.assertFalse(self.bot.non_queued_dl)


if __name__ == '__main__':
    unittest.main()
