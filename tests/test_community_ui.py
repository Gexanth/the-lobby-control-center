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
    def test_analysis_preview_offline_refresh_and_server_isolation(self):
        from datetime import datetime,timezone
        c=self.w.community
        self.assertIn('Server-ID wählen',c.analysis_preview.toPlainText())
        c.offline_server.setCurrentText('930828728966217728');c.open_offline()
        self.assertIn('Keine Aktivitätsmessungen',c.analysis_preview.toPlainText())
        c.store.guild(c.guild_id)['activity']['example-channel']={'checked_at':datetime.now(timezone.utc).isoformat(),'messages_24h':7,'participants_24h':2,'coverage':'window_reached'}
        c.tabs.setCurrentIndex(3)
        self.assertIn('7 Nachrichten / 2 Beteiligte',c.analysis_preview.toPlainText())
        self.assertIn('[ACT-',c.analysis_preview.toPlainText())
        self.assertTrue(c.analysis_preview.isReadOnly())
        c.offline_server.setCurrentText('930828728966217729');c.open_offline()
        self.assertNotIn('example-channel',c.analysis_preview.toPlainText())
        self.assertIn('Keine Aktivitätsmessungen',c.analysis_preview.toPlainText())
    def test_analysis_actions_visible_above_preview(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QPushButton
        c=self.w.community;c.tabs.setCurrentIndex(3);self.w.stack.setCurrentIndex(7)
        self.w.resize(1280,900);self.app.processEvents()
        buttons=c.tabs.widget(3).findChildren(QPushButton)
        self.assertEqual(len(buttons),2)
        for button in buttons:
            self.assertLess(button.mapTo(self.w,QPoint(0,button.height())).y(),self.w.height()-30)
            self.assertLess(button.y(),c.analysis_preview.y())
        self.assertLessEqual(c.analysis_preview.height(),420)

    def test_ai_provider_switch_isolates_keys_history_and_pending_plan(self):
        w=self.w
        self.assertEqual(w.active_ai_provider,'anthropic')
        w.api_key_input.setText('claude-test-key');w.ai_model.setText('claude-custom')
        w.ai_history=[{'role':'user','content':'private conversation'}];w.pending_ai={'spec':{}}
        w.ai_provider.setCurrentIndex(1)
        self.assertEqual(w.ai_keys['anthropic'],'claude-test-key')
        self.assertEqual(w.api_key_input.text(),'')
        self.assertEqual(w.ai_history,[]);self.assertIsNone(w.pending_ai)
        self.assertFalse(w.ai_apply.isEnabled())
        w.api_key_input.setText('openai-test-key');w.ai_provider.setCurrentIndex(0)
        self.assertEqual(w.ai_keys['openai'],'openai-test-key')
        self.assertEqual(w.ai_model.text(),'claude-custom')
        w.forget_ai_key()
        self.assertEqual(w.ai_keys['anthropic'],'')
        self.assertEqual(w.ai_keys['openai'],'openai-test-key')

    def test_ai_dispatch_uses_selected_provider(self):
        w=self.w;w.api_key_input.setText('claude-test-key');w.ai_input.setText('Hallo')
        with patch('main.request_plan',return_value={'message':'Hallo','spec':None,'guild':None}) as request:
            with patch.object(w,'run_discord_job',side_effect=lambda work,done,failed:done(work())):
                w.ask_ai()
        self.assertEqual(request.call_args.kwargs['provider'],'anthropic')
        self.assertEqual(w.api_key_input.text(),'')
        self.assertEqual(w.ai_keys['anthropic'],'claude-test-key')

    def test_adaptive_tabs_night_steps_and_review_evidence(self):
        from PySide6.QtWidgets import QSizePolicy
        from task_review import TaskReview
        c=self.w.community;c.tabs.setCurrentIndex(1)
        self.assertEqual(c.tabs.widget(2).sizePolicy().verticalPolicy(),QSizePolicy.Ignored)
        self.assertEqual(c.tabs.widget(1).sizePolicy().verticalPolicy(),QSizePolicy.Preferred)
        c.tabs.setCurrentIndex(2);tall=c.tabs.sizeHint().height();c.tabs.setCurrentIndex(3)
        self.assertLess(c.tabs.sizeHint().height(),tall);c.tabs.setCurrentIndex(1)
        self.assertEqual(c.night_steps.count(),2)
        c.offline_server.setCurrentText('930828728966217728');c.open_offline()
        c.night_title.setText('Testplan');c.options.setPlainText('Spiel A\nSpiel B');c.save_night()
        c.night_steps.setCurrentIndex(1);self.assertIn('Testplan',c.night_delivery_selection.text())
        self.assertIn('verbinden',c.poll_readiness.text())
        c.night_steps.setCurrentIndex(0);self.assertEqual(c.night_title.text(),'Testplan')
        d=TaskReview(self.w,'Idee');d.set_evidence('Bekannte Quelle');self.assertTrue(d.evidence.isReadOnly())
        self.assertIn('Bekannte Quelle',d.evidence.toPlainText());self.assertEqual(d.notes.toPlainText(),'Idee');d.close()

    def test_open_last_ai_task_with_filter_and_deleted_task(self):
        from PySide6.QtGui import QTextCursor
        w=self.w;w.chat.setPlainText('Idee');cursor=w.chat.textCursor();cursor.select(QTextCursor.Document);w.chat.setTextCursor(cursor)
        with patch('main.TaskReview.exec',return_value=1):w.save_ai_selection()
        task_id=w.last_ai_task_id;self.assertTrue(w.ai_open_task.isEnabled())
        w.filter.setCurrentText('Erledigt');w.open_last_ai_task()
        self.assertEqual(w.selected_id(),task_id);self.assertEqual(w.stack.currentIndex(),3)
        w.store.delete(task_id);w.open_last_ai_task();self.assertFalse(w.ai_open_task.isEnabled())

    def test_answer_sources_and_task_provenance_use_original_snapshot(self):
        from datetime import datetime,timezone
        from PySide6.QtGui import QTextCursor
        from evidence import activity_evidence
        w=self.w;guild='930828728966217728'
        w.server_context={'id':guild,'channels':[]}
        sample={'checked_at':datetime.now(timezone.utc).isoformat(),'messages_24h':7,'participants_24h':2,'coverage':'window_reached'}
        w.community.store.guild(guild)['activity']['c']=sample
        key=activity_evidence({'activity':{'c':sample}})['channels'][0]['latest']['source_id']
        answer='🎮 Gemeinsam spielen ['+key+'] [ACT-invented]'
        w.api_key_input.setText('test-key');w.ai_input.setText('Analyse')
        with patch('main.request_plan',return_value={'message':answer,'spec':None,'guild':guild}),patch.object(w,'run_discord_job',side_effect=lambda work,done,failed:done(work())):
            w.ask_ai(analysis_only=True)
        self.assertIn('Unbekannte Quelle',w.chat.toPlainText())
        record=w.ai_source_records[0]
        sample['messages_24h']=999
        cursor=w.chat.textCursor();cursor.setPosition(record['start']);cursor.setPosition(record['end'],QTextCursor.KeepAnchor);w.chat.setTextCursor(cursor)
        with patch('main.TaskReview.exec',return_value=1):w.save_ai_selection()
        notes=w.store.items[-1]['notes'];self.assertIn('7 Nachrichten',notes);self.assertNotIn('999',notes)
        self.assertIn(guild,notes);self.assertIn('Herkunft: KI-Vorschlag',notes)
        self.assertTrue(notes.startswith(answer))
        # Appending must not replace selected old answers (also preserves ranges).
        before=w.chat.toPlainText();w.append_chat('Weitere Antwort')
        self.assertEqual(w.chat.toPlainText(),before+'Weitere Antwort')
        w.clear_ai_chat();self.assertEqual(w.ai_source_records,[])

    def test_night_reminder_and_creator_notes_ui(self):
        from datetime import datetime,timedelta
        c=self.w.community;c.offline_server.setCurrentText('930828728966217728');c.open_offline()
        c.night_title.setText('Test Night');c.night_time.setText((datetime.now()+timedelta(days=2)).isoformat());c.options.setPlainText('A\nB');c.save_night()
        self.assertIn('verbinden',c.poll_readiness.text())
        c.night_reminder.setCurrentIndex(c.night_reminder.findData(30));c.save_night_reminder()
        self.assertEqual(c.chosen_night()['reminder_minutes'],30)
        c.creator_name.setText('Example');c.creator_url.setText('https://twitch.tv/example');c.creator_notes.setPlainText('Rückfrage zum Kanal');c.add_creator()
        c.creators.setCurrentRow(0);c.select_creator(c.creators.currentItem())
        self.assertEqual(c.creator_notes.toPlainText(),'Rückfrage zum Kanal')
        self.assertIn('Bewerbung prüfen',c.creator_next.text())
        c.new_creator();self.assertEqual(c.creator_notes.toPlainText(),'')

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
    def test_activity_permission_failure_is_actionable_and_stops_auto_retry(self):
        from lobby import Lobby,DiscordError,discord_http_error_message
        c=self.w.community;guild='930828728966217728';channel='123456789012345678';calls=[]
        def transport(method,path,payload,reason):
            calls.append(path)
            if '?' not in path:return {'id':channel,'guild_id':guild,'type':0}
            raise DiscordError(discord_http_error_message(403,method,path))
        self.w.discord_client=Lobby('test',guild,transport=transport)
        self.w.show_discord({'id':guild,'name':'test','channels':[{'id':channel,'name':'chat','type':0}],'roles':[]})
        c.auto_sample.setChecked(True)
        def synchronous(action,success,failure):
            try:result=action()
            except Exception as exc:failure(str(exc));return
            success(result)
        with patch.object(self.w,'run_discord_job',side_effect=synchronous):c.sample()
        self.assertFalse(c.auto_sample.isChecked());self.assertIn('Kanal ansehen',c.activity_access.text())
        self.assertIn('Nachrichtenverlauf anzeigen',c.activity_access.text());self.assertIn('nicht erforderlich',c.activity_access.text())
        self.assertIn('nicht erfasst',c.status.text());self.assertNotIn(channel,c.store.guild(guild)['activity'])
        self.assertEqual(len(calls),2)

    def test_successful_activity_capture_confirms_access(self):
        from lobby import Lobby
        c=self.w.community;guild='930828728966217728';channel='123456789012345678'
        def transport(method,path,payload,reason):
            if '?' not in path:return {'id':channel,'guild_id':guild,'type':0}
            return []
        self.w.discord_client=Lobby('test',guild,transport=transport)
        self.w.show_discord({'id':guild,'name':'test','channels':[{'id':channel,'name':'chat','type':0}],'roles':[]})
        def synchronous(action,success,failure):
            try:result=action()
            except Exception as exc:failure(str(exc));return
            success(result)
        with patch.object(self.w,'run_discord_job',side_effect=synchronous):c.sample()
        self.assertIn('Zugriff bei der letzten Erfassung bestätigt',c.activity_access.text())
        self.assertIn(channel,c.store.guild(guild)['activity'])
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

    def test_lobby_night_readiness_edit_and_locked_delivery(self):
        from datetime import datetime,timedelta
        c=self.w.community;guild='930828728966217728'
        c.offline_server.setCurrentText(guild);c.open_offline()
        c.night_title.setText('Community Night');c.night_time.setText((datetime.now()+timedelta(days=2)).strftime('%Y-%m-%d 20:00'));c.options.setPlainText('Minecraft\nminecraft')
        self.assertIn('Doppelte',c.night_readiness.text())
        c.options.setPlainText('Minecraft\nParty Animals\nValorant');self.assertIn('3 eindeutige Vorschläge',c.night_readiness.text())
        c.save_night();self.assertEqual(c.nights.count(),1);saved=c.chosen_night();saved_id=saved['id']
        self.assertIn('Dies ist kein Discord-Event',c.night_review.text());self.assertEqual(c.night_save.text(),'Änderungen am Entwurf speichern')
        c.options.setPlainText('Minecraft\nParty Animals');c.save_night()
        self.assertEqual(len(c.store.guild(guild)['nights']),1);self.assertEqual(c.chosen_night()['id'],saved_id);self.assertEqual(c.chosen_night()['options'],['Minecraft','Party Animals'])
        c.chosen_night()['poll_delivery']={'state':'sent','channel':'123456789012345678','message_id':'123456789012345679'}
        c.select_night();self.assertFalse(c.night_save.isEnabled());self.assertFalse(c.options.isEnabled())
        c.new_night();self.assertTrue(c.options.isEnabled());self.assertEqual(c.options.toPlainText(),'');self.assertIn('Neuer lokaler Entwurf',c.night_review.text())

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

    def test_dashboard_stream_health_uses_local_records_and_session_state(self):
        from streams import StreamJournal,save_config,set_enabled
        c=self.w.community;guild='930828728966217728';channel='123456789012345678'
        c.offline_server.setCurrentText(guild);c.open_offline()
        row=c.store.save_creator(guild,'Alpha','https://twitch.tv/alpha','Angenommen')
        cfg={'provider':'twitch','source_id':'1234','name':'Alpha','url':'https://twitch.tv/alpha'}
        save_config(c.store,guild,row['id'],cfg,channel,row['url']);set_enabled(c.store,guild,row['id'],True)
        journal=StreamJournal(c.store.path.parent);saved=c.store.guild(guild)['creators'][0]['stream_config']
        journal.start_check(guild,saved,now=1);journal.record(guild,saved,'Kein öffentlicher Live-Stream erkannt')
        c.dashboard();self.assertIn('1 eingerichtet · 1 aktiv',self.w.dashboard_page.stream_health.text())
        self.assertIn('1 fällig',self.w.dashboard_page.stream_health.text());self.assertIn('gestoppt',self.w.dashboard_page.stream_health.text())
        with patch('streams.urlopen',side_effect=AssertionError('dashboard must stay local')):c.dashboard()
        c.stream_panel.running.setChecked(True);self.assertIn('läuft in dieser App-Sitzung',self.w.dashboard_page.stream_health.text())
        c.stream_panel.running.setChecked(False)

    def test_attention_navigation_refresh_and_offline_clear(self):
        from PySide6.QtWidgets import QPushButton,QLabel
        c=self.w.community;g='930828728966217728';c.offline_server.setCurrentText(g);c.open_offline()
        c.store.save_creator(g,'<b>Private creator</b>','https://twitch.tv/example','Bewerbung');c.dashboard()
        d=self.w.dashboard_page
        row=d.attention_body.itemAt(2).widget();self.assertIn('1 offene Creator-Bewerbungen',row.findChild(QLabel).text())
        self.assertNotIn('Private creator',row.findChild(QLabel).text())
        c.dashboard();self.assertIs(d.attention_body.itemAt(2).widget(),row)
        row.findChild(QPushButton).click();self.assertEqual(self.w.stack.currentIndex(),7);self.assertEqual(c.tabs.currentIndex(),2)
        d.refresh_streams(None,c.store);self.assertEqual(d.attention_body.count(),2);self.assertIn('Wähle',d.attention_empty.text())
        self.app.processEvents();d.refresh_attention([]);self.assertIn('Keine offenen Hinweise',d.attention_empty.text())

    def test_dashboard_history_is_bounded_and_selection_becomes_task(self):
        from datetime import datetime,timezone
        from PySide6.QtGui import QTextCursor
        c=self.w.community;g='930828728966217728';c.offline_server.setCurrentText(g);c.open_offline()
        p={'checked_at':datetime.now(timezone.utc).isoformat(),'messages_24h':7,'participants_24h':3,'sample_size':7,'coverage':'history_end'}
        c.store.guild(g)['activity']={'123456789012345678':p};c.store.guild(g)['activity_history']={'123456789012345678':[p]*15};c.dashboard()
        d=self.w.dashboard_page;self.assertEqual(d.history_table.rowCount(),12);self.assertIn('nicht summieren',d.history_note.text())
        self.assertEqual(d.history_table.item(0,1).text(),'7')
        c.dashboard();self.assertEqual(d.history_channel.count(),1)
        self.w.chat.setPlainText('Eine gemeinsame Runde vorschlagen');cursor=self.w.chat.textCursor();cursor.select(QTextCursor.Document);self.w.chat.setTextCursor(cursor)
        with patch('main.TaskReview.exec',return_value=1):self.w.ai_save_selection.click()
        self.assertEqual(self.w.store.items[-1]['text'],'Eine gemeinsame Runde vorschlagen')
        self.assertIn('Noch nicht ausgeführt',self.w.ai_status.text())
        d.refresh_streams(None,c.store);self.assertEqual(d.history_table.rowCount(),0)

    def test_task_review_cancel_edit_duplicate_and_busy_guard(self):
        from PySide6.QtGui import QTextCursor
        from task_review import TaskReview
        from PySide6.QtWidgets import QDialogButtonBox
        w=self.w;w.chat.setPlainText('Idee\nBegründung');cursor=w.chat.textCursor();cursor.select(QTextCursor.Document);w.chat.setTextCursor(cursor)
        with patch('main.TaskReview.exec',return_value=0):w.save_ai_selection()
        self.assertEqual(w.store.items,[])
        def edited(d):d.title.setText('Konkrete Aufgabe');d.notes.setPlainText('Erster Schritt');d.status.setCurrentText('In Arbeit');return 1
        with patch('main.TaskReview.exec',edited):w.save_ai_selection();w.save_ai_selection()
        self.assertEqual(len(w.store.items),1);self.assertEqual(w.store.items[0]['notes'],'Erster Schritt');self.assertEqual(w.store.items[0]['status'],'In Arbeit')
        self.assertIn('bereits',w.ai_status.text())
        def busy(d):w.discord_worker=object();return 1
        with patch('main.TaskReview.exec',busy):w.save_ai_selection()
        w.discord_worker=None;self.assertEqual(len(w.store.items),1)
        d=TaskReview(w,'Idee');d.title.clear();self.assertFalse(d.buttons.button(QDialogButtonBox.Save).isEnabled())
        d.title.setText('Auftrag');d.notes.setPlainText('x'*8001);self.assertFalse(d.validate());d.close()

    def test_task_review_preserves_edits_after_save_failure(self):
        from PySide6.QtGui import QTextCursor
        w=self.w;w.chat.setPlainText('Vorschlag');cursor=w.chat.textCursor();cursor.select(QTextCursor.Document);w.chat.setTextCursor(cursor)
        dialogs=[]
        def review(d):
            dialogs.append(d)
            if len(dialogs)==1:d.title.setText('Bearbeitet');d.notes.setPlainText('Mein nächster Schritt');return 1
            self.assertIs(d,dialogs[0]);self.assertEqual(d.title.text(),'Bearbeitet');self.assertEqual(d.notes.toPlainText(),'Mein nächster Schritt');return 0
        with patch('main.TaskReview.exec',review),patch.object(w,'mutate',return_value=False):w.save_ai_selection()
        self.assertEqual(w.store.items,[]);self.assertEqual(len(dialogs),2)

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

    def stream_fixture(self):
        from lobby import Lobby
        from streams import save_config
        G='930828728966217728';C='1515362180281663610'
        source={'provider':'twitch','source_id':'1234','name':'Example','url':'https://twitch.tv/example'}
        calls=[]
        def transport(method,path,payload,reason):
            calls.append((method,path,payload))
            if method=='GET':return {'id':C,'guild_id':G,'type':0}
            return {'id':'123456789012345678','channel_id':C}
        client=Lobby('test',G,writes=True,db=self.root/'audit.db',transport=transport)
        self.w.discord_client=client
        self.w.show_discord({'id':G,'name':'Test','channels':[{'id':C,'name':'streams','type':0}],'roles':[]})
        c=self.w.community;row=c.store.save_creator(G,'Example',source['url'],'Angenommen')
        c.refresh_creators();c.creators.setCurrentRow(0)
        return c,c.stream_panel,G,C,source,row,calls

    @staticmethod
    def stream_sync(work,done,failed):
        try:result=work()
        except Exception as exc:failed(str(exc));return
        done(result)

    def test_stream_source_verification_and_dry_run_never_post(self):
        c,p,g,ch,source,row,calls=self.stream_fixture()
        p.client_id.setText('test-client');p.token.setText('secret-test')
        with patch('stream_ui.StreamAPI.resolve',return_value=source),patch.object(self.w,'run_discord_job',side_effect=self.stream_sync):
            p.resolve_source()
        self.assertFalse(c.chosen_creator()['stream_config']['enabled']);self.assertFalse(p.running.isChecked())
        self.assertNotIn('secret-test',c.store.path.read_text())
        live=[{'id':'98765','url':source['url'],'title':'Live'}]
        with patch('stream_ui.StreamAPI.live',return_value=live),patch.object(self.w,'run_discord_job',side_effect=self.stream_sync):p.check_only()
        self.assertIn('Probelauf',p.status.text());self.assertFalse(any(x[0]=='POST' for x in calls))
        p.forget_keys();self.assertEqual(p.token.text(),'');self.assertEqual(p.client_id.text(),'')

    def test_stream_activation_requires_conflict_check_and_confirmation(self):
        from streams import save_config
        from PySide6.QtWidgets import QMessageBox
        c,p,g,ch,source,row,calls=self.stream_fixture()
        save_config(c.store,g,row['id'],source,ch,row['url']);p.refresh()
        p.enable_source();self.assertFalse(c.chosen_creator()['stream_config']['enabled'])
        p.conflict.setChecked(True)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.No):p.enable_source()
        self.assertFalse(c.chosen_creator()['stream_config']['enabled'])
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):p.enable_source()
        self.assertTrue(c.chosen_creator()['stream_config']['enabled']);self.assertFalse(p.running.isChecked())
        p.pause_source();self.assertFalse(c.chosen_creator()['stream_config']['enabled'])
        self.assertFalse(any(x[0]=='POST' for x in calls))

    def test_stream_automatic_dispatch_and_pause_during_detection(self):
        from streams import save_config,set_enabled
        c,p,g,ch,source,row,calls=self.stream_fixture()
        save_config(c.store,g,row['id'],source,ch,row['url']);set_enabled(c.store,g,row['id'],True);p.refresh()
        p.client_id.setText('client');p.token.setText('token');live=[{'id':'98765','url':source['url'],'title':'Live'}]
        with patch('stream_ui.StreamAPI.live',return_value=live),patch.object(self.w,'run_discord_job',side_effect=self.stream_sync):
            p.tick();self.assertFalse(any(x[0]=='POST' for x in calls))
            p.running.setChecked(True);p.tick()
        self.assertEqual(sum(x[0]=='POST' for x in calls),1)
        with p.journal().db() as db:db.execute('DELETE FROM checks')
        def stop_during_detection(cfg):p.running.setChecked(False);return [dict(live[0],id='different')]
        with patch('stream_ui.StreamAPI.live',side_effect=stop_during_detection),patch.object(self.w,'run_discord_job',side_effect=self.stream_sync):p.tick()
        self.assertEqual(sum(x[0]=='POST' for x in calls),1)
        self.assertFalse(p.running.isChecked())

    def test_stream_polling_prioritizes_never_checked_over_due_first_row(self):
        from streams import save_config,set_enabled
        c,p,g,ch,source,row,calls=self.stream_fixture()
        save_config(c.store,g,row['id'],source,ch,row['url']);set_enabled(c.store,g,row['id'],True)
        older=c.store.guild(g)['creators'][0]['stream_config']
        p.journal().start_check(g,older,now=1)  # already due, but previously checked
        new=c.store.save_creator(g,'Second','https://twitch.tv/second','Angenommen')
        second=dict(source,source_id='5678',name='Second',url=new['url'])
        save_config(c.store,g,new['id'],second,ch,new['url']);set_enabled(c.store,g,new['id'],True)
        p.running.setChecked(True)
        with patch.object(p,'check_source') as check:p.tick()
        self.assertEqual(check.call_args.args[0]['id'],new['id'])

