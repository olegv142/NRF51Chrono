import os, sys, PyQt4
from PyQt4 import QtCore, QtGui, uic
from PyQt4.QtGui import QApplication, QWidget, QStatusBar
from PyQt4.QtCore import QTimer

application_path = os.path.split(sys.argv[0])[0]

gui_descr = 'form.ui'
gui_descr_path = os.path.join(application_path, gui_descr)
gui_MainWindow, gui_BaseClass = uic.loadUiType(gui_descr_path)

lane_descr = 'lane.ui'
lane_descr_path = os.path.join(application_path, lane_descr)
lane_Widget, lane_BaseClass = uic.loadUiType(lane_descr_path)

ui_style = 'plastique'
max_lanes = 4

def setWidgetBkgColor(w, c):
	p = w.palette()
	p.setColor(w.backgroundRole(), c)
	w.setPalette(p)

def setWidgetFogColor(w, c):
	p = w.palette()
	p.setColor(w.foregroundRole(), c)
	w.setPalette(p)

class Lane(QWidget, lane_Widget):
	def __init__(self, i, gui):
		QWidget.__init__(self)
		lane_Widget.__init__(self)
		self.i = i
		self.gui = gui
		self.setupUi(self)
		self.fStart.setAutoFillBackground(True)
		self.fFinish.setAutoFillBackground(True)
		setWidgetBkgColor(self.fStart, QtCore.Qt.green)
		setWidgetBkgColor(self.fFinish, QtCore.Qt.cyan)
		setWidgetFogColor(self.staVcc, QtCore.Qt.red)

class GUI(QWidget, gui_MainWindow):
	poll_interval = 200
	def __init__(self, nLanes = max_lanes):
		QWidget .__init__(self)
		gui_MainWindow.__init__(self)
		self.setupUi(self)
		self.sbar = QStatusBar(self)
		self.vlayout.addWidget(self.sbar)
		self.sbar.showMessage('ready')
		self.lanes = [Lane(i, self) for i in range(nLanes)]
		for l in self.lanes:
			self.laneList.addWidget(l)
		self.timer = QTimer()
		self.timer.timeout.connect(self.poll_timer)
		self.timer.start(self.poll_interval)

	def poll_timer(self):
		print('.')

def main():
	args_ = []
	nLanes = 4
	for arg in sys.argv:
		if arg.startswith('-L'):
			nLanes = int(arg[2:])
		else:
			args_.append(arg)

	app = QApplication(args_)
	app.setStyle(ui_style)
	gui = GUI(nLanes)
	gui.show()
	app.exec_()
	return 0

if __name__ == '__main__':
	sys.exit(main())
