import importlib.util
from pathlib import Path
from types import ModuleType
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


def load_db_handler():
    bot = ModuleType('bot')
    bot.DATABASE_URL = ''
    bot.user_data = {}
    bot.rss_dict = {}
    bot.LOGGER = MagicMock()
    bot.bot_id = 'bot-id'
    bot.config_dict = {}
    bot.aria2_options = {}
    bot.qbit_options = {}
    bot.bot_loop = None
    path = Path(__file__).resolve().parents[1] / 'bot/helper/ext_utils/db_handler.py'
    spec = importlib.util.spec_from_file_location('db_handler_test', path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict('sys.modules', {'bot': bot}):
        spec.loader.exec_module(module)
    module.DATABASE_URL = 'mongodb://localhost'
    return module


class DbHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.module = load_db_handler()
        self.client = MagicMock()
        self.client.close = AsyncMock()
        self.client_factory = patch.object(self.module, 'AsyncMongoClient', return_value=self.client)
        self.client_factory.start()

    async def asyncTearDown(self):
        await self.module.DbManger.close()
        self.client_factory.stop()

    async def test_shared_client_is_closed_and_recreated(self):
        collection = self.client.cloudbot.settings.config
        collection.update_one = AsyncMock()
        await self.module.DbManger().update_config({'first': 1})
        await self.module.DbManger().update_config({'second': 2})
        self.module.AsyncMongoClient.assert_called_once_with('mongodb://localhost')
        self.client.close.assert_not_awaited()
        await self.module.DbManger.close()
        self.client.close.assert_awaited_once()
        await self.module.DbManger().update_config({'third': 3})
        self.assertEqual(self.module.AsyncMongoClient.call_count, 2)

    async def test_async_cursors_load_users_and_incomplete_tasks(self):
        db = self.client.cloudbot
        db.settings.config.update_one = AsyncMock()
        db.settings.aria2c.find_one = AsyncMock(return_value={})
        db.settings.qbittorrent.find_one = AsyncMock(return_value={})
        users = db.users['bot-id']
        users.update_many = AsyncMock()
        users.find_one = AsyncMock(return_value={'_id': 5})
        users.find.return_value.__aiter__.return_value = [{'_id': 5, 'is_sudo': True}]
        rss = db.rss['bot-id']
        rss.find_one = AsyncMock(return_value=None)
        tasks = db.tasks['bot-id']
        tasks.find_one = AsyncMock(return_value={'_id': 'link'})
        tasks.find.return_value.__aiter__.return_value = [
            {'_id': 'link', 'cid': 7, 'tag': 'user', 'source': 'source'}
        ]
        tasks.drop = AsyncMock()

        manager = self.module.DbManger()
        await manager.db_load()
        self.assertEqual(self.module.user_data, {5: {'is_sudo': True}})
        users.update_many.assert_awaited_once()
        self.assertEqual(await manager.get_incomplete_tasks(), {7: {'user': [{'link': 'source'}]}})
        tasks.drop.assert_awaited_once()
