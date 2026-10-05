import copy,tempfile,unittest
from pathlib import Path
from lobby import Lobby
from ai_assistant import validate_plan,AIError
try:
    from channel_actions import prepare,execute,deletion_details,DeleteConfirmation
    QT=True
except ImportError:QT=False
G='930828728966217728';C='123456789012345671';K='123456789012345672';OTHER='123456789012345673'
class FakeDelete:
    def __init__(self):
        self.calls=[];self.guild={'id':G,'features':[]}
        self.channels=[{'id':K,'guild_id':G,'name':'EVENTS','type':4,'parent_id':None},{'id':C,'guild_id':G,'name':'chat','type':0,'parent_id':K}]
    def transport(self,method,path,payload,reason):
        self.calls.append((method,path))
        if path==f'/guilds/{G}':return copy.deepcopy(self.guild)
        if path==f'/guilds/{G}/channels':return copy.deepcopy(self.channels)
        item=next((c for c in self.channels if path=='/channels/'+c['id']),None)
        if item:
            if method=='DELETE':
                result=copy.deepcopy(item);self.channels.remove(item)
                for child in self.channels:
                    if child.get('parent_id')==result['id']:child['parent_id']=None
                return result
            return copy.deepcopy(item)
        raise AssertionError(path)
    def spec(self,channel=K):return {'action':'delete','channel':channel,'name':'','kind':'text','parent':None,'reason':'Remove test category'}
@unittest.skipUnless(QT,'PySide6 required')
class DeleteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.fake=FakeDelete();self.client=Lobby('test',G,writes=True,db=Path(self.tmp.name)/'audit.db',transport=self.fake.transport)
    def tearDown(self):self.tmp.cleanup()
    def test_category_preview_and_single_delete_keep_children(self):
        spec=self.fake.spec();plan=prepare(self.client,spec)
        self.assertFalse(any(m=='DELETE' for m,p in self.fake.calls));self.assertEqual(len(plan['before']['children']),1)
        self.assertIn('bleiben erhalten',deletion_details(G,spec,plan))
        execute(self.client,spec,plan)
        self.assertEqual([p for m,p in self.fake.calls if m=='DELETE'],['/channels/'+K])
        self.assertEqual(self.fake.channels[0]['id'],C);self.assertIsNone(self.fake.channels[0]['parent_id'])
    def test_channel_delete_does_not_delete_category(self):
        spec=self.fake.spec(C);plan=prepare(self.client,spec);execute(self.client,spec,plan)
        self.assertEqual(self.fake.channels[0]['id'],K)
    def test_changed_children_or_target_block_execution(self):
        spec=self.fake.spec();plan=prepare(self.client,spec);self.fake.channels[1]['name']='changed'
        with self.assertRaises(ValueError):execute(self.client,spec,plan)
        self.fake.channels[1]['name']='chat';self.fake.channels[0]['name']='new'
        with self.assertRaises(ValueError):execute(self.client,spec,plan)
        self.assertFalse(any(m=='DELETE' for m,p in self.fake.calls))
    def test_foreign_protected_and_disabled_writes_block(self):
        self.fake.channels[1]['guild_id']=OTHER
        with self.assertRaises(ValueError):prepare(self.client,self.fake.spec(C))
        self.fake.channels[1]['guild_id']=G;self.fake.guild.update(features=['COMMUNITY'],rules_channel_id=C)
        with self.assertRaises(ValueError):prepare(self.client,self.fake.spec(C))
        self.fake.guild['features']=[];spec=self.fake.spec(C);plan=prepare(self.client,spec);self.client.writes=False
        with self.assertRaises(ValueError):execute(self.client,spec,plan)
        self.assertFalse(any(m=='DELETE' for m,p in self.fake.calls))
class DeleteAIValidationTests(unittest.TestCase):
    def test_ai_only_prepares_known_single_target_with_null_fields(self):
        context={'id':G,'channels':FakeDelete().channels};value={'message':'Preview required','action':'delete','channel':K,'name':None,'kind':None,'parent':None}
        self.assertEqual(validate_plan(value,context,'Delete category')['channel'],K)
        for key,change in [('channel',OTHER),('name','other'),('parent',K),('kind','category')]:
            bad=dict(value,**{key:change})
            with self.assertRaises(AIError):validate_plan(bad,context,'Delete')
