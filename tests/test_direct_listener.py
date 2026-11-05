import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


LISTENER_PATH = Path(__file__).resolve().parents[1] / 'bot/helper/listeners/direct_listener.py'


def load_listener(aria2):
    bot = types.ModuleType('bot')
    bot.LOGGER = Mock()
    bot.aria2 = aria2
    utils = types.ModuleType('bot.helper.ext_utils.bot_utils')
    utils.async_to_sync = lambda callback, *args: callback(*args)
    utils.sync_to_async = Mock()
    spec = importlib.util.spec_from_file_location('_direct_listener_test', LISTENER_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'bot': bot, 'bot.helper.ext_utils.bot_utils': utils}):
        spec.loader.exec_module(module)
    return module


def finished_task(error=''):
    task = Mock()
    task.live = task
    task.error_message = error
    task.is_complete = not error
    task.total_length = 12
    return task


class DirectListenerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'downloads'
        self.root.mkdir()
        self.aria2 = Mock()
        self.module = load_listener(self.aria2)
        self.callback = Mock()
        self.listener = self.module.DirectListener('folder', 24, self.root, self.callback, {})

    def content(self, filename, directory=''):
        return {'filename': filename, 'path': directory, 'url': 'https://example.com/file'}

    def test_successful_nested_download(self):
        self.aria2.add_uris.return_value = finished_task()
        self.listener.download([self.content('file.txt', 'folder/subfolder')])
        options = self.aria2.add_uris.call_args.args[1]
        self.assertEqual(options['dir'], str(self.root / 'folder/subfolder'))
        self.assertEqual(options['out'], 'file.txt')
        self.callback.onDownloadComplete.assert_called_once_with()
        self.callback.onDownloadError.assert_not_called()
        self.assertEqual(self.listener.processed_bytes, 12)

    def test_rejects_traversal_absolute_paths_and_invalid_filenames(self):
        entries = [self.content('a', '../escape'), self.content('b', '/tmp'),
                   self.content('../outside'), self.content('/absolute'),
                   self.content('..\\outside'), self.content('C:\\outside')]
        self.listener.download(entries)
        self.aria2.add_uris.assert_not_called()
        self.callback.onDownloadComplete.assert_not_called()
        error = self.callback.onDownloadError.call_args.args[0]
        for entry in entries:
            self.assertIn(entry['filename'], error)

    def test_rejects_escaping_directory_file_and_control_file_symlinks(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (self.root / 'linked').symlink_to(outside, target_is_directory=True)
        (self.root / 'file').symlink_to(outside / 'file')
        (self.root / 'control.aria2').symlink_to(outside / 'control.aria2')
        self.listener.download([self.content('nested', 'linked'), self.content('file'),
                                self.content('control')])
        self.aria2.add_uris.assert_not_called()
        self.callback.onDownloadComplete.assert_not_called()
        error = self.callback.onDownloadError.call_args.args[0]
        for name in ('nested', 'file', 'control'):
            self.assertIn(name, error)

    def test_partial_failure_reports_all_failed_filenames(self):
        self.aria2.add_uris.side_effect = [finished_task(), RuntimeError('RPC failure'),
                                          finished_task('network failure')]
        self.listener.download([self.content('good'), self.content('rpc-error'),
                                self.content('transfer-error')])
        self.callback.onDownloadComplete.assert_not_called()
        self.callback.onDownloadError.assert_called_once()
        error = self.callback.onDownloadError.call_args.args[0]
        self.assertIn('rpc-error', error)
        self.assertIn('transfer-error', error)
        self.assertNotIn('good', error)
        self.assertEqual(self.listener.processed_bytes, 12)

    def test_task_folder_is_contained_in_download_base(self):
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (self.root / 'linked').symlink_to(outside, target_is_directory=True)
        for name in ('../outside', '/tmp', 'linked', '..\\outside'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.module.safe_download_path(self.root, '', name)
        self.assertEqual(self.module.safe_download_path(self.root, '', 'safe'), self.root / 'safe')


if __name__ == '__main__':
    unittest.main()
