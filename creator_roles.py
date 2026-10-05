"""Reviewed, single-member Creator role assignment. No bulk member discovery."""
import copy
from community import CommunityError
from lobby import snowflake

def binding(member,role):
    return {'member_id':snowflake(member),'role_id':snowflake(role)}

def save_binding(store,guild,item,link):
    link=binding(link['member_id'],link['role_id'])
    row=next((r for r in store.guild(guild)['creators'] if r['id']==item),None)
    if not row:raise CommunityError('Creator nicht mehr vorhanden.')
    old=copy.deepcopy(row);row['discord_link']=link
    if old.get('discord_link')!=link:row.pop('role_delivery',None)
    try:store.save()
    except OSError:row.clear();row.update(old);raise

def delivery(store,guild,item,link,state):
    row=next((r for r in store.guild(guild)['creators'] if r['id']==item),None)
    if not row or row.get('discord_link')!=link or row['status']!='Angenommen':raise CommunityError('Creator-Auswahl oder Verknüpfung geändert. Erneut prüfen.')
    old=copy.deepcopy(row);row['role_delivery']=dict(link,state=state)
    try:store.save()
    except OSError:row.clear();row.update(old);raise

def checked_plan(client,guild,link):
    if client.guild!=guild:raise CommunityError('Zuerst mit dem Server dieses Creators verbinden.')
    link=binding(link['member_id'],link['role_id'])
    me=client.request('GET','/users/@me');bot_id=snowflake(me.get('id'))
    server=client.request('GET',f'/guilds/{guild}')
    if server.get('id')!=guild:raise CommunityError('Serverantwort stimmt nicht mit der Auswahl überein.')
    roles=client.roles();lookup={r['id']:r for r in roles}
    role=lookup.get(link['role_id'])
    if not role or role['id']==guild or role.get('managed') or int(role.get('permissions','0'))!=0:
        raise CommunityError('Nur normale Rollen ohne serverweite Zusatzberechtigungen sind unterstützt.')
    bot=client.request('GET',f'/guilds/{guild}/members/{bot_id}')
    if bot.get('user',{}).get('id')!=bot_id:raise CommunityError('Bot-Mitglied konnte nicht geprüft werden.')
    assigned=[guild]+bot.get('roles',[])
    if any(r not in lookup for r in assigned):raise CommunityError('Bot-Rollen unvollständig. Serverübersicht aktualisieren.')
    permissions=0
    for r in assigned:permissions|=int(lookup[r].get('permissions','0'))
    if not permissions & ((1<<28)|(1<<3)):raise CommunityError('Dem Bot fehlt Rollen verwalten.')
    highest=max(int(lookup[r]['position']) for r in assigned)
    if int(role['position'])>=highest:raise CommunityError('Die Creator-Rolle muss unter der höchsten Bot-Rolle stehen.')
    member=client.request('GET',f"/guilds/{guild}/members/{link['member_id']}")
    user=member.get('user',{})
    if user.get('id')!=link['member_id'] or user.get('bot'):raise CommunityError('Die Mitglieds-ID muss zu einem menschlichen Mitglied dieses Servers gehören.')
    return dict(link,guild=guild,member_name=user.get('global_name') or user.get('username') or link['member_id'],role_name=role['name'],role_position=role['position'],has_role=role['id'] in member.get('roles',[]))

def assign_checked(client,plan):
    current=checked_plan(client,plan['guild'],plan)
    if any(current[k]!=plan[k] for k in ('guild','member_id','role_id','member_name','role_name','role_position')):raise CommunityError('Die geprüfte Vorschau hat sich geändert. Erneut prüfen.')
    if current['has_role']:return {'already_present':True}
    result=client._change('PUT',f"/guilds/{plan['guild']}/members/{plan['member_id']}/roles/{plan['role_id']}",None,'Creator Hub: ausdrücklich bestätigte Rollenvergabe',False)
    member=client.request('GET',f"/guilds/{plan['guild']}/members/{plan['member_id']}")
    if member.get('user',{}).get('id')!=plan['member_id'] or plan['role_id'] not in member.get('roles',[]):raise CommunityError('Rollenvergabe konnte nicht bestätigt werden. Mitglied in Discord prüfen.')
    return {'already_present':False,'audit_warning':result.get('audit_warning') if isinstance(result,dict) else None}
