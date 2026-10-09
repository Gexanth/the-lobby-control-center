import copy
import unittest
from datetime import datetime, timezone, timedelta
from attention import attention_items


class AttentionTests(unittest.TestCase):
    def test_priority_deadlines_quality_and_no_mutation(self):
        now=datetime(2026,10,9,16,tzinfo=timezone.utc)
        data={'nights':[
            {'status':'geplant','when':(now+timedelta(hours=1)).isoformat(),'poll_delivery':{'state':'scheduled','send_at':now.isoformat()}},
            {'poll_delivery':{'state':'uncertain'}},
            {'status':'geplant','when':now.isoformat(),'poll_delivery':{'state':'scheduled','send_at':now.isoformat()}}],
            'activity':{'old':{'checked_at':(now-timedelta(hours=7)).isoformat()}},
            'creators':[{'status':'Bewerbung'}]}
        original=copy.deepcopy(data)
        rows=attention_items(data,{'unclear':1,'errors':1,'active':2},False,now)
        self.assertEqual([r['key'] for r in rows],['poll_unclear','stream_unclear','poll_due','poll_stopped','stream_errors','stream_stopped','activity','applications'])
        self.assertEqual([r['tab'] for r in rows],[1,2,1,1,2,2,0,2])
        self.assertEqual(data,original)
    def test_empty_and_missing_journal_are_distinct(self):
        self.assertEqual(attention_items({},{}),[])
        self.assertEqual(attention_items({},None)[0]['key'],'stream_journal')
    def test_fresh_data_running_monitor_and_closed_application_no_hint(self):
        now=datetime.now(timezone.utc)
        data={'activity':{'one':{'checked_at':now.isoformat(),'messages_24h':3,'participants_24h':2,'coverage':'window_reached'}},'creators':[{'status':'Angenommen'}]}
        self.assertEqual(attention_items(data,{'active':1},True,now),[])
