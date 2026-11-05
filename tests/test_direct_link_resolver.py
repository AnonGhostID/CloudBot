import asyncio
import importlib.util
from pathlib import Path
from threading import Event
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]


def load_resolver():
    bot = ModuleType('bot')
    bot.LOGGER = MagicMock()
    bot.config_dict = {'REAL_DEBRID_API': 'token'}
    utils = ModuleType('bot.helper.ext_utils.bot_utils')
    utils.get_readable_time = MagicMock()
    utils.is_share_link = MagicMock()
    utils.is_index_link = MagicMock()
    utils.is_magnet = lambda value: value.startswith('magnet:')
    errors = ModuleType('bot.helper.ext_utils.exceptions')
    errors.DirectDownloadLinkException = type('DirectDownloadLinkException', (Exception,), {})
    messages = ModuleType('bot.helper.ext_utils.help_messages')
    messages.PASSWORD_ERROR_MESSAGE = ''
    spec = importlib.util.spec_from_file_location(
        'resolver_test', ROOT / 'bot/helper/mirror_utils/download_utils/direct_link_generator.py'
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict('sys.modules', {
        'bot': bot,
        'bot.helper.ext_utils.bot_utils': utils,
        'bot.helper.ext_utils.exceptions': errors,
        'bot.helper.ext_utils.help_messages': messages,
    }):
        spec.loader.exec_module(module)
    return module


def response(status, data):
    return SimpleNamespace(status_code=status, json=lambda: data)


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.resolver = load_resolver()
        self.magnet = 'magnet:?xt=urn:btih:ABC123'

    def scraper(self, polling):
        replies = [
            response(200, {'abc123': {'rd': ['cached']}}),
            response(201, {'id': 'torrent'}),
            response(204, {}),
            *polling,
        ]
        scraper = MagicMock()
        scraper.request.side_effect = replies
        return scraper

    def test_session_and_scraper_default_timeout_and_override(self):
        with patch.object(self.resolver.RequestsSession, 'request') as request:
            session = self.resolver.Session()
            session.get('https://example.org')
            self.assertEqual(request.call_args.kwargs['timeout'], self.resolver.HTTP_TIMEOUT)
            session.get('https://example.org', timeout=7)
            self.assertEqual(request.call_args.kwargs['timeout'], 7)
        raw = MagicMock()
        raw_request = raw.request
        with patch.object(self.resolver, 'cloudscraper_create_scraper', return_value=raw):
            scraper = self.resolver.create_scraper()
            scraper.request('GET', 'https://example.org')
            self.assertEqual(raw_request.call_args.kwargs['timeout'], self.resolver.HTTP_TIMEOUT)

    def test_terminal_status_stops_polling(self):
        scraper = self.scraper([response(200, {'links': [], 'status': 'dead'})])
        with patch.object(self.resolver, 'create_scraper', return_value=scraper):
            with self.assertRaisesRegex(self.resolver.DirectDownloadLinkException, 'dead'):
                self.resolver.real_debrid(self.magnet, True)
        self.assertEqual(scraper.request.call_count, 4)

    def test_deadline_caps_request_and_stops_polling(self):
        scraper = self.scraper([response(200, {'links': [], 'status': 'downloading'})])
        with patch.object(self.resolver, 'create_scraper', return_value=scraper), \
             patch.object(self.resolver, 'REAL_DEBRID_POLL_TIMEOUT', 1), \
             patch.object(self.resolver, 'monotonic', side_effect=[10, 10.75, 11]):
            with self.assertRaisesRegex(self.resolver.DirectDownloadLinkException, 'timed out'):
                self.resolver.real_debrid(self.magnet, True)
        self.assertEqual(scraper.request.call_args.kwargs['timeout'], 0.25)

    def test_cancellation_interrupts_poll_wait(self):
        event = Event()
        scraper = self.scraper([response(200, {'links': [], 'status': 'downloading'})])
        event.wait = MagicMock(side_effect=lambda timeout: event.set() or True)
        with patch.object(self.resolver, 'create_scraper', return_value=scraper):
            with self.assertRaisesRegex(self.resolver.DirectDownloadLinkException, 'cancelled'):
                self.resolver.real_debrid(self.magnet, True, event)
        self.assertEqual(scraper.request.call_count, 4)

    def test_cached_torrent_returns_unrestricted_link(self):
        scraper = self.scraper([
            response(200, {'links': ['restricted'], 'status': 'downloaded',
                           'original_filename': 'folder', 'bytes': 10,
                           'files': [{'path': '/file.txt'}]}),
            response(200, {'filename': 'file.txt', 'download': 'https://example.org/file'}),
        ])
        with patch.object(self.resolver, 'create_scraper', return_value=scraper):
            self.assertEqual(self.resolver.real_debrid(self.magnet, True), 'https://example.org/file')


class ResolverTaskTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_command_reaches_worker_and_removes_status(self):
        bot = ModuleType('bot')
        bot.download_dict = {}
        bot.download_dict_lock = asyncio.Lock()
        utils = ModuleType('bot.helper.ext_utils.bot_utils')
        utils.MirrorStatus = SimpleNamespace(STATUS_DOWNLOADING='Downloading')
        started = asyncio.Event()
        release = asyncio.Event()

        async def sync_to_async(function, link, cancel_event):
            started.set()
            await release.wait()
            self.assertTrue(cancel_event.is_set())
            return 'result'

        utils.sync_to_async = sync_to_async
        errors = ModuleType('bot.helper.ext_utils.exceptions')
        errors.DirectDownloadLinkException = type('DirectDownloadLinkException', (Exception,), {})
        generator = ModuleType('bot.helper.mirror_utils.download_utils.direct_link_generator')
        generator.direct_link_generator = MagicMock()
        spec = importlib.util.spec_from_file_location(
            'resolver_task_test', ROOT / 'bot/helper/mirror_utils/download_utils/resolver_task.py'
        )
        module = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', {
            'bot': bot,
            'bot.helper.ext_utils.bot_utils': utils,
            'bot.helper.ext_utils.exceptions': errors,
            'bot.helper.mirror_utils.download_utils.direct_link_generator': generator,
        }):
            spec.loader.exec_module(module)
        resolving = asyncio.create_task(module.resolve_magnet(SimpleNamespace(id=42), 'magnet:'))
        await started.wait()
        await bot.download_dict[42].download().cancel_download()
        release.set()
        with self.assertRaisesRegex(errors.DirectDownloadLinkException, 'cancelled'):
            await resolving
        self.assertEqual(bot.download_dict, {})
