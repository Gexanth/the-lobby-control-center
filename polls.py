"""Native Discord poll payload validation and durable delivery journal."""
import copy,hashlib
from datetime import datetime,timezone
from community import CommunityError,parse_time
from lobby import snowflake

def poll_spec(guild,night,channel,hours,multi):
    snowflake(guild);snowflake(channel)
    if night.get('status')!='geplant':raise CommunityError('Nur geplante Lobby Nights können veröffentlicht werden.')
    if night.get('poll_delivery',{}).get('state') in ('sending','uncertain','sent'):raise CommunityError('Diese Abstimmung wurde veröffentlicht oder ihr Versand ist unklar. Zuerst den gespeicherten Versandstatus prüfen.')
    if parse_time(night['when'])<=datetime.now(timezone.utc):raise CommunityError('Der Lobby-Night-Termin liegt bereits in der Vergangenheit.')
    if type(hours) is not int or not 1<=hours<=768 or type(multi) is not bool:raise CommunityError('Abstimmungsdauer: 1–768 Stunden; Mehrfachauswahl muss an/aus sein.')
    question=night['title']+' · Was wollt ihr spielen?'
    if not 1<=len(question)<=300:raise CommunityError('Die Abstimmungsfrage darf höchstens 300 Zeichen haben.')
    options=night['options']
    if not 2<=len(options)<=10 or any(not isinstance(x,str) or not 1<=len(x.strip())<=55 for x in options):raise CommunityError('Eine Discord-Abstimmung benötigt 2–10 Antworten mit jeweils höchstens 55 Zeichen.')
    if len({x.strip().casefold() for x in options})!=len(options):raise CommunityError('Doppelte Antwortmöglichkeiten entfernen.')
    nonce=hashlib.sha256((guild+night['id']).encode()).hexdigest()[:24]
    return {'guild':guild,'night_id':night['id'],'channel':channel,'payload':{'content':'Geplanter Termin: '+parse_time(night['when']).astimezone().strftime('%d.%m.%Y %H:%M')+'\nEigene Spielvorschläge sind willkommen.','poll':{'question':{'text':question},'answers':[{'poll_media':{'text':x.strip()}} for x in options],'duration':hours,'allow_multiselect':multi,'layout_type':1},'allowed_mentions':{'parse':[]},'nonce':nonce,'enforce_nonce':True}}

class PollJournal:
    def __init__(self,store):self.store=store
    def night(self,guild,item):
        n=next((n for n in self.store.guild(guild)['nights'] if n['id']==item),None)
        if not n:raise CommunityError('Lobby Night nicht mehr vorhanden.')
        return n
    def change(self,guild,item,value):
        n=self.night(guild,item);old=copy.deepcopy(n)
        n['poll_delivery']=value
        try:self.store.save()
        except OSError:n.clear();n.update(old);raise
    def begin(self,spec):
        n=self.night(spec['guild'],spec['night_id'])
        current=poll_spec(spec['guild'],n,spec['channel'],spec['payload']['poll']['duration'],spec['payload']['poll']['allow_multiselect'])
        if current!=spec:raise CommunityError('Planung hat sich seit der Vorschau geändert. Erneut prüfen.')
        self.change(spec['guild'],spec['night_id'],{'state':'sending','channel':spec['channel'],'spec':copy.deepcopy(spec),'attempted_at':datetime.now(timezone.utc).isoformat()})
    def schedule(self,spec,send_at):
        now=datetime.now(timezone.utc);due=parse_time(send_at)
        night=self.night(spec['guild'],spec['night_id'])
        if not now<due<parse_time(night['when']):raise CommunityError('Veröffentlichung muss in der Zukunft und vor der Lobby Night liegen.')
        current=poll_spec(spec['guild'],night,spec['channel'],spec['payload']['poll']['duration'],spec['payload']['poll']['allow_multiselect'])
        if current!=spec:raise CommunityError('Planung seit der Vorschau geändert.')
        self.change(spec['guild'],spec['night_id'],{'state':'scheduled','channel':spec['channel'],'spec':copy.deepcopy(spec),'send_at':due.isoformat()})
    def due(self,guild,now=None):
        now=now or datetime.now(timezone.utc)
        return [copy.deepcopy(n['poll_delivery']['spec']) for n in self.store.guild(guild)['nights'] if n.get('poll_delivery',{}).get('state')=='scheduled' and parse_time(n['poll_delivery']['send_at'])<=now and n.get('status')=='geplant' and parse_time(n['when'])>now]
    def unschedule(self,guild,item):
        if self.night(guild,item).get('poll_delivery',{}).get('state')!='scheduled':raise CommunityError('Keine geplante Veröffentlichung ausgewählt.')
        self.change(guild,item,{'state':'ready'})
    def finish(self,spec,message):
        if not isinstance(message,dict) or message.get('channel_id')!=spec['channel']:raise CommunityError('Discord-Antwort konnte dem Zielkanal nicht zugeordnet werden.')
        snowflake(message.get('id'));self.change(spec['guild'],spec['night_id'],{'state':'sent','channel':spec['channel'],'message_id':message['id'],'spec':copy.deepcopy(spec)})
    def uncertain(self,spec):
        old=self.night(spec['guild'],spec['night_id']).get('poll_delivery',{})
        self.change(spec['guild'],spec['night_id'],dict(old,state='uncertain'))
    def reset_uncertain(self,guild,item):
        state=self.night(guild,item).get('poll_delivery',{}).get('state')
        if state not in ('sending','uncertain'):raise CommunityError('Nur ein unklarer Versand kann erneut freigegeben werden.')
        self.change(guild,item,{'state':'ready'})

def send_poll(client,spec):
    if client.guild!=spec['guild']:raise CommunityError('Der verbundene Server stimmt nicht mit der Vorschau überein.')
    if client.channel(spec['channel']).get('type')!=0:raise CommunityError('Discord-Abstimmungen nur in normalen Textkanälen veröffentlichen.')
    return client._change('POST',f"/channels/{spec['channel']}/messages",copy.deepcopy(spec['payload']),'Lobby Night Abstimmung',False)


def read_poll_results(client,guild,delivery):
    if client.guild!=guild or delivery.get('state')!='sent':raise CommunityError('Zuerst mit dem Server der veröffentlichten Abstimmung verbinden.')
    channel=snowflake(delivery.get('channel'));message=snowflake(delivery.get('message_id'))
    client.channel(channel)
    data=client.request('GET',f'/channels/{channel}/messages/{message}')
    if not isinstance(data,dict) or data.get('id')!=message or data.get('channel_id')!=channel:raise CommunityError('Abstimmungsnachricht konnte nicht zugeordnet werden.')
    poll=data.get('poll')
    if not isinstance(poll,dict):raise CommunityError('Discord liefert keine Abstimmungsdaten. Bot-Rechte oder gelöschte Nachricht prüfen.')
    results=poll.get('results')
    if not isinstance(results,dict):return 'Ergebnisse aktuell nicht verfügbar. Das bedeutet nicht, dass es keine Stimmen gibt.'
    counts={x['id']:x['count'] for x in results.get('answer_counts',[])}
    lines=['Endgültig ausgezählt.' if results.get('is_finalized') else 'Zwischenstand; während der Abstimmung können die Zahlen abweichen.']
    for answer in poll.get('answers',[]):lines.append(str(answer.get('poll_media',{}).get('text','Antwort'))+': '+str(counts.get(answer.get('answer_id'),0))+' Stimmen')
    return '\n'.join(lines)
