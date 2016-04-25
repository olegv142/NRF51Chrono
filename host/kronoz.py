import os, sys, time, subprocess, traceback, PyQt4
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

home_folder = os.environ['USERPROFILE'] + os.sep + 'kronoz'
log_filename = home_folder + os.sep + 'kronoz.log'
res_filename = home_folder + os.sep + 'kronoz.txt'

log_file = None
res_file = None

gui = None

def format_timestamp():
	t = time.time()
	return time.strftime('%d-%m-%y %H:%M:%S', time.localtime(t)) + ('.%03d ' % int(1000*(t%1)))

def format_msg(pref, fmt, args):
	if args:
		return pref + (fmt % args)
	else:
		return pref + fmt

def err(fmt, args = None):
	msg = format_msg('Error: ', fmt, args)
	if gui is not None:
		gui.show_status(msg, QtCore.Qt.red)
	print(format_timestamp() + msg, file=log_file)

def errx(fmt, args = None):
	msg = format_msg('Error: ', fmt, args)
	if gui is not None:
		gui.show_status(msg, QtCore.Qt.red)
	print(format_timestamp() + msg, file=log_file)
	traceback.print_exc(file=log_file)

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
		self.lanes = [Lane(i, self) for i in range(nLanes)]
		for l in self.lanes:
			self.laneList.addWidget(l)
		self.timer = QTimer()
		self.timer.timeout.connect(self.poll_timer)
		self.timer.start(self.poll_interval)
		self.btOpen.clicked.connect(self.open_res_file)
		self.btBrowse.clicked.connect(self.browse_res_folder)
		self.show_status('ready')

	def show_status(self, msg, color=QtCore.Qt.black):
		self.sbar.showMessage(msg)
		setWidgetFogColor(self.sbar, color)

	def open_res_file(self):
		try:
			subprocess.Popen([u'notepad.exe', res_filename])
		except:
			errx('failed to open %s', res_filename)

	def browse_res_folder(self):
		try:
			os.startfile(home_folder, 'explore')
		except:
			errx('failed to browse %s', home_folder)

	def poll_timer(self):
		pass

def prepare_env():
	global log_file, res_file
	try:
		os.mkdir(home_folder)
	except:
		pass
	try:
		log_file = open(log_filename, 'w')
	except:
		print('Failed to open log file ' + log_filename, file=sys.stderr)
		traceback.print_exc(file=sys.stderr)
		return -1
	try:
		res_file = open(res_filename, 'a')
	except:
		print('Failed to open results file ' + res_filename, file=sys.stderr)
		traceback.print_exc(file=sys.stderr)
		return -1
	return 0

def main():
	global gui
	args_ = []
	nLanes = 4
	for arg in sys.argv:
		if arg.startswith('-L'):
			nLanes = int(arg[2:])
		else:
			args_.append(arg)
	if prepare_env():
		return -1
	app = QApplication(args_)
	app.setStyle(ui_style)
	gui = GUI(nLanes)
	gui.show()
	app.exec_()
	return 0

if __name__ == '__main__':
	sys.exit(main())
