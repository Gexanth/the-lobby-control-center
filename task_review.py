"""Editable local task review from an explicitly selected assistant passage."""
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QLineEdit,QTextEdit,QComboBox,QDialogButtonBox
from PySide6.QtCore import Qt
from storage import STATUSES


class TaskReview(QDialog):
    def __init__(self,parent,selection):
        super().__init__(parent);self.setWindowTitle('Vorschlag als Aufgabe vorbereiten');self.resize(620,480)
        layout=QVBoxLayout(self)
        hint=QLabel('Formuliere einen konkreten Auftrag. Speichern legt nur eine lokale Aufgabe an.');hint.setWordWrap(True);layout.addWidget(hint)
        layout.addWidget(QLabel('Auftrag'))
        self.title=QLineEdit(selection.splitlines()[0][:120]);self.title.setMaxLength(4000);layout.addWidget(self.title)
        layout.addWidget(QLabel('Details / ausgewählter Text – bearbeitbar'))
        self.notes=QTextEdit();self.notes.setAcceptRichText(False);self.notes.setPlainText(selection);layout.addWidget(self.notes)
        self.status=QComboBox();self.status.addItems(STATUSES);layout.addWidget(self.status)
        self.feedback=QLabel();self.feedback.setTextFormat(Qt.PlainText);layout.addWidget(self.feedback)
        self.buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);layout.addWidget(self.buttons)
        self.buttons.button(QDialogButtonBox.Save).setText('Aufgabe speichern')
        self.buttons.button(QDialogButtonBox.Cancel).setText('Abbrechen')
        self.buttons.accepted.connect(self.accept);self.buttons.rejected.connect(self.reject)
        self.title.textChanged.connect(self.validate);self.notes.textChanged.connect(self.validate);self.validate()

    def validate(self):
        valid=bool(self.title.text().strip()) and len(self.notes.toPlainText())<=8000
        self.buttons.button(QDialogButtonBox.Save).setEnabled(valid)
        self.feedback.setText('Auftrag fehlt oder Details überschreiten 8000 Zeichen.' if not valid else 'Vor dem Speichern kannst du Auftrag, Details und Status anpassen.')
        return valid

    def accept(self):
        if self.validate():super().accept()
