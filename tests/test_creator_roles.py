import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from lobby import Lobby,DiscordError
from community import CommunityStore,CommunityError
from creator_roles import binding,save_binding,delivery,checked_plan,assign_checked
G='930828728966217728';B='123456789012345670';U='123456789012345671';R='123456789012345672';BR='123456789012345673'
class FakeRoles:
    def __init__(self):
        self.calls=[];self.member_roles=[];self.fail=False
        self.roles=[{'id':G,'name':'everyone','position':0,'permissions':'0','managed':False},{'id':BR,'name':'bot','position':10,'permissions':str(1<<28),'managed':True},{'id':R,'name':'Streamer','position':2,'permissions':'0','managed':False}]
    def transport(self,method,path,payload,reason):
        self.calls.append((method,path))
        if method=='PUT':
            if self.fail:raise DiscordError('simulated network failure')
            self.member_roles=[R];return {'ok':True}
        if path=='/users/@me':return {'id':B}
        if path==f'/guilds/{G}':return {'id':G}
        if path==f'/guilds/{G}/roles':return copy.deepcopy(self.roles)
        if path==f'/guilds/{G}/members/{B}':return {'user':{'id':B,'bot':True},'roles':[BR]}
        if path==f'/guilds/{G}/members/{U}':return {'user':{'id':U,'username':'Creator'},'roles':self.member_roles[:]}
        raise AssertionError(path)
class RoleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.fake=FakeRoles();self.client=Lobby('test',G,writes=True,db=self.root/'audit.db',transport=self.fake.transport);self.link=binding(U,R)
    def tearDown(self):self.tmp.cleanup()
    def test_checked_assignment_and_existing_role_no_second_write(self):
        plan=checked_plan(self.client,G,self.link);self.assertFalse(plan['has_role']);result=assign_checked(self.client,plan)
        self.assertFalse(result['already_present']);self.assertTrue(assign_checked(self.client,plan)['already_present'])
        self.assertEqual(sum(m=='PUT' for m,p in self.fake.calls),1)
        self.assertFalse(any(p==f'/guilds/{G}/members' for m,p in self.fake.calls))
    def test_permission_hierarchy_managed_and_privileged_roles_block(self):
        for key,value,index in [('permissions','0',1),('position',10,2),('managed',True,2),('permissions','8',2)]:
            original=self.fake.roles[index][key];self.fake.roles[index][key]=value
            with self.assertRaises(CommunityError):checked_plan(self.client,G,self.link)
            self.fake.roles[index][key]=original
        with self.assertRaises(CommunityError):checked_plan(self.client,'123456789012345674',self.link)
        self.assertFalse(any(m=='PUT' for m,p in self.fake.calls))
    def test_changed_preview_and_write_disabled_block(self):
        plan=checked_plan(self.client,G,self.link);self.fake.roles[2]['name']='Changed'
        with self.assertRaises(CommunityError):assign_checked(self.client,plan)
        self.fake.roles[2]['name']='Streamer';self.client.writes=False
        with self.assertRaises(ValueError):assign_checked(self.client,plan)
        self.assertFalse(any(m=='PUT' for m,p in self.fake.calls))
    def test_binding_and_unclear_status_persist_without_exposing_to_ai(self):
        store=CommunityStore(self.root);row=store.save_creator(G,'Creator','https://www.twitch.tv/test','Angenommen')
        save_binding(store,G,row['id'],self.link);delivery(store,G,row['id'],self.link,'uncertain')
        self.assertEqual(CommunityStore(self.root).guild(G)['creators'][0]['role_delivery']['state'],'uncertain')
        self.assertNotIn(U,str(store.analysis_context(G)))
        before=copy.deepcopy(store.data)
        with patch.object(store,'save',side_effect=OSError('full')):
            with self.assertRaises(OSError):save_binding(store,G,row['id'],binding(B,R))
            with self.assertRaises(OSError):delivery(store,G,row['id'],self.link,'confirmed')
        self.assertEqual(store.data,before)
