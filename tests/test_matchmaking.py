import copy
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from community import CommunityStore, CommunityError, utcnow
from matchmaking import create_listing, join_listing, leave_listing, close_listing, active_listings

class MatchmakingTests(unittest.TestCase):
    def test_expired_listings_release_quota_without_deleting_history(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);store=CommunityStore(root)
            now=datetime(2026,10,13,12,tzinfo=timezone.utc)
            due=now+timedelta(hours=1)
            for _ in range(3):
                create_listing(store,"123","10","Valorant","Ranked","",2,due.isoformat(),now)
            before=copy.deepcopy(store.data)
            # The start instant is still active, consistently with active_listings/join.
            self.assertEqual(len(active_listings(store,"123",due)),3)
            with self.assertRaises(CommunityError):
                create_listing(store,"123","10","New","Ranked","",2,(due+timedelta(hours=1)).isoformat(),due)
            self.assertEqual(store.data,before)
            after=due+timedelta(microseconds=1)
            row=create_listing(store,"123","10","New","Ranked","",2,(due+timedelta(hours=1)).isoformat(),after)
            reloaded=CommunityStore(root)
            self.assertEqual(reloaded.guild("123")["matchmaking"][:3],before["guilds"]["123"]["matchmaking"])
            self.assertEqual([r["id"] for r in active_listings(reloaded,"123",after)],[row["id"]])
            with self.assertRaises(CommunityError):
                join_listing(reloaded,"123",before["guilds"]["123"]["matchmaking"][0]["id"],"11",after)

    def test_quota_is_scoped_to_owner_server_and_open_status(self):
        with tempfile.TemporaryDirectory() as d:
            store=CommunityStore(Path(d));now=datetime(2026,10,13,12,tzinfo=timezone.utc)
            due=(now+timedelta(hours=1)).isoformat()
            def create(guild="123",owner="10"):
                return create_listing(store,guild,owner,"Game","Mode","",1,due,now)
            rows=[create() for _ in range(3)]
            with self.assertRaises(CommunityError):create()
            create(owner="20");create(guild="456")
            join_listing(store,"123",rows[0]["id"],"11",now)
            create()
            with self.assertRaises(CommunityError):create()
            close_listing(store,"123",rows[1]["id"],"10")
            create()
            with self.assertRaises(CommunityError):create()

    def test_failed_save_after_expiry_preserves_memory_and_disk(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);store=CommunityStore(root);now=datetime(2026,10,13,12,tzinfo=timezone.utc)
            due=now+timedelta(hours=1)
            for _ in range(3):
                create_listing(store,"123","10","Game","Mode","",2,due.isoformat(),now)
            before=copy.deepcopy(store.data);disk=store.path.read_bytes()
            with patch.object(store,"save",side_effect=OSError("disk full")),self.assertRaises(OSError):
                create_listing(store,"123","10","New","Mode","",2,(due+timedelta(hours=1)).isoformat(),due+timedelta(seconds=1))
            self.assertEqual(store.data,before);self.assertEqual(store.path.read_bytes(),disk)

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

