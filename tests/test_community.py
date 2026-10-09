import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from community import CommunityStore,CommunityError,activity_sample,night_fields
from ai_assistant import request_plan
class CommunityTests(unittest.TestCase):
    def test_activity_aggregation_excludes_bots_and_content(self):
        now=datetime.now(timezone.utc)
        sample=activity_sample([{'author_id':'one','timestamp':now.isoformat(),'content':'private'}, {'author_id':'one','timestamp':now.isoformat()}, {'author_id':'bot','bot':True,'timestamp':now.isoformat()}, {'author_id':'bad','timestamp':'bad'}],'42',now)
        self.assertEqual((sample['messages'],sample['participants']),(2,1))
        self.assertNotIn('private',json.dumps(sample));self.assertNotIn('author_id',sample)
    def test_server_isolation_creator_and_reminder_lifecycle(self):
        with tempfile.TemporaryDirectory() as d:
            store=CommunityStore(Path(d));future=datetime.now(timezone.utc)+timedelta(hours=1)
            n=store.add_night('one','Night',future.isoformat(),'Game A\nGame B')
            self.assertEqual(store.due_nights('one',future+timedelta(seconds=1))[0]['id'],n['id'])
            store.mark_reminded('one',n['id']);self.assertEqual(store.due_nights('one',future+timedelta(seconds=1)),[])
            store.save_creator('one','Creator','https://www.twitch.tv/test','Bewerbung')
            store.save_creator('one','Creator','https://www.twitch.tv/test','Angenommen')
            self.assertEqual(len(store.guild('one')['creators']),1)
            self.assertEqual(store.guild('two')['creators'],[])
            self.assertEqual(CommunityStore(Path(d)).guild('one')['creators'][0]['status'],'Angenommen')
            with self.assertRaises(CommunityError):store.save_creator('one','bad','https://evil.example/test','Bewerbung')
    def test_analysis_context_whitelist(self):
        context={'id':'42','name':'test','channels':[],'token':'secret','community':{'activity_samples':[],'planned_lobby_nights':[],'creator_status_counts':{'Bewerbung':1},'token':'secret'}}
        def transport(payload):
            sent=json.loads(payload['input'][0]['content'].split('\n',1)[1])
            self.assertIn('community',sent);self.assertNotIn('secret',json.dumps(sent))
            return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'message':'Analysis','action':'answer','channel':None,'name':None,'kind':None,'parent':None})}]}]}
        self.assertIsNone(request_plan('test','model','Analyze',context,[],transport)['spec'])

class HistoryTests(unittest.TestCase):
    def test_window_boundaries_and_limit(self):
        now=datetime.now(timezone.utc)
        messages=[{'author_id':'one','timestamp':(now-timedelta(hours=24)).isoformat()}, {'author_id':'two','timestamp':(now-timedelta(hours=25)).isoformat()}]
        sample=activity_sample(messages,'42',now)
        self.assertEqual((sample['messages_24h'],sample['participants_24h']),(1,1))
        self.assertFalse(sample['limit_reached'])
        self.assertTrue(activity_sample(messages*50,'42',now)['limit_reached'])
    def test_bounded_history_migration_and_same_bucket(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);store=CommunityStore(root)
            start=datetime(2026,10,1,0,0,tzinfo=timezone.utc)
            for i in range(110):
                sample=activity_sample([],'42',start+timedelta(minutes=15*i));store.record_activity('one',sample)
            self.assertEqual(len(store.history('one','42')),96)
            sample=activity_sample([],'42',start+timedelta(minutes=15*109+1));store.record_activity('one',sample)
            self.assertEqual(len(store.history('one','42')),96)
            self.assertEqual(CommunityStore(root).history('one','42')[-1]['checked_at'],sample['checked_at'])
            store.record_activity('one',activity_sample([],'42',start+timedelta(days=40)))
            self.assertEqual(len(store.history('one','42')),1)
            self.assertEqual(store.history('two','42'),[])
    def test_failed_write_restores_in_memory_history(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            store=CommunityStore(Path(d));store.guild('one')
            before=json.dumps(store.data,sort_keys=True)
            with patch.object(store,'save',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):store.record_activity('one',activity_sample([],'42'))
            self.assertEqual(json.dumps(store.data,sort_keys=True),before)

class LobbyNightDraftTests(unittest.TestCase):
    def test_early_poll_limits_and_duplicate_validation(self):
        future=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        self.assertEqual(night_fields(' Night ',future,' Game A \nGame B')[2],['Game A','Game B'])
        for suggestions in ('Game A\ngame a','A\n'+('B'*56)):
            with self.assertRaises(CommunityError):night_fields('Night',future,suggestions)
    def test_safe_edit_preserves_identity_and_blocks_delivery_states(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            store=CommunityStore(Path(d));future=datetime.now(timezone.utc)+timedelta(days=1)
            row=store.add_night('one','Night',future.isoformat(),'A\nB');row['reminded']=True
            edited=store.update_night('one',row['id'],'Updated',(future+timedelta(hours=1)).isoformat(),'C\nD\nE')
            self.assertEqual(edited['id'],row['id']);self.assertFalse(edited['reminded']);self.assertEqual(edited['options'],['C','D','E'])
            edited['poll_delivery']={'state':'scheduled'}
            with self.assertRaises(CommunityError):store.update_night('one',row['id'],'Blocked',(future+timedelta(hours=2)).isoformat(),'F\nG')
            edited['poll_delivery']={'state':'ready'};before=json.dumps(store.data,sort_keys=True)
            with patch.object(store,'save',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):store.update_night('one',row['id'],'Rollback',(future+timedelta(hours=2)).isoformat(),'F\nG')
            self.assertEqual(json.dumps(store.data,sort_keys=True),before)


class CreatorEditTests(unittest.TestCase):
    def test_edit_by_id_preserves_identity_and_rejects_collisions(self):
        with tempfile.TemporaryDirectory() as d:
            store=CommunityStore(Path(d));first=store.save_creator('one','First','https://www.twitch.tv/first','Bewerbung')
            second=store.save_creator('one','Second','https://www.twitch.tv/second','Angenommen')
            edited=store.save_creator('one','Renamed','https://www.twitch.tv/new','Pausiert',first['id'])
            self.assertEqual(edited['id'],first['id']);self.assertEqual(len(store.guild('one')['creators']),2)
            with self.assertRaises(CommunityError):store.save_creator('one','Collision',second['url'],'Bewerbung',first['id'])
            with self.assertRaises(CommunityError):store.save_creator('two','Wrong server',edited['url'],'Bewerbung',first['id'])
            self.assertEqual(CommunityStore(Path(d)).guild('one')['creators'][0]['url'],edited['url'])
    def test_failed_creator_writes_restore_local_state(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            store=CommunityStore(Path(d));row=store.save_creator('one','First','https://www.twitch.tv/first','Bewerbung');before=json.dumps(store.data,sort_keys=True)
            with patch.object(store,'save',side_effect=OSError('disk full')):
                for action in [lambda:store.save_creator('one','Changed','https://www.twitch.tv/new','Angenommen',row['id']),lambda:store.save_creator('one','New','https://www.twitch.tv/another','Bewerbung'),lambda:store.remove_creator('one',row['id'])]:
                    with self.assertRaises(OSError):action()
                    self.assertEqual(json.dumps(store.data,sort_keys=True),before)
            self.assertEqual(json.dumps(CommunityStore(Path(d)).data,sort_keys=True),before)


class ReminderAndCreatorTests(unittest.TestCase):
    def test_reminder_offset_disable_reload_and_no_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            store=CommunityStore(Path(d));now=datetime.now(timezone.utc);due=now+timedelta(hours=2)
            n=store.add_night('g','Night',due.isoformat(),'A\nB')
            store.set_night_reminder('g',n['id'],60)
            self.assertEqual(store.due_nights('g',due-timedelta(minutes=61)),[])
            self.assertEqual(len(store.due_nights('g',due-timedelta(minutes=60))),1)
            store.mark_reminded('g',n['id']);store.set_night_reminder('g',n['id'],60)
            self.assertEqual(store.due_nights('g',due),[])
            store.set_night_reminder('g',n['id'],None)
            self.assertEqual(CommunityStore(Path(d)).due_nights('g',due),[])
    def test_reminder_validation_and_rollback(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            store=CommunityStore(Path(d));n=store.add_night('g','Night',(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'A\nB')
            for value in (-1,True,'60',16):
                with self.assertRaises(CommunityError):store.set_night_reminder('g',n['id'],value)
            with patch.object(store,'save',side_effect=OSError('disk')),self.assertRaises(OSError):store.set_night_reminder('g',n['id'],30)
            self.assertNotIn('reminder_minutes',n)
    def test_creator_notes_preserve_binding_and_stay_out_of_ai(self):
        from creator_roles import creator_next_step
        with tempfile.TemporaryDirectory() as d:
            store=CommunityStore(Path(d));r=store.save_creator('g','Example','https://twitch.tv/example','Bewerbung',notes='PRIVATE REVIEW')
            row=store.guild('g')['creators'][0];row['discord_link']={'member_id':'1','role_id':'2'};store.save()
            store.save_creator('g','Example','https://twitch.tv/example','Angenommen',r['id'],notes='Changed')
            saved=CommunityStore(Path(d)).guild('g')['creators'][0]
            self.assertEqual(saved['notes'],'Changed');self.assertEqual(saved['discord_link'],row['discord_link'])
            self.assertNotIn('Changed',json.dumps(store.analysis_context('g')))
            self.assertIn('prüfen',creator_next_step(saved))
            with self.assertRaises(CommunityError):store.save_creator('g','Example','https://twitch.tv/example','Angenommen',r['id'],notes='x'*2001)
            self.assertEqual(store.guild('g')['creators'][0]['notes'],'Changed')
