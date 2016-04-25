import os
import sys
import PyQt4
from PyQt4 import QtCore, QtGui, uic
from PyQt4.QtGui import QStatusBar

application_path = os.path.split(sys.argv[0])[0]

gui_descr = "form.ui"
gui_descr_path = os.path.join(application_path, gui_descr)
gui_MainWindow, gui_BaseClass = uic.loadUiType(gui_descr_path)

lane_descr = "lane.ui"
lane_descr_path = os.path.join(application_path, lane_descr)
lane_Widget, lane_BaseClass = uic.loadUiType(lane_descr_path)

nLanes = 4

def setWidgetBkgColor(w, c):
	p = w.palette()
	p.setColor(w.backgroundRole(), c)
	w.setPalette(p)

def setWidgetFogColor(w, c):
	p = w.palette()
	p.setColor(w.foregroundRole(), c)
	w.setPalette(p)

class Lane(QtGui.QWidget, lane_Widget):
	def __init__(self):
		QtGui.QWidget.__init__(self)
		lane_Widget  .__init__(self)
		self.setupUi(self)
		self.fStart.setAutoFillBackground(True)
		self.fFinish.setAutoFillBackground(True)
		setWidgetBkgColor(self.fStart, QtCore.Qt.green)
		setWidgetBkgColor(self.fFinish, QtCore.Qt.cyan)
		setWidgetFogColor(self.staVcc, QtCore.Qt.red)

class GUI(QtGui.QWidget, gui_MainWindow):
	def __init__(self):
		QtGui.QWidget .__init__(self)
		gui_MainWindow.__init__(self)
		self.setupUi(self)
		self.sbar = QStatusBar(self)
		self.vlayout.addWidget(self.sbar)
		self.sbar.showMessage("ready")

app = QtGui.QApplication(sys.argv)
app.setStyle("plastique")
gui = GUI()
for _ in range(nLanes):
	gui.laneList.addWidget(Lane())
gui.show()
app.exec_()
