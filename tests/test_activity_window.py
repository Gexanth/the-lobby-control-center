import tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from lobby import Lobby,DiscordError,discord_http_error_message

GUILD='930828728966217728';CHANNEL='123456789012345678'
class WindowTests(unittest.TestCase):
    def batch(self,start,count,now,age=0):
        return [{'id':str(900000000000000000-start-i),'timestamp':(now-timedelta(hours=age)).isoformat(),'author':{'id':str(i),'bot':i==0},'content':'do not retain'} for i in range(count)]
    def client(self,batches):
        calls=[]
        def transport(method,path,payload,reason):
            self.assertEqual(method,'GET');calls.append(path)
            if '?' not in path:return {'id':CHANNEL,'guild_id':GUILD,'type':0}
            if not batches:raise AssertionError('Unexpected extra page')
            item=batches.pop(0)
            if isinstance(item,Exception):raise item
            return item
        return Lobby('test',GUILD,transport=transport),calls
    def test_paginate_and_stop_at_window(self):
        now=datetime.now(timezone.utc)
        client,calls=self.client([self.batch(0,100,now),self.batch(100,100,now,age=25)])
        s=client.activity_window(CHANNEL,now=now)
        self.assertEqual(s['coverage'],'window_reached');self.assertEqual(s['pages'],2)
        self.assertEqual(s['messages_24h'],99);self.assertEqual(s['sample_size'],200)
        self.assertIn('before=899999999999999901',calls[-1]);self.assertNotIn('do not retain',repr(s))
    def test_cap_and_empty_not_reported_as_complete(self):
        now=datetime.now(timezone.utc)
        client,_=self.client([self.batch(i*100,100,now) for i in range(5)])
        s=client.activity_window(CHANNEL,now=now);self.assertEqual(s['coverage'],'capped');self.assertTrue(s['limit_reached'])
        client,_=self.client([[]]);self.assertEqual(client.activity_window(CHANNEL,now=now)['coverage'],'empty_or_no_history_access')
    def test_short_page_and_failure(self):
        now=datetime.now(timezone.utc)
        client,_=self.client([self.batch(0,3,now)])
        self.assertEqual(client.activity_window(CHANNEL,now=now)['coverage'],'history_end')
        client,_=self.client([self.batch(0,100,now),DiscordError('rate limited')])
        with self.assertRaises(DiscordError):client.activity_window(CHANNEL,now=now)
    def test_cursor_must_advance(self):
        now=datetime.now(timezone.utc);batch=self.batch(0,100,now)
        client,_=self.client([batch,batch])
        with self.assertRaises(DiscordError):client.activity_window(CHANNEL,now=now)
    def test_http_permission_guidance_is_endpoint_specific_and_sanitized(self):
        messages=discord_http_error_message(403,'GET',f'/channels/{CHANNEL}/messages?limit=100')
        self.assertIn('Kanal ansehen',messages);self.assertIn('Nachrichtenverlauf anzeigen',messages)
        self.assertIn('nicht erforderlich',messages);self.assertNotIn('token',messages.lower())
        channel=discord_http_error_message(403,'GET',f'/channels/{CHANNEL}')
        self.assertIn('Kanal ansehen',channel);self.assertNotIn('Nachrichtenverlauf anzeigen',channel)
        self.assertIn('nicht sichtbar',discord_http_error_message(404,'GET',f'/channels/{CHANNEL}'))
        self.assertEqual(discord_http_error_message(403,'POST','/guilds/x'),'Bot hat keinen Zugriff. Rechte der Bot-Rolle und Kanalüberschreibungen prüfen.')
