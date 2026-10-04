from copy import deepcopy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox
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
        before={key:channel.get(key) for key in ('id','name','type','parent_id')}
        if action=='rename':
            if channel['name']==name(spec['name']): raise ValueError('Der Kanal hat diesen Namen bereits.')
            plan=client.edit_channel(spec['channel'],channel_name=spec['name'],reason=reason,preview=True)
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
    return client._change(approved['method'],approved['path'],deepcopy(approved['payload']),approved['reason'],False)


class ChannelActions(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host=host
        self.channels=[]
        layout=QVBoxLayout(self)
        label=QLabel('Kanäle verwalten'); layout.addWidget(label)
        self.action=QComboBox()
        for title,key in [('Kanal erstellen','create'),('Kanal umbenennen','rename'),('Kanal verschieben','move')]:self.action.addItem(title,key)
        self.channel=QComboBox(); self.channel.setMinimumContentsLength(20)
        self.kind=QComboBox()
        for title,key in [('Textkanal','text'),('Sprachkanal','voice'),('Kategorie','category')]:self.kind.addItem(title,key)
        self.channel_name=QLineEdit(); self.channel_name.setPlaceholderText('Kanalname / neuer Name'); self.channel_name.setMaxLength(100)
        self.parent=QComboBox(); self.parent.addItem('Ohne Kategorie',None)
        self.reason=QLineEdit(); self.reason.setPlaceholderText('Grund für das Discord-Protokoll');self.reason.setMaxLength(200)
        for widget in (self.action,self.channel,self.kind,self.channel_name,self.parent,self.reason):layout.addWidget(widget)
        self.preview=QPushButton('Änderung prüfen'); self.preview.clicked.connect(self.review);layout.addWidget(self.preview)
        self.result=QLabel('Zuerst die Serverübersicht laden.');self.result.setWordWrap(True);self.result.setTextFormat(Qt.PlainText);layout.addWidget(self.result)
        self.action.currentIndexChanged.connect(self.update_fields)
        self.kind.currentIndexChanged.connect(self.update_fields)
        self.channel.currentIndexChanged.connect(self.fill_name)
        self.update_fields()

    def update_fields(self,*_):
        action=self.action.currentData()
        self.channel.setVisible(action!='create')
        self.kind.setVisible(action=='create')
        self.channel_name.setVisible(action!='move')
        self.parent.setVisible(action=='move' or (action=='create' and self.kind.currentData()!='category'))
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
            self.channel.addItem(f"{c['name']} • {c['id']}",c['id'])
            if c.get('type')==4:self.parent.addItem(f"{c['name']} • {c['id']}",c['id'])
        if self.channel.findData(selected)>=0:self.channel.setCurrentIndex(self.channel.findData(selected))
        if self.parent.findData(parent)>=0:self.parent.setCurrentIndex(self.parent.findData(parent))

    def review(self):
        client=self.host.discord_client
        if client is None:
            self.result.setText('Bitte zuerst die Discord-Verbindung prüfen.');return
        action=self.action.currentData()
        spec={'action':action,'channel':self.channel.currentData(),'name':self.channel_name.text().strip(),'kind':self.kind.currentData(),'parent':self.parent.currentData(),'reason':self.reason.text().strip()}
        if action=='create' and spec['kind']=='category':spec['parent']=None
        if not spec['reason']:
            self.result.setText('Bitte einen Grund für die Änderung eingeben.');return
        self.result.setText('Vorschau wird geprüft …')
        def reviewed(plan):
            target=self.parent.currentText() if spec['parent'] else 'Ohne Kategorie'
            old=plan['before']
            details=f"Server: {client.guild}\n"
            if action=='create':details+=f"Erstellen: {spec['name']} ({self.kind.currentText()})\nZiel: {target}"
            elif action=='rename':details+=f"Umbenennen: {old['name']} → {spec['name']}\nKanal-ID: {spec['channel']}"
            else:details+=f"Verschieben: {old['name']}\nKanal-ID: {spec['channel']}\nBisherige Kategorie-ID: {old['parent_id'] or 'Keine'}\nZiel: {target}"
            details+=f"\nGrund: {spec['reason']}"
            box=QMessageBox(self);box.setWindowTitle('Discord-Änderung ausführen');box.setTextFormat(Qt.PlainText);box.setText(details);box.setStandardButtons(QMessageBox.Ok|QMessageBox.Cancel);box.setDefaultButton(QMessageBox.Cancel)
            box.button(QMessageBox.Ok).setText('Jetzt ausführen');box.button(QMessageBox.Cancel).setText('Abbrechen')
            if box.exec()!=QMessageBox.Ok:
                self.result.setText('Abgebrochen. Keine Änderung gesendet.');return
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
