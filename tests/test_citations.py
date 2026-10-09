import unittest
from citations import source_index,reference_report


class CitationTests(unittest.TestCase):
    def test_unknown_missing_duplicate_and_limit(self):
        self.assertIn('Keine ACT-',reference_report('Idee',{}))
        report=reference_report('[ACT-madeup] [ACT-madeup]',{})
        self.assertEqual(report.count('Unbekannte Quelle'),1)
        self.assertIn('2 weitere',reference_report(' '.join(f'[ACT-{i}]' for i in range(12)),{}))

    def test_index_is_private_snapshot_with_quality(self):
        point={'source_id':'ACT-test','quality':'stale','checked_at':'time','messages_24h':2,'participants_24h':1,'coverage':'capped','secret':'PRIVATE'}
        context={'community':{'activity_evidence':{'channels':[{'channel_id':'c','latest':point}]}}}
        sources=source_index(context);point['messages_24h']=99
        report=reference_report('[ACT-test]',sources)
        self.assertIn('2 Nachrichten',report);self.assertIn('Veraltet',report)
        self.assertNotIn('PRIVATE',str(sources));self.assertNotIn('99',report)
        sources['ACT-test']['quality']='invalid'
        self.assertIn('nicht verwendbar',reference_report('[ACT-test]',sources))
        self.assertNotIn('2 Nachrichten',reference_report('[ACT-test]',sources))
