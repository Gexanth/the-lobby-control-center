import unittest
from datetime import datetime,timezone,timedelta
from engagement import engagement_ideas,activity_quality,activity_next_step
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
    def test_quality_boundaries_and_invalid_data(self):
        self.assertEqual(activity_quality(self.sample(age=6),self.now),'fresh')
        self.assertEqual(activity_quality(self.sample(age=6.01),self.now),'stale')
        self.assertEqual(activity_quality(self.sample(age=-1),self.now),'future')
        for stamp in (None,'not-a-date',{},999):
            sample=self.sample();sample['checked_at']=stamp
            self.assertEqual(activity_quality(sample,self.now),'invalid')
            self.assertEqual(engagement_ideas(sample,self.now)['kind'],'general')
        for messages,people in ((True,1),(1,True),(-1,0),(1,2)):
            sample=self.sample(people,messages)
            self.assertEqual(activity_quality(sample,self.now),'invalid')
        self.assertEqual(activity_quality(self.sample(0,0,'empty_or_no_history_access'),self.now),'limited')

    def test_old_samples_keep_invalid_and_incomplete_quality(self):
        for coverage in ('capped','empty_or_no_history_access',None):
            self.assertEqual(activity_quality(self.sample(0,0,coverage,age=24),self.now),'limited')
        for messages,people in ((True,1),(1,True),(-1,0),(1,2),('bad',0)):
            sample=self.sample(people,messages,age=24)
            self.assertEqual(activity_quality(sample,self.now),'invalid')
            self.assertIn('nicht verwendbar',engagement_ideas(sample,self.now)['basis'])

    def test_activity_next_step_is_specific_and_non_destructive(self):
        cases=[
            (None,False,True,'connect','Messung fehlt'),
            (None,True,True,'scan','Messung fehlt'),
            (self.sample(age=7),True,True,'scan','aktualisieren'),
            (self.sample(coverage='empty_or_no_history_access'),True,True,'scan','Verlaufzugriff'),
            (self.sample(coverage='capped'),True,True,'impulse','500-Nachrichten-Grenze'),
            (self.sample(),True,True,'impulse','verwendbar'),
            (None,False,False,'connect','Textkanal')]
        for sample,connected,selected,action,title in cases:
            with self.subTest(action=action,title=title):
                result=activity_next_step(sample,connected,selected,self.now)
                self.assertEqual(result['action'],action);self.assertIn(title,result['title'])
                self.assertNotIn('token',repr(result).lower())
        self.assertIsNone(activity_next_step(None,True,False,self.now)['action'])
