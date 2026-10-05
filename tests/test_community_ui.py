"""Regression checks for community access before connection and after restart."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PySide6.QtWidgets import QApplication
    QT=True
except ImportError:QT=False

@unittest.skipUnless(QT,'PySide6 not installed')
class CommunityAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        import main,community_ui
        from community import CommunityStore
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.task_patch=patch.object(main,'TASK_FILE',self.root/'tasks.json');self.task_patch.start()
        self.store_patch=patch.object(community_ui,'CommunityStore',lambda:CommunityStore(self.root));self.store_patch.start()
        self.login_patch=patch.object(main,'load_login',return_value=('','',False));self.login_patch.start()
        self.read_patch=patch.object(community_ui,'read_json',return_value={});self.read_patch.start()
        self.w=main.MainWindow();self.w.show();self.app.processEvents()
    def tearDown(self):
        self.w.close();self.app.processEvents()
        self.read_patch.stop();self.login_patch.stop();self.store_patch.stop();self.task_patch.stop();self.tmp.cleanup()
    def test_all_tabs_available_offline_and_connection_shortcut(self):
        c=self.w.community
        self.assertTrue(c.tabs.isEnabled());self.assertFalse(c.scan.isEnabled())
        for i in range(c.tabs.count()):c.tabs.setCurrentIndex(i);self.app.processEvents();self.assertEqual(c.tabs.currentIndex(),i)
        c.open_connection();self.assertEqual(self.w.stack.currentIndex(),2)
    def test_offline_planning_disconnect_and_wrong_server_block(self):
        from datetime import datetime,timedelta
        c=self.w.community;guild='930828728966217728'
        c.offline_server.setCurrentText(guild);c.open_offline()
        self.assertEqual(c.guild_id,guild)
        c.night_time.setText((datetime.now()+timedelta(days=1)).strftime('%Y-%m-%d 20:00'));c.options.setPlainText('Game A\nGame B');c.add_night()
        self.assertEqual(c.nights.count(),1)
        class Client:pass
        client=Client();client.guild=guild;client.token='test';self.w.discord_client=client
        self.w.show_discord({'id':guild,'name':'test','channels':[{'id':'123456789012345678','name':'chat','type':0}],'roles':[]})
        self.assertTrue(c.scan.isEnabled())
        self.w.disconnect_discord();self.assertTrue(c.tabs.isEnabled());self.assertFalse(c.scan.isEnabled());self.assertEqual(c.nights.count(),1)
        client.guild='123456789012345679';self.w.discord_client=client;c.refresh_connection_controls();self.assertFalse(c.scan.isEnabled())
        c.sample();self.assertIn('verbinden',c.status.text())
