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

    def test_review_cancel_and_confirm_with_fake_discord(self):
        from datetime import datetime,timezone,timedelta
        from lobby import Lobby
        from PySide6.QtWidgets import QMessageBox
        c=self.w.community;guild='930828728966217728';channel='123456789012345678';calls=[]
        def transport(method,path,payload,reason):
            calls.append(method)
            if method=='GET':return {'guild_id':guild,'type':0}
            return {'id':'123456789012345679','channel_id':channel}
        self.w.discord_client=Lobby('test',guild,writes=True,db=self.root/'audit.db',transport=transport)
        self.w.show_discord({'id':guild,'name':'test','channels':[{'id':channel,'name':'vote','type':0}],'roles':[]})
        c.store.add_night(guild,'Night',(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'Game A\nGame B');c.refresh();c.nights.setCurrentRow(0)
        def synchronous(action,success,failure):
            try:result=action()
            except Exception as exc:failure(str(exc));return
            success(result)
        with patch.object(self.w,'run_discord_job',side_effect=synchronous),patch.object(QMessageBox,'question',return_value=QMessageBox.No):c.review_poll()
        self.assertEqual(calls,[])
        with patch.object(self.w,'run_discord_job',side_effect=synchronous),patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):c.review_poll()
        self.assertEqual(calls,['GET','POST'])
        self.assertIn('Veröffentlicht',c.poll_status.text())
        with patch.object(self.w,'run_discord_job',side_effect=synchronous):c.review_poll()
        self.assertEqual(calls,['GET','POST'])

    def test_confirmed_schedule_records_without_sending(self):
        from datetime import datetime,timezone,timedelta
        from lobby import Lobby
        from PySide6.QtWidgets import QMessageBox
        c=self.w.community;guild='930828728966217728';channel='123456789012345678'
        def forbidden(*args):raise AssertionError('No requests during scheduling')
        self.w.discord_client=Lobby('test',guild,writes=True,transport=forbidden)
        self.w.show_discord({'id':guild,'name':'test','channels':[{'id':channel,'name':'vote','type':0}],'roles':[]})
        c.store.add_night(guild,'Night',(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'Game A\nGame B');c.refresh();c.nights.setCurrentRow(0)
        c.poll_send_time.setText((datetime.now()+timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'))
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):c.review_poll(True)
        self.assertEqual(c.chosen_night()['poll_delivery']['state'],'scheduled')
        self.assertFalse(c.poll_publish.isEnabled());self.assertTrue(c.poll_unschedule.isEnabled())
        c.stop_scheduled_poll();self.assertEqual(c.chosen_night()['poll_delivery']['state'],'ready')

    def test_due_dispatch_waits_for_connection_and_sends_once(self):
        from datetime import datetime,timezone,timedelta
        from lobby import Lobby
        from polls import PollJournal,poll_spec
        c=self.w.community;guild='930828728966217728';channel='123456789012345678';calls=[]
        def transport(method,path,payload,reason):
            calls.append(method)
            if method=='GET':return {'guild_id':guild,'type':0}
            return {'id':'123456789012345679','channel_id':channel}
        client=Lobby('test',guild,writes=True,db=self.root/'audit.db',transport=transport)
        self.w.discord_client=client
        self.w.show_discord({'id':guild,'name':'test','channels':[{'id':channel,'name':'vote','type':0}],'roles':[]})
        c.store.add_night(guild,'Night',(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'Game A\nGame B');c.refresh();c.nights.setCurrentRow(0)
        n=c.chosen_night();spec=poll_spec(guild,n,channel,24,False)
        PollJournal(c.store).schedule(spec,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())
        n['poll_delivery']['send_at']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat();c.store.save()
        self.w.discord_client=None;c.dispatch_scheduled_poll();self.assertEqual(calls,[])
        client.guild='123456789012345680';self.w.discord_client=client;c.dispatch_scheduled_poll();self.assertEqual(calls,[])
        client.guild=guild;self.w.discord_worker=object();c.dispatch_scheduled_poll();self.assertEqual(calls,[])
        self.w.discord_worker=None
        def synchronous(action,success,failure):
            try:result=action()
            except Exception as exc:failure(str(exc));return
            success(result)
        with patch.object(self.w,'run_discord_job',side_effect=synchronous):
            c.dispatch_scheduled_poll();c.dispatch_scheduled_poll()
        self.assertEqual(calls,['GET','POST']);self.assertEqual(n['poll_delivery']['state'],'sent')

    def test_schedule_feedback_matches_expiry_and_cancellation(self):
        from datetime import datetime,timezone,timedelta
        from polls import PollJournal,poll_spec
        c=self.w.community;guild='930828728966217728';channel='123456789012345678'
        c.offline_server.setCurrentText(guild);c.open_offline()
        c.store.add_night(guild,'Night',(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'Game A\nGame B');c.refresh();c.nights.setCurrentRow(0)
        n=c.chosen_night();spec=poll_spec(guild,n,channel,24,False)
        PollJournal(c.store).schedule(spec,(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat());c.refresh()
        self.assertIn('1 geplant',self.w.community_summary.text())
        n['poll_delivery']['send_at']=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat();c.dispatch_scheduled_poll()
        self.assertIn('fällig',c.poll_status.text());self.assertIn('1 fällig',self.w.community_summary.text())
        n['when']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat();c.dispatch_scheduled_poll()
        self.assertIn('abgelaufen',c.poll_status.text());self.assertIn('0 fällig',self.w.community_summary.text())
        self.assertFalse(c.poll_publish.isEnabled());self.assertFalse(c.poll_unschedule.isHidden())
        n['status']='abgesagt';c.dispatch_scheduled_poll();self.assertIn('abgesagt',c.poll_status.text())

    def test_dashboard_keeps_local_work_when_disconnected(self):
        from datetime import datetime,timezone,timedelta
        from PySide6.QtCore import Qt
        c=self.w.community;guild='930828728966217728'
        c.offline_server.setCurrentText(guild);c.open_offline()
        self.w.store.add('<b>Local task</b>');done=self.w.store.add('Done');self.w.store.update(done['id'],'Erledigt','');self.w.refresh_tasks()
        now=datetime.now(timezone.utc)
        c.store.add_night(guild,'Upcoming',(now+timedelta(days=1)).isoformat(),'A\nB')
        canceled=c.store.add_night(guild,'Canceled',(now+timedelta(days=2)).isoformat(),'A\nB');c.store.cancel_night(guild,canceled['id'])
        old=c.store.add_night(guild,'Past',(now+timedelta(days=3)).isoformat(),'A\nB');old['when']=(now-timedelta(days=1)).isoformat();old['reminded']=True;c.store.save();c.refresh()
        class Client:pass
        client=Client();client.guild=guild;self.w.discord_client=client
        self.w.show_discord({'id':guild,'name':'test','channels':[],'roles':[],'approximate_members_including_bots':70,'online_now_not_weekly_activity':22})
        d=self.w.dashboard_page
        self.assertEqual(d.values['members'].text(),'70');self.assertTrue(d.badge.property('connected'))
        self.w.disconnect_discord()
        self.assertEqual(d.values['members'].text(),'—');self.assertEqual(d.values['tasks'].text(),'1');self.assertFalse(d.badge.property('connected'))
        self.assertIn('Upcoming',d.nights.text());self.assertNotIn('Canceled',d.nights.text());self.assertNotIn('Past',d.nights.text())
        self.assertIn('<b>Local task</b>',d.task_preview.text());self.assertEqual(d.task_preview.textFormat(),Qt.PlainText)

    def test_dashboard_buttons_keep_navigation_and_offline_access(self):
        from PySide6.QtWidgets import QPushButton
        d=self.w.dashboard_page
        for text,tab in [('Aktivität öffnen',0),('Lobby Night öffnen',1),('Creator Hub öffnen',2)]:
            button=next(b for b in d.findChildren(QPushButton) if b.text()==text);button.click()
            self.assertEqual(self.w.stack.currentIndex(),7);self.assertEqual(self.w.community.tabs.currentIndex(),tab)
            self.assertTrue(self.w.nav_buttons[7].isChecked());self.assertTrue(self.w.community.tabs.isEnabled())
        d.connection_button.click();self.assertEqual(self.w.stack.currentIndex(),2)
        next(b for b in d.findChildren(QPushButton) if b.text()=='Aufgaben verwalten').click();self.assertEqual(self.w.stack.currentIndex(),3)
        for index,b in enumerate(self.w.nav_buttons):b.click();self.assertEqual(self.w.stack.currentIndex(),index)
        self.w.stack.setCurrentIndex(0);self.app.processEvents()
        self.assertEqual(self.w.stack.currentWidget().horizontalScrollBar().maximum(),0)
