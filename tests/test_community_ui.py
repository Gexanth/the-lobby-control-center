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

    def test_activity_ages_without_requests_or_losing_draft(self):
        from datetime import datetime,timezone,timedelta
        c=self.w.community;guild='930828728966217728';channel='123456789012345678'
        now=datetime.now(timezone.utc)
        sample={'channel_id':channel,'checked_at':now.isoformat(),'messages':8,'participants':2,
                'messages_24h':8,'participants_24h':2,'sample_size':8,'oldest':now.isoformat(),
                'latest':now.isoformat(),'coverage':'history_end'}
        c.store.record_activity(guild,sample);c.offline_server.setCurrentText(guild);c.open_offline()
        self.assertIn('24h vor Erfassung',c.activity_metrics.text())
        self.assertIn('Aktuelle',c.activity_quality.text())
        c.engagement_draft.setPlainText('Mein bearbeiteter Entwurf');c.engagement_draft.document().setModified(True)
        history_item=c.history_table.item(0,0)
        with patch('engagement.utcnow',return_value=now+timedelta(hours=7)),patch.object(self.w,'run_discord_job',side_effect=AssertionError('No Discord request')):
            c.timer.timeout.emit()
        self.assertIn('Veraltet',c.activity_quality.text());self.assertIn('sechs Stunden',c.engagement_basis.text())
        self.assertEqual(c.engagement_select.itemData(0)['key'],'activity')
        self.assertEqual(c.engagement_select.itemText(0),'Eine leichte Einstiegsfrage')
        self.assertEqual(c.engagement_draft.toPlainText(),'Mein bearbeiteter Entwurf')
        self.assertIs(c.history_table.item(0,0),history_item)
        self.assertEqual(c.store.guild(guild)['activity'][channel],sample)

    def test_unconfirmed_empty_activity_is_not_zero(self):
        from datetime import datetime,timezone
        c=self.w.community;guild='930828728966217728';channel='123456789012345678'
        c.store.record_activity(guild,{'channel_id':channel,'checked_at':datetime.now(timezone.utc).isoformat(),
            'messages':0,'participants':0,'messages_24h':0,'participants_24h':0,'sample_size':0,
            'oldest':None,'latest':None,'coverage':'empty_or_no_history_access'})
        c.offline_server.setCurrentText(guild);c.open_offline()
        self.assertIn('Keine belastbaren',c.activity_metrics.text());self.assertIn('unbestätigte',c.activity_quality.text())
        self.assertNotIn('0 Nachrichten',c.activity_metrics.text())
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

    def test_creator_edit_filter_and_keyboard_selection(self):
        c=self.w.community;guild='930828728966217728';c.offline_server.setCurrentText(guild);c.open_offline()
        c.creator_name.setText('Alpha');c.creator_url.setText('https://www.twitch.tv/alpha');c.add_creator()
        original=c.creator_edit_id;c.creator_url.setText('https://www.twitch.tv/renamed');c.add_creator()
        self.assertEqual(c.creator_edit_id,original);self.assertEqual(len(c.store.guild(guild)['creators']),1)
        c.new_creator();c.creator_name.setText('Beta');c.creator_url.setText('https://www.youtube.com/@beta');c.creator_status.setCurrentText('Angenommen');c.add_creator()
        c.creator_filter.setCurrentText('Bewerbung');self.assertEqual(c.creators.count(),1)
        c.creators.setCurrentRow(0);self.assertEqual(c.creator_edit_id,original);self.assertEqual(c.creator_name.text(),'Alpha')
        c.creator_name.setText('Unsaved draft');c.refresh();self.assertEqual(c.creator_name.text(),'Unsaved draft')
        c.creator_search.setText('no-match');self.assertEqual(c.creators.count(),0);self.assertFalse(c.creator_remove.isEnabled())
        c.offline_server.setCurrentText('123456789012345680');c.open_offline()
        self.assertIsNone(c.creator_edit_id);self.assertEqual(c.creator_name.text(),'');self.assertEqual(c.creator_search.text(),'');self.assertEqual(c.creator_filter.currentIndex(),0)

    def test_creator_removal_confirmation_and_copy_saved_link(self):
        from PySide6.QtWidgets import QMessageBox,QApplication
        c=self.w.community;guild='930828728966217728';c.offline_server.setCurrentText(guild);c.open_offline()
        c.creator_name.setText('Alpha');c.creator_url.setText('https://www.twitch.tv/alpha');c.add_creator()
        c.creator_url.setText('https://www.twitch.tv/unsaved');c.copy_creator_link()
        self.assertEqual(QApplication.clipboard().text(),'https://www.twitch.tv/alpha')
        with patch.object(QMessageBox,'question',return_value=QMessageBox.No):c.remove_creator()
        self.assertEqual(c.creators.count(),1)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):c.remove_creator()
        self.assertEqual(c.creators.count(),0);self.assertIsNone(c.creator_edit_id)

    def test_creator_role_preview_cancel_confirm_and_existing_role(self):
        from creator_roles import binding,save_binding
        from test_creator_roles import FakeRoles,G,U,R
        from lobby import Lobby
        from PySide6.QtWidgets import QMessageBox
        c=self.w.community;fake=FakeRoles();self.w.discord_client=Lobby('test',G,writes=True,db=self.root/'role-audit.db',transport=fake.transport)
        self.w.show_discord({'id':G,'name':'test','channels':[],'roles':fake.roles})
        row=c.store.save_creator(G,'Creator','https://www.twitch.tv/test','Angenommen');save_binding(c.store,G,row['id'],binding(U,R));c.refresh();c.creators.setCurrentRow(0)
        self.assertTrue(c.creator_role_apply.isEnabled())
        def synchronous(action,success,failure):
            try:result=action()
            except Exception as exc:failure(str(exc));return
            success(result)
        with patch.object(self.w,'run_discord_job',side_effect=synchronous),patch.object(QMessageBox,'question',return_value=QMessageBox.No):c.review_creator_role()
        self.assertFalse(any(m=='PUT' for m,p in fake.calls))
        def started_other_job(*args):self.w.discord_worker=object();return QMessageBox.Yes
        with patch.object(self.w,'run_discord_job',side_effect=synchronous),patch.object(QMessageBox,'question',side_effect=started_other_job):c.review_creator_role()
        self.w.discord_worker=None
        self.assertFalse(any(m=='PUT' for m,p in fake.calls));self.assertNotIn('role_delivery',c.chosen_creator())
        with patch.object(self.w,'run_discord_job',side_effect=synchronous),patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):c.review_creator_role()
        self.assertEqual(sum(m=='PUT' for m,p in fake.calls),1);self.assertEqual(c.chosen_creator()['role_delivery']['state'],'confirmed')
        with patch.object(self.w,'run_discord_job',side_effect=synchronous),patch.object(QMessageBox,'question') as confirm:c.review_creator_role();confirm.assert_not_called()
        self.assertEqual(sum(m=='PUT' for m,p in fake.calls),1)
        self.w.disconnect_discord();self.assertFalse(c.creator_role_apply.isEnabled());self.assertTrue(c.creator_link_save.isEnabled())

    def test_failed_role_assignment_is_unclear_and_never_auto_retried(self):
        from creator_roles import binding,save_binding
        from test_creator_roles import FakeRoles,G,U,R
        from lobby import Lobby
        from PySide6.QtWidgets import QMessageBox
        c=self.w.community;fake=FakeRoles();fake.fail=True;self.w.discord_client=Lobby('test',G,writes=True,db=self.root/'role-audit.db',transport=fake.transport)
        self.w.show_discord({'id':G,'name':'test','channels':[],'roles':fake.roles})
        row=c.store.save_creator(G,'Creator','https://www.twitch.tv/test','Angenommen');save_binding(c.store,G,row['id'],binding(U,R));c.refresh();c.creators.setCurrentRow(0)
        def synchronous(action,success,failure):
            try:result=action()
            except Exception as exc:failure(str(exc));return
            success(result)
        with patch.object(self.w,'run_discord_job',side_effect=synchronous),patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):c.review_creator_role()
        self.assertEqual(c.chosen_creator()['role_delivery']['state'],'uncertain');c.dispatch_scheduled_poll();c.refresh()
        self.assertEqual(sum(m=='PUT' for m,p in fake.calls),1)
        c.chosen_creator()['status']='Bewerbung';c.refresh();self.assertFalse(c.creator_role_apply.isEnabled())

    def test_creator_role_storage_failure_prevents_write(self):
        from creator_roles import binding,save_binding
        from test_creator_roles import FakeRoles,G,U,R
        from lobby import Lobby
        from PySide6.QtWidgets import QMessageBox
        c=self.w.community;fake=FakeRoles();self.w.discord_client=Lobby('test',G,writes=True,db=self.root/'role-audit.db',transport=fake.transport)
        self.w.show_discord({'id':G,'name':'test','channels':[],'roles':fake.roles})
        row=c.store.save_creator(G,'Creator','https://www.twitch.tv/test','Angenommen');save_binding(c.store,G,row['id'],binding(U,R));c.refresh();c.creators.setCurrentRow(0)
        def synchronous(action,success,failure):
            try:result=action()
            except Exception as exc:failure(str(exc));return
            success(result)
        with patch.object(self.w,'run_discord_job',side_effect=synchronous),patch.object(QMessageBox,'question',return_value=QMessageBox.Yes),patch.object(QMessageBox,'warning'),patch.object(c.store,'save',side_effect=OSError('full')):c.review_creator_role()
        self.assertFalse(any(m=='PUT' for m,p in fake.calls));self.assertNotIn('role_delivery',c.chosen_creator())

    def test_delete_confirmation_requires_exact_id_and_category_is_only_target(self):
        from test_channel_delete import FakeDelete,G,K
        from lobby import Lobby
        from channel_actions import DeleteConfirmation
        from PySide6.QtWidgets import QDialog
        fake=FakeDelete();self.w.discord_client=Lobby('test',G,writes=True,db=self.root/'delete-audit.db',transport=fake.transport)
        self.w.show_discord({'id':G,'name':'test','channels':fake.channels,'roles':[]});c=self.w.channel_actions;c.action.setCurrentIndex(c.action.findData('delete'));c.channel.setCurrentIndex(c.channel.findData(K));c.reason.setText('Delete category')
        box=DeleteConfirmation(c,'Example',K);self.assertFalse(box.delete_button.isEnabled());box.id_input.setText('wrong');self.assertFalse(box.delete_button.isEnabled());box.id_input.setText(K);self.assertTrue(box.delete_button.isEnabled());box.close()
        def synchronous(action,success,failure):
            try:result=action()
            except Exception as exc:failure(str(exc));return
            success(result)
        with patch.object(self.w,'run_discord_job',side_effect=synchronous),patch.object(DeleteConfirmation,'exec',return_value=QDialog.Accepted):c.review()
        self.assertFalse(any(m=='DELETE' for m,p in fake.calls))
        def confirm(dialog):dialog.id_input.setText(K);return QDialog.Accepted
        with patch.object(self.w,'run_discord_job',side_effect=synchronous),patch.object(DeleteConfirmation,'exec',confirm),patch.object(self.w,'refresh_discord') as refresh:c.review();refresh.assert_called_once()
        self.assertEqual([p for m,p in fake.calls if m=='DELETE'],['/channels/'+K])

    def test_delete_waits_if_other_job_starts_during_confirmation(self):
        from test_channel_delete import FakeDelete,G,K
        from lobby import Lobby
        from channel_actions import DeleteConfirmation
        from PySide6.QtWidgets import QDialog
        fake=FakeDelete();self.w.discord_client=Lobby('test',G,writes=True,db=self.root/'delete-audit.db',transport=fake.transport)
        self.w.show_discord({'id':G,'name':'test','channels':fake.channels,'roles':[]});c=self.w.channel_actions;c.action.setCurrentIndex(c.action.findData('delete'));c.channel.setCurrentIndex(c.channel.findData(K));c.reason.setText('Delete category')
        def synchronous(action,success,failure):
            try:result=action()
            except Exception as exc:failure(str(exc));return
            success(result)
        def occupy(dialog):dialog.id_input.setText(K);self.w.discord_worker=object();return QDialog.Accepted
        with patch.object(self.w,'run_discord_job',side_effect=synchronous),patch.object(DeleteConfirmation,'exec',occupy):c.review()
        self.w.discord_worker=None;self.assertFalse(any(m=='DELETE' for m,p in fake.calls))
