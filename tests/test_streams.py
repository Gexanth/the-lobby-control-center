import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from community import CommunityStore
from lobby import Lobby
from streams import StreamAPI, StreamError, StreamJournal, source_input, save_config, set_enabled, send_stream, stream_overview

G='930828728966217728'; C='1515362180281663610'; M='123456789012345678'
SOURCE={'provider':'twitch','source_id':'1234','name':'Example','url':'https://twitch.tv/example'}
LIVE={'id':'98765','title':'Live','url':SOURCE['url']}
YC='UC'+'a'*22; YV='v'*11

class StreamTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.store=CommunityStore(self.root)
        self.row=self.store.save_creator(G,'Example',SOURCE['url'],'Angenommen')
        save_config(self.store,G,self.row['id'],SOURCE,C,self.row['url'])
        self.cfg=self.store.guild(G)['creators'][0]['stream_config'];self.journal=StreamJournal(self.root)
    def tearDown(self):self.tmp.cleanup()

    def test_strict_sources(self):
        self.assertEqual(source_input('https://www.twitch.tv/EXAMPLE/'),('twitch','example'))
        self.assertEqual(source_input('https://youtube.com/@example'),('youtube','@example'))
        self.assertEqual(source_input('https://youtube.com/channel/'+YC),('youtube',YC))
        for url in ('http://twitch.tv/example','https://twitch.tv.evil.test/example','https://twitch.tv/videos/123',
                    'https://youtube.com/watch?v=123','https://user:secret@twitch.tv/example','https://twitch.tv/example?foo=1'):
            with self.subTest(url=url),self.assertRaises(StreamError):source_input(url)

    def test_config_off_by_default_duplicate_and_edit_pause(self):
        self.assertFalse(self.cfg['enabled']);set_enabled(self.store,G,self.row['id'],True)
        self.store.save_creator(G,'Example',SOURCE['url'],'Pausiert',self.row['id'])
        row=self.store.guild(G)['creators'][0];self.assertFalse(row['stream_config']['enabled'])
        with self.assertRaises(StreamError):set_enabled(self.store,G,row['id'],True)
        self.store.save_creator(G,'Example',SOURCE['url'],'Angenommen',row['id'])
        set_enabled(self.store,G,row['id'],True)
        self.store.save_creator(G,'Example','https://twitch.tv/other','Angenommen',row['id'])
        self.assertFalse(self.store.guild(G)['creators'][0]['stream_config']['enabled'])
        with self.assertRaises(StreamError):set_enabled(self.store,G,row['id'],True)
        other=self.store.save_creator(G,'Duplicate','https://www.twitch.tv/example','Angenommen')
        with self.assertRaises(StreamError):save_config(self.store,G,other['id'],SOURCE,C,other['url'])
        self.assertNotIn('stream_config',str(self.store.analysis_context(G)))

    def test_save_failure_rolls_back(self):
        before=copy.deepcopy(self.store.data)
        with patch.object(self.store,'save',side_effect=OSError('full')):
            with self.assertRaises(OSError):set_enabled(self.store,G,self.row['id'],True)
            with self.assertRaises(OSError):save_config(self.store,G,self.row['id'],SOURCE,M,self.row['url'])
        self.assertEqual(before,self.store.data)

    def test_twitch_validated_token_resolve_and_live_identity(self):
        calls=[]
        def get(url,headers):
            calls.append((url,headers))
            if '/validate' in url:return {'client_id':'client','expires_in':3600}
            if '/users?' in url:return {'data':[{'id':'1234','login':'example','display_name':'Example'}]}
            return {'data':[{'id':'98765','user_id':'1234','type':'live','title':'Live'}]}
        api=StreamAPI('client','secret',get=get)
        source=api.resolve(SOURCE['url']);self.assertEqual(source,SOURCE)
        self.assertEqual(api.live(source),[LIVE]);self.assertEqual(sum('/validate' in c[0] for c in calls),2)
        self.assertTrue(all('secret' not in c[0] for c in calls))
        bad=StreamAPI('other','secret',get=get)
        with self.assertRaises(StreamError):bad.live(SOURCE)
        def wrong(url,headers):
            if '/validate' in url:return {'client_id':'client','expires_in':1}
            return {'data':[{'id':'98765','user_id':'999','type':'live'}]}
        with self.assertRaises(StreamError):StreamAPI('client','secret',get=wrong).live(SOURCE)

    def test_offline_vs_malformed_response(self):
        def get(url,headers):return {'client_id':'client','expires_in':5} if '/validate' in url else {'data':[]}
        self.assertEqual(StreamAPI('client','token',get=get).live(SOURCE),[])
        def bad(url,headers):return {'client_id':'client','expires_in':5} if '/validate' in url else {}
        with self.assertRaises(StreamError):StreamAPI('client','token',get=bad).live(SOURCE)

    def test_youtube_resolves_handle_checks_actual_live_and_keeps_key_out_of_url(self):
        ended=False;calls=[]
        def get(url,headers):
            calls.append((url,headers))
            if '/channels?' in url:return {'items':[{'id':YC,'snippet':{'title':'Example'}}]}
            if '/search?' in url:return {'items':[{'id':{'videoId':YV},'snippet':{'channelId':YC}}]}
            return {'items':[{'id':YV,'snippet':{'channelId':YC,'title':'Stream','liveBroadcastContent':'live'},
                              'liveStreamingDetails':{'actualStartTime':'2026-10-09T01:00:00Z',**({'actualEndTime':'2026-10-09T02:00:00Z'} if ended else {})}}]}
        api=StreamAPI(youtube_key='secret',get=get);cfg=api.resolve('https://youtube.com/@example')
        self.assertEqual(cfg['source_id'],YC);self.assertEqual(api.live(cfg)[0]['id'],YV)
        ended=True;self.assertEqual(api.live(cfg),[])
        self.assertTrue(all('secret' not in url and headers=={'X-Goog-Api-Key':'secret'} for url,headers in calls))
        self.assertTrue(any('eventType=live' in url for url,_ in calls))

    def test_youtube_wrong_channel_blocks(self):
        source=dict(provider='youtube',source_id=YC,url='https://youtube.com/channel/'+YC)
        api=StreamAPI(youtube_key='secret',get=lambda u,h:{'items':[{'id':{'videoId':YV},'snippet':{'channelId':'UCwrong'}}]})
        with self.assertRaises(StreamError):api.live(source)

    def test_check_interval_and_budget_survive_restart(self):
        j=self.journal;j.start_check(G,self.cfg,now=1000)
        self.assertFalse(StreamJournal(self.root).due(G,self.cfg,now=1119))
        self.assertTrue(j.due(G,self.cfg,now=1120))
        with self.assertRaises(StreamError):j.start_check(G,self.cfg,now=1119)
        for i in range(80):j.start_check(G,dict(provider='youtube',source_id=str(i)),now=2000)
        with self.assertRaises(StreamError):StreamJournal(self.root).start_check(G,dict(provider='youtube',source_id='extra'),now=2001)
        j.start_check(G,dict(provider='youtube',source_id='extra'),now=2000+86401)

    def test_dashboard_overview_reads_real_journal_without_mutation(self):
        set_enabled(self.store,G,self.row['id'],True)
        cfg=self.store.guild(G)['creators'][0]['stream_config']
        empty_root=self.root/'empty';empty_root.mkdir()
        empty=stream_overview(empty_root,G,self.store.guild(G)['creators'],now=1000)
        self.assertEqual((empty['active'],empty['never'],empty['sent']),(1,1,0))
        self.assertFalse(empty['journal']);self.assertFalse((empty_root/'streams.sqlite3').exists())
        self.journal.start_check(G,cfg,now=1000);self.journal.record(G,cfg,'Fehler: Anbieter nicht erreichbar')
        self.journal.reserve(G,cfg,LIVE)
        other=dict(cfg,source_id='other',provider='youtube',enabled=True,creator_url='https://youtube.com/@other')
        self.store.guild(G)['creators'].append({'id':'other','name':'Other','url':'https://youtube.com/@other','status':'Angenommen','stream_config':other})
        state=stream_overview(self.root,G,self.store.guild(G)['creators'],now=1200)
        self.assertEqual((state['configured'],state['active'],state['paused']),(2,2,0))
        self.assertEqual((state['current'],state['due'],state['never']),(0,1,1))
        self.assertEqual((state['errors'],state['sent'],state['unclear']),(1,0,1))
        isolated=stream_overview(self.root,'123456789012345679',[],now=1200)
        self.assertEqual((isolated['sent'],isolated['unclear']),(0,0))

    def client(self,mode='ok'):
        self.posts=[]
        def transport(method,path,payload,reason):
            if method=='GET':return {'id':C,'guild_id':G,'type':0}
            self.posts.append(payload)
            if mode=='timeout':raise TimeoutError('secret must not reach errors')
            if mode=='wrong':return {'id':M,'channel_id':M}
            return {'id':M,'channel_id':self.cfg['channel']}
        return Lobby('test-token',G,writes=True,db=self.root/'audit.db',transport=transport)

    def test_exactly_one_attempt_after_restart_target_change_and_creator_removal(self):
        client=self.client();self.assertIn('gesendet',send_stream(client,self.journal,G,self.cfg,LIVE))
        self.assertEqual(len(self.posts),1)
        self.assertEqual(self.posts[0]['allowed_mentions'],{'parse':[]});self.assertTrue(self.posts[0]['enforce_nonce'])
        self.assertEqual(self.journal.history(G,self.cfg)[0][1],'sent')
        self.store.remove_creator(G,self.row['id']);cfg=dict(self.cfg,channel=M)
        send_stream(client,StreamJournal(self.root),G,cfg,LIVE)
        self.assertEqual(len(self.posts),1)
        send_stream(client,self.journal,G,self.cfg,dict(LIVE,id='98766'))
        self.assertEqual(len(self.posts),2)

    def test_uncertain_delivery_no_retry_and_response_validation(self):
        for mode in ('timeout','wrong'):
            with self.subTest(mode=mode):
                client=self.client(mode);stream=dict(LIVE,id=mode)
                with self.assertRaisesRegex(StreamError,'Versand unklar'):send_stream(client,self.journal,G,self.cfg,stream)
                self.assertEqual(self.journal.history(G,self.cfg)[0][1],'uncertain')
                send_stream(client,StreamJournal(self.root),G,self.cfg,stream)
                self.assertEqual(len(self.posts),1)

    def test_unfinished_reservation_and_failed_disk_write_prevent_post(self):
        client=self.client();self.journal.reserve(G,self.cfg,LIVE)
        send_stream(client,StreamJournal(self.root),G,self.cfg,LIVE);self.assertEqual(self.posts,[])
        with patch.object(self.journal,'reserve',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):send_stream(client,self.journal,G,self.cfg,dict(LIVE,id='other'))
        self.assertEqual(self.posts,[])
        client.writes=False
        with self.assertRaises(StreamError):send_stream(client,self.journal,G,self.cfg,dict(LIVE,id='other'))

