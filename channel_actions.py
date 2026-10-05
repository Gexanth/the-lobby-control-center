from copy import deepcopy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox, QDialog, QDialogButtonBox, QTextEdit
from lobby import name


def prepare(client, spec):
    action=spec['action']
    reason=spec['reason']
    before=None
    if action=='create':
        channels=client.channels()
        if any(c.get('name')==name(spec['name']) and c.get('type')=={'text':0,'voice':2,'category':4}[spec['kind']] and c.get('parent_id')==spec['parent'] for c in channels):
            raise ValueError('Ein gleichnamiger Kanal dieses Typs existiert bereits am Ziel.')
        plan=client.create_channel(spec['name'],spec['kind'],spec['parent'],reason,preview=True)
    else:
        channel=client.channel(spec['channel'])
        if channel.get('id')!=spec['channel']:raise ValueError('Kanalantwort stimmt nicht mit der ausgewählten ID überein.')
        before={key:channel.get(key) for key in ('id','name','type','parent_id')}
        if action=='rename':
            if channel['name']==name(spec['name']): raise ValueError('Der Kanal hat diesen Namen bereits.')
            plan=client.edit_channel(spec['channel'],channel_name=spec['name'],reason=reason,preview=True)
        elif action=='delete':
            if channel.get('type') not in (0,2,4,5,13,15,16):raise ValueError('Dieser Kanaltyp wird für das Löschen nicht unterstützt.')
            guild=client.request('GET',f'/guilds/{client.guild}')
            if guild.get('id')!=client.guild:raise ValueError('Serverantwort stimmt nicht mit der Verbindung überein.')
            if 'COMMUNITY' in guild.get('features',[]) and channel['id'] in (guild.get('rules_channel_id'),guild.get('public_updates_channel_id')):
                raise ValueError('Dieser Community-Systemkanal ist von Discord vor Löschung geschützt. Zuerst die Serverkonfiguration in Discord ändern.')
            if channel['type']==4:
                before['children']=sorted([{k:c.get(k) for k in ('id','name','type','parent_id')} for c in client.channels() if c.get('parent_id')==channel['id']],key=lambda c:c['id'])
            plan=client._change('DELETE',f"/channels/{spec['channel']}",None,reason,True)
        elif action=='move':
            if channel.get('type') not in (0,2,5,13,15,16): raise ValueError('Dieser Kanaltyp kann nicht in eine Kategorie verschoben werden.')
            if channel.get('parent_id')==spec['parent']: raise ValueError('Der Kanal befindet sich bereits am Ziel.')
            if spec['parent'] and client.channel(spec['parent']).get('type')!=4: raise ValueError('Das Ziel muss eine Kategorie sein.')
            plan=client._change('PATCH',f"/channels/{spec['channel']}",{'parent_id':spec['parent']},reason,True)
        else: raise ValueError('Unbekannte Aktion.')
    plan['before']=before
    return plan


def execute(client, spec, approved):
    current=prepare(client,spec)
    if current!=approved: raise ValueError('Der Kanal wurde seit der Vorschau geändert. Bitte eine neue Vorschau erstellen.')
    result=client._change(approved['method'],approved['path'],deepcopy(approved['payload']),approved['reason'],False)
    if spec['action']=='delete' and (not isinstance(result,dict) or result.get('id')!=spec['channel']):raise ValueError('Löschung konnte nicht bestätigt werden. Serverübersicht prüfen; nicht automatisch wiederholen.')
    return result


def deletion_details(guild,spec,plan):
    old=plan['before'];category=old['type']==4
    text=f"Server: {guild}\n{'Kategorie' if category else 'Kanal'} löschen: {old['name']}\nKanal-ID: {old['id']}\nGrund: {spec['reason']}\n\n"
    if category:
        children=old['children'];text+=f'Enthaltene Kanäle: {len(children)}\n'
        text+='\n'.join('• '+c['name']+' · '+c['id'] for c in children)
        text+='\n\nNur die Kategorie wird gelöscht. Diese Kanäle bleiben erhalten und verlieren ihre Kategoriezuordnung.'
    else:text+='Der Kanal und seine Inhalte werden endgültig gelöscht.'
    return text+'\n\nDiese Discord-Löschung kann nicht rückgängig gemacht werden. App-Wiederherstellung stellt keine Discord-Kanäle wieder her.'

class DeleteConfirmation(QDialog):
    def __init__(self,parent,details,target):
        super().__init__(parent);self.setWindowTitle('Endgültige Discord-Löschung');self.setMinimumWidth(560)
        layout=QVBoxLayout(self);text=QTextEdit();text.setReadOnly(True);text.setPlainText(details);text.setMinimumHeight(210);layout.addWidget(text)
        label=QLabel('Zur Bestätigung die angezeigte Kanal-ID eingeben:');layout.addWidget(label)
        self.id_input=QLineEdit();self.id_input.setPlaceholderText(target);layout.addWidget(self.id_input)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);self.delete_button=buttons.button(QDialogButtonBox.Ok)
        self.delete_button.setText('Endgültig löschen');self.delete_button.setObjectName('danger');self.delete_button.setEnabled(False)
        buttons.button(QDialogButtonBox.Cancel).setText('Abbrechen');buttons.rejected.connect(self.reject);buttons.accepted.connect(self.accept)
        self.id_input.textChanged.connect(lambda value:self.delete_button.setEnabled(value==target));layout.addWidget(buttons)


class ChannelActions(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host=host
        self.channels=[]
        layout=QVBoxLayout(self)
        label=QLabel('Kanäle verwalten'); layout.addWidget(label)
        self.action=QComboBox()
        for title,key in [('Kanal erstellen','create'),('Kanal umbenennen','rename'),('Kanal verschieben','move'),('Kanal / Kategorie löschen','delete')]:self.action.addItem(title,key)
        self.channel=QComboBox(); self.channel.setMinimumContentsLength(20)
        self.kind=QComboBox()
        for title,key in [('Textkanal','text'),('Sprachkanal','voice'),('Kategorie','category')]:self.kind.addItem(title,key)
        self.channel_name=QLineEdit(); self.channel_name.setPlaceholderText('Kanalname / neuer Name'); self.channel_name.setMaxLength(100)
        self.parent=QComboBox(); self.parent.addItem('Ohne Kategorie',None)
        self.reason=QLineEdit(); self.reason.setPlaceholderText('Grund für das Discord-Protokoll');self.reason.setMaxLength(200)
        for widget in (self.action,self.channel,self.kind,self.channel_name,self.parent,self.reason):layout.addWidget(widget)
        self.delete_note=QLabel('Endgültige Löschung nur nach Vorschau und Kanal-ID-Bestätigung. Der Bot benötigt Kanäle verwalten. Beim Löschen einer Kategorie bleiben ihre Kanäle erhalten.');self.delete_note.setWordWrap(True);layout.addWidget(self.delete_note)
        self.preview=QPushButton('Änderung prüfen'); self.preview.clicked.connect(self.review);layout.addWidget(self.preview)
        self.result=QLabel('Zuerst die Serverübersicht laden.');self.result.setWordWrap(True);self.result.setTextFormat(Qt.PlainText);layout.addWidget(self.result)
        self.action.currentIndexChanged.connect(self.update_fields)
        self.kind.currentIndexChanged.connect(self.update_fields)
        self.channel.currentIndexChanged.connect(self.fill_name)
        self.update_fields()

    def update_fields(self,*_):
        action=self.action.currentData()
        self.delete_note.setVisible(action=='delete')
        self.channel.setVisible(action!='create')
        self.kind.setVisible(action=='create')
        self.channel_name.setVisible(action in ('create','rename'))
        self.parent.setVisible(action=='move' or (action=='create' and self.kind.currentData()!='category'))
        self.preview.setText('Löschung prüfen' if action=='delete' else 'Änderung prüfen');self.preview.setObjectName('danger' if action=='delete' else '')
        self.preview.style().unpolish(self.preview);self.preview.style().polish(self.preview)
        self.fill_name()

    def fill_name(self,*_):
        if self.action.currentData()=='rename':
            channel=next((x for x in self.channels if x['id']==self.channel.currentData()),None)
            if channel:self.channel_name.setText(channel['name'])

    def populate(self, channels):
        self.channels=channels
        selected=self.channel.currentData(); parent=self.parent.currentData()
        self.channel.clear();self.parent.clear();self.parent.addItem('Ohne Kategorie',None)
        for c in channels:
            kind={0:'Text',2:'Sprache',4:'Kategorie',5:'Ankündigung',13:'Stage',15:'Forum',16:'Medien'}.get(c.get('type'),'Kanal')
            self.channel.addItem(f"[{kind}] {c['name']} • {c['id']}",c['id'])
            if c.get('type')==4:self.parent.addItem(f"{c['name']} • {c['id']}",c['id'])
        if self.channel.findData(selected)>=0:self.channel.setCurrentIndex(self.channel.findData(selected))
        if self.parent.findData(parent)>=0:self.parent.setCurrentIndex(self.parent.findData(parent))

    def review(self):
        if self.host.discord_worker is not None:return
        client=self.host.discord_client
        if client is None:
            self.result.setText('Bitte zuerst die Discord-Verbindung prüfen.');return
        action=self.action.currentData()
        spec={'action':action,'channel':self.channel.currentData(),'name':self.channel_name.text().strip(),'kind':self.kind.currentData(),'parent':self.parent.currentData(),'reason':self.reason.text().strip()}
        if action=='create' and spec['kind']=='category':spec['parent']=None
        if action=='delete':spec['parent']=None;spec['name']=''
        if not spec['reason']:
            self.result.setText('Bitte einen Grund für die Änderung eingeben.');return
        self.result.setText('Vorschau wird geprüft …')
        def reviewed(plan):
            target=self.parent.currentText() if spec['parent'] else 'Ohne Kategorie'
            old=plan['before']
            details=f"Server: {client.guild}\n"
            if action=='create':details+=f"Erstellen: {spec['name']} ({self.kind.currentText()})\nZiel: {target}"
            elif action=='rename':details+=f"Umbenennen: {old['name']} → {spec['name']}\nKanal-ID: {spec['channel']}"
            elif action=='move':details+=f"Verschieben: {old['name']}\nKanal-ID: {spec['channel']}\nBisherige Kategorie-ID: {old['parent_id'] or 'Keine'}\nZiel: {target}"
            details+=f"\nGrund: {spec['reason']}"
            if action=='delete':
                box=DeleteConfirmation(self,deletion_details(client.guild,spec,plan),spec['channel'])
                accepted=box.exec()==QDialog.Accepted and box.id_input.text()==spec['channel']
            else:
                box=QMessageBox(self);box.setWindowTitle('Discord-Änderung ausführen');box.setTextFormat(Qt.PlainText);box.setText(details);box.setStandardButtons(QMessageBox.Ok|QMessageBox.Cancel);box.setDefaultButton(QMessageBox.Cancel)
                box.button(QMessageBox.Ok).setText('Jetzt ausführen');box.button(QMessageBox.Cancel).setText('Abbrechen');accepted=box.exec()==QMessageBox.Ok
            if not accepted:
                self.result.setText('Abgebrochen. Keine Änderung gesendet.');return
            if self.host.discord_worker is not None or self.host.discord_client is not client:
                self.result.setText('Verbindung oder laufender Vorgang geändert. Danach erneut prüfen.');return
            self.result.setText('Änderung wird ausgeführt …')
            self.host.run_discord_job(lambda:execute(client,spec,plan),self.completed,self.failed)
        self.host.run_discord_job(lambda:prepare(client,spec),reviewed,self.failed)

    def failed(self, message):
        self.result.setText(message+' Bei einem Verbindungsfehler während der Ausführung zuerst die Serverübersicht aktualisieren, bevor du erneut ausführst.')

    def completed(self, data):
        text=f"Discord hat die Änderung bestätigt. Kanal-ID: {data.get('id','—')}"
        if data.get('audit_warning'):text+='\n'+data['audit_warning']
        self.result.setText(text)
        self.host.refresh_discord()
