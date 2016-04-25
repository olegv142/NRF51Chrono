import os, sys, time, subprocess, traceback, codecs, PyQt4
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
res_enc = 'utf-8-sig'
res_eol = '\r\n'

log_file = None
res_file = None

gui = None

def format_date_time_(t):
	return time.strftime('%d/%m/%y\t%H:%M:%S', time.localtime(t))

def format_date_time():
	return format_date_time_(time.time())

def format_timestamp():
	t = time.time()
	return format_date_time_(t) + ('.%03d ' % int(1000*(t%1)))

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

def warn(fmt, args = None):
	msg = format_msg('Warning: ', fmt, args)
	if gui is not None:
		gui.show_status(msg, QtCore.Qt.magenta)
	print(format_timestamp() + msg, file=log_file)

def dbg(pref, fmt, args = None):
	msg = format_msg(pref, fmt, args)
	print(format_timestamp() + msg, file=log_file)

def setWidgetBkgColor(w, c):
	p = w.palette()
	p.setColor(w.backgroundRole(), c)
	w.setPalette(p)

def setWidgetFogColor(w, c):
	p = w.palette()
	p.setColor(w.foregroundRole(), c)
	w.setPalette(p)

class Lane:
	# states
	Inactive  = 0
	Ready     = 1
	Starting  = 2
	Running   = 3
	Completed = 4
	Failed    = 5
	state_names = {
		Inactive  : 'Inactive',
		Ready     : 'Ready',
		Starting  : 'Starting',
		Running   : 'Running',
		Completed : 'Completed',
		Failed    : 'Failed'
	}

	def __init__(self, i):
		self.i = i
		self.result = 0.
		self.state = Lane.Inactive

	def set_state(self, st):
		dbg('[%d] ' % self.i, '%s -> %s', (Lane.state_names[self.state], Lane.state_names[st]))
		self.state = st

	def update(self, ts, stat):
		pass

	def update_result(self, res):
		self.result = res

	def start(self):
		pass

	def busy(self):
		return self.state == Lane.Starting or self.state == Lane.Running

	def stop(self):
		pass

	def reset(self):
		pass

class Kronoz:
	# states
	Idle      = 0
	Running   = 1
	Completed = 2
	Failed    = 3
	state_names = {
		Idle      : 'Idle',
		Running   : 'Running',
		Completed : 'Completed',
		Failed    : 'Failed'
	}

	def __init__(self):
		self.state = Kronoz.Idle

	def set_state(self, st):
		dbg('[K] ', '%s -> %s', (Kronoz.state_names[self.state], Kronoz.state_names[st]))
		self.state = st

	def get_lanes(self):
		return []

	def start(self):
		if self.state != Kronoz.Idle:
			return
		started = False
		for l in self.get_lanes():
			l.start()
			if l.busy():
				started = True
		if started:
			self.set_state(Kronoz.Running)

	def stop(self):
		if self.state != Kronoz.Running:
			return
		for l in self.get_lanes():
			l.stop()
		self.set_state(Kronoz.Completed)

	def reset(self):
		if self.state != Kronoz.Completed:
			return
		for l in self.get_lanes():
			l.reset()
		self.set_state(Kronoz.Idle)

	def update(self, ts, stats):
		if self.state == Kronoz.Failed:
			return
		lanes = self.get_lanes()
		running = False
		for i, stat in enumerate(stats):
			if i < len(lanes):
				l = lanes[i]
				l.update(ts, stat)
				if l.busy():
					running = True
		if self.state == Kronoz.Running and not running:
			self.set_state(Kronoz.Completed)

class GUILane(Lane, QWidget, lane_Widget):
	def __init__(self, i, gui):
		Lane.__init__(self, i)
		QWidget.__init__(self)
		lane_Widget.__init__(self)
		self.gui = gui
		self.setupUi(self)
		self.fStart.setAutoFillBackground(True)
		self.fFinish.setAutoFillBackground(True)
		setWidgetBkgColor(self.fStart, QtCore.Qt.green)
		setWidgetBkgColor(self.fFinish, QtCore.Qt.cyan)
		setWidgetFogColor(self.staVcc, QtCore.Qt.red)

class GUI(Kronoz, QWidget, gui_MainWindow):
	poll_interval = 200
	def __init__(self, nLanes = max_lanes):
		Kronoz.__init__(self)
		QWidget.__init__(self)
		gui_MainWindow.__init__(self)
		self.setupUi(self)
		self.sbar = QStatusBar(self)
		self.vlayout.addWidget(self.sbar)
		self.lanes = [GUILane(i, self) for i in range(nLanes)]
		for l in self.lanes:
			self.laneList.addWidget(l)
		self.timer = QTimer()
		self.timer.timeout.connect(self.poll_timer)
		self.timer.start(self.poll_interval)
		self.btSave.clicked.connect(self.save_results)
		self.btOpen.clicked.connect(self.open_res_file)
		self.btBrowse.clicked.connect(self.browse_res_folder)

	def get_lanes(self):
		return self.lanes

	def show_status(self, msg, color=QtCore.Qt.black):
		self.sbar.showMessage(msg)
		setWidgetFogColor(self.sbar, color)

	def save_results(self):
		t = format_date_time()
		for l in self.lanes:
			print(t + '\t' + str(l.i) + '\t' + l.leName.text() + '\t' + str(l.result) + res_eol, file=res_file)
		res_file.flush()

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

def setup_env():
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
		res_file = codecs.open(res_filename, 'a', res_enc)
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
	if setup_env():
		return -1
	app = QApplication(args_)
	app.setStyle(ui_style)
	gui = GUI(nLanes)
	gui.show()
	app.exec_()
	return 0

if __name__ == '__main__':
	sys.exit(main())
