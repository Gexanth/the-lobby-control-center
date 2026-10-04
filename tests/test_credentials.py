import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from credentials import save_login,load_login,forget_login,CredentialError
class CredentialsTest(unittest.TestCase):
    def test_token_never_written_to_settings(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch('credentials.save_token') as vault:save_login('secret-test-token','930828728966217728',root)
            vault.assert_called_once_with('secret-test-token')
            content=(root/'discord_login.json').read_text()
            self.assertNotIn('secret-test-token',content)
            with patch('credentials.os.name','nt'),patch('credentials.load_token',return_value='secret-test-token'):
                self.assertEqual(load_login(root),('secret-test-token','930828728966217728',True))
            with patch('credentials.os.name','nt'),patch('credentials.delete_token') as delete:forget_login(root)
            delete.assert_called_once();self.assertFalse((root/'discord_login.json').exists())
    def test_vault_failure_does_not_save_settings(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch('credentials.save_token',side_effect=CredentialError('failed')):
                with self.assertRaises(CredentialError):save_login('secret','123',root)
            self.assertFalse((root/'discord_login.json').exists())
