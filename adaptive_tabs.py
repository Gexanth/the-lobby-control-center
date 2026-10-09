"""Keep inactive, tall forms from stretching the selected Community tab."""
from PySide6.QtWidgets import QTabWidget,QSizePolicy
from PySide6.QtCore import QSize


class AdaptiveTabs(QTabWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.currentChanged.connect(self.fit_current)

    def addTab(self,widget,label):
        index=super().addTab(widget,label)
        self.fit_current()
        return index

    def fit_current(self,*_):
        for i in range(self.count()):
            widget=self.widget(i)
            widget.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred if i==self.currentIndex() else QSizePolicy.Ignored)
        self.updateGeometry()

    def sizeHint(self):
        current=self.currentWidget()
        if current is None:return super().sizeHint()
        content=current.sizeHint();bar=self.tabBar().sizeHint()
        return QSize(max(content.width(),bar.width())+8,content.height()+bar.height()+8)
