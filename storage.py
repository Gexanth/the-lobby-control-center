import json
import os
import uuid
from datetime import datetime
from pathlib import Path

STATUSES = ('Vorgemerkt', 'In Arbeit', 'Erledigt')

class TaskStore:
    def __init__(self, path):
        self.path = Path(path)
        self.items = []
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data, list) or any(not isinstance(x, dict) or not isinstance(x.get('text'), str) for x in data):
                raise ValueError('Die Aufgabendatei hat ein ungültiges Format.')
            self.items = data
            for item in self.items:
                item.setdefault('id', str(uuid.uuid4()))
                item.setdefault('notes', '')
                item.setdefault('created', '')
                if item.get('status') not in STATUSES:
                    item['status'] = STATUSES[0]

    def commit(self, items):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temporary, self.path)
        self.items = items

    def add(self, text):
        item = dict(id=str(uuid.uuid4()), text=text, created=datetime.now().isoformat(timespec='minutes'), status=STATUSES[0], notes='')
        self.commit(self.items + [item])
        return item

    def update(self, task_id, status, notes):
        if status not in STATUSES:
            raise ValueError('Unbekannter Status')
        self.commit([dict(x, status=status, notes=notes) if x['id'] == task_id else x.copy() for x in self.items])

    def delete(self, task_id):
        self.commit([x.copy() for x in self.items if x['id'] != task_id])

    def handoff(self, task_id):
        item = next(x for x in self.items if x['id'] == task_id)
        return f"Projekt: The Lobby Control Center / Discord-Server The Lobby\nAuftrag: {item['text']}\nStatus: {item['status']}\nDetails: {item['notes'] or 'Keine zusätzlichen Details'}\n\nBitte bearbeite diesen Auftrag. Der Desktop-Auftrag wurde noch nicht automatisch ausgeführt."
