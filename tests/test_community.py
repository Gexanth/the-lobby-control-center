import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from community import CommunityStore,CommunityError,activity_sample
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
