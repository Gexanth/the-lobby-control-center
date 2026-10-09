import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from update_ui import UpdatePage

class UpdateTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_busy_retry_schedule_error_backoff_and_saved_opt_out(self):
        class Host:
            discord_worker=None
            calls=[]
            def run_discord_job(self,action,success,failure):self.calls.append((action,success,failure))
        h=Host()
        with tempfile.TemporaryDirectory() as tmp,patch('update_ui.DATA',Path(tmp)),patch.dict(os.environ,{'LOBBY_LAUNCHER':'1'}),patch('update_ui.time.monotonic',return_value=100):
            p=UpdatePage(h);p.timer.stop();h.discord_worker=object();p.auto_check();self.assertEqual(h.calls,[])
            self.assertIn('wartet',p.auto_status.text());h.discord_worker=None;p.auto_check();self.assertEqual(len(h.calls),1)
            self.assertEqual(p.next_check,1900);h.calls[-1][2]('network error');self.assertEqual(p.next_check,400)
            with patch('update_ui.time.monotonic',return_value=399):p.auto_check();self.assertEqual(len(h.calls),1)
            with patch('update_ui.time.monotonic',return_value=400):p.auto_check();self.assertEqual(len(h.calls),2)
            h.calls[-1][1]('bereit');self.assertEqual(p.next_check,1900)
            p.auto.setChecked(False);p.save_config();p.auto_check();self.assertEqual(len(h.calls),2);self.assertIn('deaktiviert',p.auto_status.text());p.close()
