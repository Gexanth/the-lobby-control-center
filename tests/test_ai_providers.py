import json
import unittest
from unittest.mock import patch
from ai_assistant import request_plan,AIError

ANSWER=dict(message='Hallo',action='answer',channel=None,name=None,kind=None,parent=None)
CONTEXT={'id':'g','name':'Lobby','token':'NEVER_SEND','channels':[{'id':'c','name':'chat','type':0,'parent_id':None}]}
def response(value=ANSWER,stop='tool_use'):
    return {'stop_reason':stop,'content':[{'type':'tool_use','name':'lobby_plan','input':value}]}

class Providers(unittest.TestCase):
    def test_claude_payload_and_whitelist(self):
        def transport(p):
            self.assertEqual(p['tool_choice']['name'],'lobby_plan')
            self.assertNotIn('NEVER_SEND',json.dumps(p))
            self.assertNotIn('input',p)
            return response()
        self.assertIsNone(request_plan('key','model','Hallo',CONTEXT,[],transport,provider='anthropic')['spec'])
    def test_claude_action_is_only_plan(self):
        value=dict(ANSWER,action='rename',channel='c',name='neu')
        result=request_plan('key','model','Umbenennen',CONTEXT,[],lambda _:response(value),provider='anthropic')
        self.assertEqual(result['spec']['channel'],'c')
        self.assertEqual(result['guild'],'g')
    def test_claude_fails_closed(self):
        bad=[response(stop='max_tokens'),response(dict(ANSWER,action='delete',channel='invented')),{'stop_reason':'tool_use','content':[]},response(None)]
        duplicate=response();duplicate['content']*=2;bad.append(duplicate)
        for item in bad:
            with self.subTest(item=item),self.assertRaises(AIError):
                request_plan('key','model','Hallo',CONTEXT,[],lambda _:item,provider='anthropic')
    def test_openai_compatible(self):
        r={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(ANSWER)}]}]}
        self.assertEqual(request_plan('key','model','Hallo',None,[],lambda _:r)['message'],'Hallo')
    def test_anthropic_headers(self):
        with patch('ai_assistant.urlopen') as opener:
            opener.return_value.__enter__.return_value.read.return_value=json.dumps(response()).encode()
            request_plan('secret','model','Hallo',None,[],provider='anthropic')
            req=opener.call_args.args[0]
            self.assertEqual(req.full_url,'https://api.anthropic.com/v1/messages')
            self.assertEqual(req.get_header('X-api-key'),'secret')
            self.assertIsNone(req.get_header('Authorization'))
    def test_no_key_or_unknown_provider(self):
        for key,provider in [('', 'anthropic'),('key','unknown')]:
            with self.assertRaises(AIError):request_plan(key,'model','Hallo',None,[],provider=provider)

if __name__=='__main__':unittest.main()
