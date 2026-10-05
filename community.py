"""Local community state and bounded activity aggregation without message content."""
import uuid,copy
from datetime import datetime,timezone,timedelta
from urllib.parse import urlparse
from updates import DATA,atomic_json,read_json

class CommunityError(ValueError):pass

def utcnow():return datetime.now(timezone.utc)
def parse_time(value):
    try:d=datetime.fromisoformat(value.replace('Z','+00:00'))
    except (ValueError,TypeError,AttributeError):raise CommunityError('Datum als JJJJ-MM-TT HH:MM eingeben.') from None
    return d.astimezone(timezone.utc)

def activity_sample(messages,channel_id,now=None):
    now=now or utcnow();people=set();recent_people=set();times=[];count=0;recent=0
    for m in messages:
        if m.get('bot') or not m.get('author_id'):continue
        try:t=parse_time(m['timestamp'])
        except (CommunityError,KeyError):continue
        if t>now:continue
        people.add(m['author_id']);times.append(t);count+=1
        if t>=now-timedelta(hours=24):recent+=1;recent_people.add(m['author_id'])
    return {'channel_id':channel_id,'checked_at':now.isoformat(),'messages':count,'participants':len(people),'sample_size':len(messages),'messages_24h':recent,'participants_24h':len(recent_people),'limit_reached':len(messages)>=100,'oldest':min(times).isoformat() if times else None,'latest':max(times).isoformat() if times else None,'scope':'Letzte maximal 100 Nachrichten eines ausgewählten Kanals; keine vollständige Wochenaktivität.'}

class CommunityStore:
    def __init__(self,root=DATA):
        self.path=root/'community.json'
        self.data=read_json(self.path,{'format':1,'guilds':{}})
        if not isinstance(self.data,dict) or self.data.get('format')!=1 or not isinstance(self.data.get('guilds'),dict):raise CommunityError('Community-Datei ungültig; sie wird nicht überschrieben.')
    def guild(self,guild):
        if not guild:raise CommunityError('Zuerst Discord verbinden.')
        return self.data['guilds'].setdefault(guild,{'activity':{},'nights':[],'creators':[]})
    def save(self):atomic_json(self.path,self.data)
    def record_activity(self,guild,sample):
        g=self.guild(guild);before=copy.deepcopy(g)
        g['activity'][sample['channel_id']]=sample
        history=g.setdefault('activity_history',{}).setdefault(sample['channel_id'],[])
        when=parse_time(sample['checked_at']);cutoff=when-timedelta(days=30)
        history[:]=[x for x in history if parse_time(x['checked_at'])>=cutoff]
        bucket=int(when.timestamp())//900
        if history and int(parse_time(history[-1]['checked_at']).timestamp())//900==bucket:history[-1]=dict(sample)
        else:history.append(dict(sample))
        history[:]=history[-96:]
        try:self.save()
        except OSError:
            self.data['guilds'][guild]=before;raise
    def history(self,guild,channel):
        g=self.guild(guild)
        return g.get('activity_history',{}).get(channel,[])
    def add_night(self,guild,title,when,suggestions):
        if not 1<=len(title.strip())<=120:raise CommunityError('Titel mit 1–120 Zeichen eingeben.')
        due=parse_time(when)
        if due<=utcnow():raise CommunityError('Der Termin muss in der Zukunft liegen.')
        options=[x.strip() for x in suggestions.split('\n') if x.strip()]
        if not 2<=len(options)<=10:raise CommunityError('2–10 Spielvorschläge eingeben, einen pro Zeile.')
        night={'id':uuid.uuid4().hex,'title':title.strip(),'when':due.isoformat(),'options':options,'reminded':False,'status':'geplant'}
        self.guild(guild)['nights'].append(night);self.save();return night
    def due_nights(self,guild,now=None):
        now=now or utcnow()
        return [n for n in self.guild(guild)['nights'] if n['status']=='geplant' and not n['reminded'] and parse_time(n['when'])<=now]
    def mark_reminded(self,guild,item):
        for n in self.guild(guild)['nights']:
            if n['id']==item:n['reminded']=True
        self.save()
    def cancel_night(self,guild,item):
        for n in self.guild(guild)['nights']:
            if n['id']==item:n['status']='abgesagt'
        self.save()
    def save_creator(self,guild,name,url,status,item=None):
        parsed=urlparse(url)
        if not name.strip() or len(name)>100:raise CommunityError('Creator-Namen mit höchstens 100 Zeichen eingeben.')
        if parsed.scheme!='https' or parsed.hostname not in ('twitch.tv','www.twitch.tv','youtube.com','www.youtube.com') or parsed.username or parsed.password or not parsed.path.strip('/'):
            raise CommunityError('Vollständigen HTTPS-Kanallink von Twitch oder YouTube eingeben.')
        if status not in ('Bewerbung','Angenommen','Pausiert'):raise CommunityError('Ungültiger Creator-Status.')
        g=self.guild(guild);before=copy.deepcopy(g['creators']);rows=copy.deepcopy(before)
        existing=next((x for x in rows if x['id']==item),None) if item else next((x for x in rows if x['url']==url),None)
        if item and not existing:raise CommunityError('Creator nicht mehr vorhanden. Auswahl erneut öffnen.')
        if item and any(x['url']==url and x['id']!=item for x in rows):raise CommunityError('Dieser Kanallink gehört bereits zu einem anderen Creator.')
        if existing:existing.update(name=name.strip(),url=url,status=status);result=existing
        else:
            result={'id':uuid.uuid4().hex,'name':name.strip(),'url':url,'status':status};rows.append(result)
        g['creators']=rows
        try:self.save()
        except OSError:g['creators']=before;raise
        return copy.deepcopy(result)
    def remove_creator(self,guild,item):
        g=self.guild(guild);before=copy.deepcopy(g['creators']);g['creators']=[x for x in before if x['id']!=item]
        try:self.save()
        except OSError:g['creators']=before;raise
    def analysis_context(self,guild):
        g=self.guild(guild)
        return {'activity_samples':list(g['activity'].values()),'planned_lobby_nights':g['nights'],'creator_status_counts':{s:sum(x['status']==s for x in g['creators']) for s in ('Bewerbung','Angenommen','Pausiert')},'limits':'Aktivität ist eine begrenzte Kanalstichprobe, keine vollständige Servermessung. Lobby Nights und Creator-Status werden lokal geplant, nicht mit Discord synchronisiert.'}
