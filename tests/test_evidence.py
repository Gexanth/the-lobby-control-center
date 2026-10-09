import copy,unittest
from datetime import datetime,timezone,timedelta
from evidence import activity_evidence,evidence_preview
from ai_assistant import request_plan,AIError

class EvidenceTests(unittest.TestCase):
    def test_latest_without_history_and_stable_source(self):
        now=datetime.now(timezone.utc)
        p={'checked_at':now.isoformat(),'messages_24h':5,'participants_24h':2,'coverage':'window_reached'}
        data={'activity':{'c':p}}
        first=activity_evidence(data,now);later=activity_evidence(data,now+timedelta(hours=7))
        point=first['channels'][0]['latest']
        self.assertEqual(point['source_id'],later['channels'][0]['latest']['source_id'])
        self.assertEqual(later['channels'][0]['quality'],'stale')
        self.assertIn(point['source_id'],evidence_preview(first))
        self.assertIn('5 Nachrichten / 2 Beteiligte',evidence_preview(first))
        p['messages_24h']=6
        self.assertNotEqual(point['source_id'],activity_evidence(data,now)['channels'][0]['latest']['source_id'])

    def test_latest_invalid_and_future_withheld(self):
        now=datetime.now(timezone.utc)
        for stamp,count,quality in ((now-timedelta(days=1),'bad','invalid'),(now+timedelta(hours=1),4,'future')):
            e=activity_evidence({'activity':{'c':{'checked_at':stamp.isoformat(),'messages_24h':count,'participants_24h':1}}},now)
            self.assertEqual(e['channels'][0]['quality'],quality)
            self.assertIsNone(e['channels'][0]['latest']['messages_24h'])
            self.assertIn('Messwerte ausgeblendet',evidence_preview(e))
        self.assertIn('Keine Aktivitätsmessungen',evidence_preview(activity_evidence({},now)))
        e=activity_evidence({'activity':{'c':{'checked_at':'bad'}}},now)
        self.assertIn('Zeitpunkt unbekannt',evidence_preview(e))

    def test_bounded_private_history_and_invalid_values(self):
        now=datetime.now(timezone.utc)
        p={'checked_at':now.isoformat(),'messages_24h':5,'participants_24h':2,'coverage':'window_reached','token':'SECRET','content':'PRIVATE'}
        points=[dict(p) for _ in range(20)];points[-1]=dict(p,checked_at=(now-timedelta(days=1)).isoformat(),messages_24h='bad')
        data={'activity':{'channel':p},'activity_history':{'channel':points}}
        before=copy.deepcopy(data);e=activity_evidence(data,now);row=e['channels'][0]
        self.assertEqual(len(row['recent_points']),12);self.assertEqual(row['history_points'],20)
        self.assertEqual(row['recent_points'][-1]['quality'],'invalid');self.assertIsNone(row['recent_points'][-1]['messages_24h'])
        self.assertNotIn('SECRET',str(e));self.assertNotIn('PRIVATE',str(e));self.assertEqual(data,before)
    def test_analysis_action_rejected_for_both_providers(self):
        import json
        value={'message':'Plan','action':'rename','channel':'c','name':'new','kind':None,'parent':None}
        context={'id':'g','channels':[{'id':'c','type':0}]}
        responses={'anthropic':{'stop_reason':'tool_use','content':[{'type':'tool_use','name':'lobby_plan','input':value}]},'openai':{'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(value)}]}]}}
        for provider,response in responses.items():
            with self.subTest(provider=provider),self.assertRaisesRegex(AIError,'Serveranalyse'):
                request_plan('key','model','Analyse',context,[],lambda _:response,provider,analysis_only=True)

    def test_ai_evidence_whitelist_and_bounds(self):
        import json
        answer={'message':'Daten fehlen','action':'answer','channel':None,'name':None,'kind':None,'parent':None}
        row={'channel_id':'c','quality':'limited','checked_at':'today','history_points':99,'secret':'PRIVATE','latest':{'source_id':'ACT-test','messages_24h':None,'secret':'PRIVATE'},'recent_points':[{'source_id':'ACT-history','checked_at':'today','quality':'limited','messages_24h':1,'participants_24h':1,'coverage':'capped','content':'PRIVATE'}]*20}
        context={'id':'g','channels':[],'community':{'activity_samples':[{'messages_24h':'RAW-INVALID'}],'activity_evidence':{'channels':[row]*60,'token':'PRIVATE'}}}
        def transport(payload):
            text=payload['messages'][0]['content'];self.assertNotIn('PRIVATE',text)
            data=json.loads(text.split('\n',1)[1]);e=data['community']['activity_evidence']
            self.assertEqual(len(e['channels']),50);self.assertEqual(len(e['channels'][0]['recent_points']),12)
            self.assertNotIn('RAW-INVALID',text);self.assertNotIn('activity_samples',data['community'])
            self.assertEqual(e['channels'][0]['latest']['source_id'],'ACT-test')
            self.assertEqual(e['channels'][0]['recent_points'][0]['source_id'],'ACT-history')
            return {'stop_reason':'tool_use','content':[{'type':'tool_use','name':'lobby_plan','input':answer}]}
        request_plan('key','model','Analyse',context,[],transport,'anthropic',True)
