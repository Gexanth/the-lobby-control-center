import unittest
from datetime import datetime,timezone,timedelta
from activity_compare import compare_samples

class ComparisonTests(unittest.TestCase):
    def test_distinct_snapshots_and_gaps(self):
        now=datetime.now(timezone.utc)
        p={'checked_at':now.isoformat(),'messages_24h':4,'participants_24h':2,'coverage':'window_reached'}
        self.assertIn('Mindestens zwei',compare_samples('c',[p,p],now))
        earlier=dict(p,checked_at=(now-timedelta(hours=1)).isoformat(),messages_24h=3)
        text=compare_samples('c',[earlier,p],now)
        self.assertIn('4 Nachrichten',text);self.assertIn('3 Nachrichten',text);self.assertIn('nicht',text.replace('weder','nicht'))
        self.assertNotIn('Datenlücke',text)
        earlier['coverage']='capped';self.assertIn('Datenlücke',compare_samples('c',[earlier,p],now))
        earlier['messages_24h']='bad';text=compare_samples('c',[earlier,p],now)
        self.assertIn('Werte nicht verwendbar',text);self.assertNotIn('bad',text)
