"""Editable local task review from an explicitly selected assistant passage."""
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QLineEdit,QTextEdit,QComboBox,QDialogButtonBox,QTabWidget,QWidget
from PySide6.QtCore import Qt
from storage import STATUSES


class TaskReview(QDialog):
    def __init__(self,parent,selection):
        super().__init__(parent);self.setWindowTitle('Vorschlag als Aufgabe vorbereiten');self.resize(620,480)
        layout=QVBoxLayout(self)
        hint=QLabel('Formuliere einen konkreten Auftrag. Speichern legt nur eine lokale Aufgabe an.');hint.setWordWrap(True);layout.addWidget(hint)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        editor=QWidget();form=QVBoxLayout(editor);self.tabs.addTab(editor,'Aufgabe bearbeiten')
        form.addWidget(QLabel('Auftrag'))
        self.title=QLineEdit(selection.splitlines()[0][:120]);self.title.setMaxLength(4000);form.addWidget(self.title)
        form.addWidget(QLabel('Details / ausgewählter Text – bearbeitbar'))
        self.notes=QTextEdit();self.notes.setAcceptRichText(False);self.notes.setPlainText(selection);form.addWidget(self.notes)
        self.status=QComboBox();self.status.addItems(STATUSES);form.addWidget(self.status)
        self.evidence=QTextEdit();self.evidence.setReadOnly(True);self.evidence.setPlainText('Keine eindeutig zugeordnete KI-Antwort. Bei einer Auswahl über mehrere Nachrichten werden keine Belege automatisch zugeordnet.');self.tabs.addTab(self.evidence,'Belege und Grenzen')
        self.feedback=QLabel();self.feedback.setTextFormat(Qt.PlainText);layout.addWidget(self.feedback)
        self.buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);layout.addWidget(self.buttons)
        self.buttons.button(QDialogButtonBox.Save).setText('Aufgabe speichern')
        self.buttons.button(QDialogButtonBox.Cancel).setText('Abbrechen')
        self.buttons.accepted.connect(self.accept);self.buttons.rejected.connect(self.reject)
        self.title.textChanged.connect(self.validate);self.notes.textChanged.connect(self.validate);self.validate()

    def set_evidence(self,text):
        self.evidence.setPlainText(text+'\n\nPrüfe vor dem Speichern: Passt die Quelle zur Aussage? Ist die Messung aktuell und ausreichend? Was ist der konkrete nächste Schritt?\nDie bearbeitbaren Details bestimmen, was in der Aufgabe gespeichert wird.')

    def validate(self):
        valid=bool(self.title.text().strip()) and len(self.notes.toPlainText())<=8000
        self.buttons.button(QDialogButtonBox.Save).setEnabled(valid)
        self.feedback.setText('Auftrag fehlt oder Details überschreiten 8000 Zeichen.' if not valid else 'Vor dem Speichern kannst du Auftrag, Details und Status anpassen.')
        return valid

    def accept(self):
        if self.validate():super().accept()
