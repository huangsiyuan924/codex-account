import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'codex-account'


def credential(name, refreshed='2026-01-01T00:00:00Z'):
    # Deliberately not JWTs or usable authentication credentials.
    return json.dumps({
        'auth_mode': 'chatgpt',
        'tokens': {'account_id': 'test-account-' + name,
                   'access_token': 'FAKE-ACCESS-' + name,
                   'refresh_token': 'FAKE-REFRESH-' + name},
        'last_refresh': refreshed,
    }).encode()


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'codex-home'
        self.home.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        fake = self.bin / 'codex'
        fake.write_text('''#!''' + sys.executable + '''
import os, sys
from pathlib import Path
root = Path(os.environ['TEST_ROOT'])
home = Path(os.environ['CODEX_HOME'])
if sys.argv[1:] == ['-c', 'cli_auth_credentials_store="file"', 'login']:
    if (root / 'fail-login').exists():
        sys.exit(1)
    (home / 'auth.json').write_bytes((root / 'login-auth').read_bytes())
    sys.exit(0)
assert sys.argv[1:] == ['app-server', 'daemon', 'stop'], sys.argv
with (root / 'stops').open('a') as file:
    file.write('stop\\n')
if (root / 'fail-stop').exists():
    sys.exit(1)
if (root / 'shutdown-auth').exists():
    (home / 'auth.json').write_bytes((root / 'shutdown-auth').read_bytes())
''')
        fake.chmod(0o755)
        self.env = {**os.environ, 'CODEX_HOME': str(self.home),
                    'TEST_ROOT': str(self.root),
                    'PATH': str(self.bin) + os.pathsep + os.environ.get('PATH', '')}

    def run_cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *args],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        self.assertNotIn('FAKE-ACCESS-', result.stdout + result.stderr)
        self.assertNotIn('FAKE-REFRESH-', result.stdout + result.stderr)
        return result.stdout

    def active(self, name):
        (self.home / 'auth.json').write_bytes(credential(name))

    def saved(self, name):
        return self.home / 'accounts' / (name + '.json')

    def bootstrap(self):
        self.active('personal')
        self.run_cli('save', 'personal')
        (self.root / 'login-auth').write_bytes(credential('work'))
        self.run_cli('add', 'work')

    def daemon(self):
        directory = self.home / 'app-server-daemon'
        directory.mkdir()
        (directory / 'daemon.pid').write_text('{}')

    def test_empty_home_can_add_first_login(self):
        (self.root / 'login-auth').write_bytes(credential('personal'))
        self.run_cli('add', 'personal')
        self.assertFalse((self.home / 'auth.json').exists())
        self.run_cli('personal')
        self.assertEqual((self.home / 'auth.json').read_bytes(), credential('personal'))

    def test_save_add_list_switch_cycle(self):
        self.bootstrap()
        self.assertEqual((self.home / 'auth.json').read_bytes(), credential('personal'))
        self.assertEqual(self.run_cli('list').splitlines(), ['* personal', '  work'])
        self.run_cli('work')
        self.assertIn('work', self.run_cli('status'))
        self.run_cli()
        self.assertEqual((self.home / 'auth.json').read_bytes(), credential('personal'))
        self.assertEqual(self.saved('work').stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.saved('work').parent.stat().st_mode & 0o777, 0o700)

    def test_import_and_duplicate_protection(self):
        self.bootstrap()
        source = self.root / 'source.json'
        source.write_bytes(credential('third'))
        self.run_cli('import', 'third', str(source))
        self.assertEqual(self.saved('third').read_bytes(), source.read_bytes())
        self.run_cli('import', 'duplicate', str(source), success=False)
        self.assertFalse(self.saved('duplicate').exists())
        self.run_cli('add', 'third', success=False)

    def test_invalid_names_and_arguments(self):
        for args in [('add', '../escape'), ('save', 'status'), ('add',),
                     ('import', 'x'), ('foo', 'bar'), ('add', '1bad')]:
            with self.subTest(args=args):
                self.run_cli(*args, success=False)

    def test_unknown_current_account_is_preserved(self):
        self.bootstrap()
        self.active('unknown')
        self.run_cli('work', success=False)
        self.assertEqual((self.home / 'auth.json').read_bytes(), credential('unknown'))

    def test_daemon_shutdown_can_write_another_saved_account(self):
        self.bootstrap()
        self.daemon()
        newer = credential('work', '2026-02-01T00:00:00Z')
        (self.root / 'shutdown-auth').write_bytes(newer)
        self.run_cli('personal')
        self.assertEqual(self.saved('work').read_bytes(), newer)
        self.assertEqual(self.saved('personal').read_bytes(), credential('personal'))
        self.assertEqual((self.home / 'auth.json').read_bytes(), credential('personal'))
        self.assertEqual((self.root / 'stops').read_text(), 'stop\n')

    def test_failed_stop_preserves_all_credentials(self):
        self.bootstrap()
        self.daemon()
        (self.root / 'fail-stop').touch()
        self.run_cli('work', success=False)
        self.assertEqual((self.home / 'auth.json').read_bytes(), credential('personal'))
        self.assertEqual(self.saved('personal').read_bytes(), credential('personal'))
        self.assertEqual(self.saved('work').read_bytes(), credential('work'))

    def test_same_account_switch_still_stops_daemon(self):
        self.bootstrap()
        self.daemon()
        self.run_cli('personal')
        self.assertTrue((self.root / 'stops').exists())

    def test_renew_same_account_keeps_newer_saved_tokens(self):
        self.bootstrap()
        newer = credential('personal', '2026-03-01T00:00:00Z')
        (self.root / 'login-auth').write_bytes(newer)
        self.run_cli('login', 'personal')
        self.assertEqual((self.home / 'auth.json').read_bytes(), newer)
        self.assertEqual(self.saved('personal').read_bytes(), newer)

    def test_wrong_login_and_cancel_preserve_credentials(self):
        self.bootstrap()
        self.run_cli('login', 'personal', success=False)
        self.assertEqual(self.saved('personal').read_bytes(), credential('personal'))
        (self.root / 'fail-login').touch()
        self.run_cli('add', 'third', success=False)
        self.assertFalse(self.saved('third').exists())

    def test_malformed_auth_stops_before_daemon(self):
        self.bootstrap()
        self.daemon()
        self.saved('work').write_text('not JSON')
        self.run_cli('work', success=False)
        self.assertFalse((self.root / 'stops').exists())
        self.assertEqual((self.home / 'auth.json').read_bytes(), credential('personal'))

    def test_non_file_storage_is_rejected(self):
        self.active('personal')
        (self.home / 'config.toml').write_text('cli_auth_credentials_store = "keyring"\n')
        self.run_cli('save', 'personal', success=False)
        self.assertFalse(self.saved('personal').exists())

    def test_legacy_backups_are_discovered_without_rewriting(self):
        self.active('personal')
        (self.home / 'auth_main.json').write_bytes(credential('personal'))
        (self.home / 'auth_l.json').write_bytes(credential('work'))
        self.assertEqual(self.run_cli('list').splitlines(), ['* huang', '  li'])
        self.run_cli('li')
        self.assertEqual((self.home / 'auth.json').read_bytes(), credential('work'))


if __name__ == '__main__':
    unittest.main()
