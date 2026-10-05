import copy,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from community import CommunityStore,CommunityError
from polls import poll_spec,PollJournal,send_poll,read_poll_results
from lobby import Lobby
GUILD='930828728966217728';CHANNEL='123456789012345678';MESSAGE='123456789012345679'
class PollTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=CommunityStore(self.root)
        self.n=self.store.add_night(GUILD,'Lobby Night',(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'Game A\nGame B')
        self.spec=poll_spec(GUILD,self.n,CHANNEL,24,True);self.j=PollJournal(self.store)
    def tearDown(self):self.tmp.cleanup()
    def test_payload_and_no_duplicate_attempts(self):
        self.assertEqual(self.spec['payload']['allowed_mentions'],{'parse':[]});self.assertTrue(self.spec['payload']['enforce_nonce'])
        self.assertLessEqual(len(self.spec['payload']['nonce']),25)
        self.j.begin(self.spec)
        with self.assertRaises(CommunityError):self.j.begin(self.spec)
        with self.assertRaises(CommunityError):poll_spec(GUILD,self.n,CHANNEL,24,True)
        self.j.finish(self.spec,{'id':MESSAGE,'channel_id':CHANNEL})
        restored=CommunityStore(self.root).guild(GUILD)['nights'][0]
        self.assertEqual(restored['poll_delivery']['message_id'],MESSAGE)
    def test_uncertain_requires_reset_and_changed_plan_rejected(self):
        self.j.begin(self.spec);self.j.uncertain(self.spec)
        with self.assertRaises(CommunityError):self.j.begin(self.spec)
        self.j.reset_uncertain(GUILD,self.n['id']);self.j.begin(self.spec)
        self.j.reset_uncertain(GUILD,self.n['id']);self.n['options'][0]='Changed'
        with self.assertRaises(CommunityError):self.j.begin(self.spec)
    def test_validation_and_storage_failure_prevents_send(self):
        self.n['options']=['a'*56,'b']
        with self.assertRaises(CommunityError):poll_spec(GUILD,self.n,CHANNEL,24,True)
        self.n['options']=['a','A']
        with self.assertRaises(CommunityError):poll_spec(GUILD,self.n,CHANNEL,24,True)
        self.n['options']=['Game A','Game B']
        with patch.object(self.store,'save',side_effect=OSError('full')):
            with self.assertRaises(OSError):self.j.begin(self.spec)
        self.assertNotIn('poll_delivery',self.n)
    def test_fake_transport_send_and_server_guard(self):
        calls=[]
        def transport(method,path,payload,reason):
            calls.append((method,path,payload))
            if method=='GET':return {'guild_id':GUILD,'type':0}
            return {'id':MESSAGE,'channel_id':CHANNEL}
        client=Lobby('test',GUILD,writes=True,db=self.root/'audit.db',transport=transport)
        result=send_poll(client,self.spec);self.assertEqual(result['id'],MESSAGE)
        self.assertEqual([x[0] for x in calls],['GET','POST']);self.assertIn('poll',calls[-1][2])
        client.guild='123456789012345680'
        with self.assertRaises(CommunityError):send_poll(client,self.spec)
        self.assertEqual(len(calls),2)

    def test_missing_results_are_unknown_not_zero(self):
        def transport(method,path,payload,reason):
            if '/messages/' in path:return {'id':MESSAGE,'channel_id':CHANNEL,'poll':{'answers':[]}}
            return {'guild_id':GUILD,'type':0}
        client=Lobby('test',GUILD,transport=transport)
        text=read_poll_results(client,GUILD,{'state':'sent','channel':CHANNEL,'message_id':MESSAGE})
        self.assertIn('nicht verfügbar',text);self.assertNotIn('0 Stimmen',text)

    def test_scheduled_delivery_persists_and_does_not_repeat(self):
        now=datetime.now(timezone.utc);due=now+timedelta(hours=1)
        self.j.schedule(self.spec,due.isoformat())
        restored=PollJournal(CommunityStore(self.root))
        self.assertEqual(restored.due(GUILD,now),[])
        self.assertEqual(restored.due(GUILD,due+timedelta(seconds=1)),[self.spec])
        restored.begin(self.spec)
        self.assertEqual(restored.due(GUILD,due+timedelta(seconds=1)),[])
        restored.uncertain(self.spec)
        self.assertEqual(restored.due(GUILD,due+timedelta(seconds=1)),[])
    def test_cancelled_expired_and_unscheduled_are_not_due(self):
        now=datetime.now(timezone.utc);due=now+timedelta(hours=1)
        self.j.schedule(self.spec,due.isoformat());self.j.unschedule(GUILD,self.n['id'])
        self.assertEqual(self.j.due(GUILD,due+timedelta(seconds=1)),[])
        self.j.schedule(self.spec,due.isoformat());self.store.cancel_night(GUILD,self.n['id'])
        self.assertEqual(self.j.due(GUILD,due+timedelta(seconds=1)),[])
        self.n['status']='geplant'
        self.assertEqual(self.j.due(GUILD,now+timedelta(days=2)),[])
        with self.assertRaises(CommunityError):self.j.schedule(self.spec,(now+timedelta(days=2)).isoformat())
