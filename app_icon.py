"""Native vector branding, also exported as a Windows ICO at shortcut setup."""
import struct
from PySide6.QtCore import Qt,QByteArray,QBuffer,QIODevice
from PySide6.QtGui import QPixmap,QPainter,QColor,QFont,QIcon

APP_ID='TheLobby.ControlCenter'
def icon():
    pix=QPixmap(256,256);pix.fill(Qt.transparent)
    painter=QPainter(pix);painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen);painter.setBrush(QColor('#10141d'));painter.drawRoundedRect(4,4,248,248,52,52)
    painter.setBrush(QColor('#7966ff'));painter.drawRoundedRect(28,28,200,200,38,38)
    painter.setPen(QColor('white'));painter.setFont(QFont('Segoe UI',102,QFont.Bold))
    painter.drawText(pix.rect(),Qt.AlignCenter,'L');painter.end()
    return QIcon(pix)
def write_ico(path):
    data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.WriteOnly)
    icon().pixmap(256,256).save(buffer,'PNG');buffer.close();raw=bytes(data)
    path.write_bytes(struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',0,0,0,0,1,32,len(raw),22)+raw)
