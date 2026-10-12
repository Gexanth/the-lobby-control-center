import tempfile
import unittest
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
from community import CommunityStore, CommunityError, utcnow
from matchmaking import create_listing, join_listing, leave_listing, close_listing, active_listings

class MatchmakingTests(unittest.TestCase):
    def test_lifecycle_and_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            store=CommunityStore(Path(d))
            due=(utcnow()+timedelta(hours=2)).isoformat()
            row=create_listing(store,"123","10","Valorant","Ranked","Gold",2,due)
            self.assertEqual(len(active_listings(CommunityStore(Path(d)),"123")),1)
            join_listing(store,"123",row["id"],"11")
            full=join_listing(store,"123",row["id"],"12")
            self.assertEqual(full["status"],"full")
            with self.assertRaises(CommunityError):
                join_listing(store,"123",row["id"],"13")
            self.assertEqual(leave_listing(store,"123",row["id"],"11")["status"],"open")
            with self.assertRaises(CommunityError):
                close_listing(store,"123",row["id"],"13")
            close_listing(store,"123",row["id"],"10")
            self.assertEqual(active_listings(store,"123"),[])

    def test_invalid_and_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            store=CommunityStore(Path(d))
            due=(utcnow()+timedelta(hours=2)).isoformat()
            with self.assertRaises(CommunityError):
                create_listing(store,"123","abc","Valorant","Ranked","",2,due)
            with patch.object(store,"save",side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    create_listing(store,"123","10","Valorant","Ranked","",2,due)
            self.assertEqual(active_listings(store,"123"),[])
if __name__=="__main__":
    unittest.main()
