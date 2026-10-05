import unittest
from datetime import datetime,timezone,timedelta
from engagement import engagement_ideas
class EngagementTests(unittest.TestCase):
    def sample(self,people=2,messages=7,coverage='window_reached',age=0):
        return {'checked_at':(self.now-timedelta(hours=age)).isoformat(),'messages_24h':messages,'participants_24h':people,'coverage':coverage}
    def setUp(self):self.now=datetime.now(timezone.utc)
    def test_confirmed_data_drives_explainable_ideas(self):
        for people,messages,expected in [(0,0,'restart'),(3,9,'invite'),(4,9,'continue')]:
            result=engagement_ideas(self.sample(people,messages),self.now)
            self.assertEqual(result['kind'],expected);self.assertIn(str(messages),result['basis'])
            self.assertEqual(len(result['ideas']),3)
    def test_incomplete_empty_stale_and_legacy_never_infer_inactivity(self):
        for sample in [None,self.sample(0,0,'empty_or_no_history_access'),self.sample(0,0,'capped'),self.sample(0,0,age=7),{'checked_at':self.now.isoformat(),'messages':0},self.sample(9,1)]:
            result=engagement_ideas(sample,self.now)
            self.assertEqual(result['kind'],'general');self.assertNotIn('keine menschlichen',result['ideas'][0]['why'])
    def test_no_identifiers_or_tokens_in_drafts(self):
        sample=self.sample();sample['token']='private-token';sample['author_id']='secret-person'
        result=repr(engagement_ideas(sample,self.now))
        self.assertNotIn('private-token',result);self.assertNotIn('secret-person',result)
