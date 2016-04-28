import os, sys, time, subprocess, traceback, serial, codecs, PyQt4
from serial.tools.list_ports import comports
from collections import namedtuple
from PyQt4 import QtCore, QtGui, uic
from PyQt4.QtGui import QApplication, QWidget, QShortcut, QKeySequence
from PyQt4.QtCore import QTimer

application_path = os.path.split(sys.argv[0])[0]

gui_descr = 'form.ui'
gui_descr_path = os.path.join(application_path, gui_descr)
gui_MainWindow, gui_BaseClass = uic.loadUiType(gui_descr_path)

lane_descr = 'lane.ui'
lane_descr_path = os.path.join(application_path, lane_descr)
lane_Widget, lane_BaseClass = uic.loadUiType(lane_descr_path)

ui_style = 'plastique'
gui = None

home_folder = os.environ['USERPROFILE'] + os.sep + 'kronoz'
log_filename = home_folder + os.sep + 'kronoz.log'
res_filename = home_folder + os.sep + 'kronoz.txt'
res_enc = 'utf-8-sig'
res_eol = '\r\n'

StatSet    = namedtuple('StatSet',    ('group', 'ts', 'gates'))
GateStat   = namedtuple('GateStat',   ('epoch', 'rep_total', 'rep_received', 'first_ts', 'last_ts', 'rep_sn', 'rep_ts', 'bt_pressed', 'pressed_ts', 'released_ts', 'vcc'))
GateStatus = namedtuple('GateStatus', ('pkt_receiption', 'vcc', 'online', 'pressed'))

#### Logging facilities ####

log_file = sys.stderr
log_trace_en = True

def format_date_time_(t):
	return time.strftime('%d/%m/%y\t%H:%M:%S', time.localtime(t))

def format_date_time():
	return format_date_time_(time.time())

def format_timestamp():
	t = time.time()
	return format_date_time_(t) + ('.%03d ' % int(1000*(t%1)))

def format_msg(pref, fmt, args):
	if args is not None:
		return pref + (fmt % args)
	else:
		return pref + fmt

def err(fmt, args = None):
	msg = format_msg('Error: ', fmt, args)
	if gui is not None:
		gui.show_message(msg, QtCore.Qt.red)
	print(format_timestamp() + msg, file=log_file)
	log_file.flush()

def errx(fmt, args = None):
	msg = format_msg('Error: ', fmt, args)
	if gui is not None:
		gui.show_message(msg, QtCore.Qt.red)
	print(format_timestamp() + msg, file=log_file)
	traceback.print_exc(file=log_file)
	log_file.flush()

def warn(fmt, args = None):
	msg = format_msg('Warning: ', fmt, args)
	if gui is not None:
		gui.show_message(msg, QtCore.Qt.magenta)
	print(format_timestamp() + msg, file=log_file)

def info(fmt, args = None):
	msg = format_msg('', fmt, args)
	if gui is not None:
		gui.show_message(msg, QtCore.Qt.black)
	print(format_timestamp() + msg, file=log_file)

def dbg(pref, fmt, args = None):
	msg = format_msg(pref, fmt, args)
	print(format_timestamp() + msg, file=log_file)

def trace(pref, fmt, args = None):
	if log_trace_en:
		dbg(pref, fmt, args)

def traced(f):
	def proxy(*args):
		trace(f.__name__, ' %s', (args,))
		r = f(*args)
		trace(f.__name__, ' -> %s', (r,))
	return proxy

#### Helper routines ####

log_file_size_limit = 4*1024*1024
log_file_rotate_group = 2

def rotate_logs(path):
	try:
		os.unlink('%s.%d' % (path, log_file_rotate_group))
	except:
		pass
	for i in range(log_file_rotate_group, 0, -1):
		old_path = '%s.%d' % (path, i - 1) if i > 1 else path
		new_path = '%s.%d' % (path, i)
		try:
			os.rename(old_path, new_path)
		except:
			pass

def open_log(path):
	try:
		out_file_sz = 0
		try:
			out_file_sz = os.stat(path).st_size
		except:
			pass
		if out_file_sz > log_file_size_limit:
			rotate_logs(path)
		return open(path, 'a')
	except:
		errx('Failed to open log file %s', path)
		return None

def setup_env():
	global log_file
	try:
		os.mkdir(home_folder)
	except:
		pass

	log_file = open_log(log_filename)
	if log_file is None:
		return False

	return True

def setWidgetBkgColor(w, c):
	p = w.palette()
	p.setColor(w.backgroundRole(), c)
	w.setPalette(p)

def setWidgetFogColor(w, c):
	p = w.palette()
	p.setColor(w.foregroundRole(), c)
	w.setPalette(p)

#### State machines ####

class Lane:
	# states
	Disconnected = 0
	Idle         = 1
	Ready        = 2
	Starting     = 3
	Running      = 4
	Completed    = 5
	Failed       = 6
	state_names = {
		Disconnected : 'Disconnected',
		Idle         : 'Idle',
		Ready        : 'Ready',
		Starting     : 'Starting',
		Running      : 'Running',
		Completed    : 'Completed',
		Failed       : 'Failed'
	}
	offline_tout = 3 * 1024 # 3 sec

	def __init__(self, i):
		self.i = i
		self.result = None
		self.state = Lane.Disconnected
		self.last_ts       = None
		self.idle_ts       = None
		self.start_ts      = None
		self.start_stat    = None
		self.finish_stat   = None
		self.start_status  = None
		self.finish_status = None

	def set_state(self, st):
		if self.state != st:
			if st == Lane.Completed:
				dbg('[%d] ' % self.i, '%s -> %s %.3f sec', (Lane.state_names[self.state], Lane.state_names[st], self.result))
			else:
				dbg('[%d] ' % self.i, '%s -> %s', (Lane.state_names[self.state], Lane.state_names[st]))
			self.state = st
		if st == Lane.Idle:
			self.update_result(0.)
			self.idle_ts = self.last_ts
		if (self.start_stat is not None and self.start_stat.epoch) or (self.finish_stat is not None and self.finish_stat.epoch):
			trace('[%d] ' % self.i, '%s ts=%s start: %s %s finish: %s %s',
				(Lane.state_names[st], self.last_ts, self.start_stat, self.start_status, self.finish_stat, self.finish_status))

	@staticmethod
	def gate_status(ts, stat):
		if not stat.epoch:
			return GateStatus(pkt_receiption = None, vcc = None, online = False, pressed = False)
		else:
			return GateStatus(pkt_receiption = float(stat.rep_received) / stat.rep_total, vcc = stat.vcc / 1000., online = (stat.last_ts + Lane.offline_tout > ts), pressed = stat.bt_pressed)

	@staticmethod
	def mils2sec(mils):
		return mils / 1024.

	@staticmethod
	def get_pressed_ts(stat):
		if stat.pressed_ts:
			return stat.last_ts - (stat.rep_ts - stat.pressed_ts)
		else:
			return 0

	@staticmethod
	def get_released_ts(stat):
		if stat.released_ts:
			return stat.last_ts - (stat.rep_ts - stat.released_ts)
		else:
			return 0

	def do_start(self):
		self.start_ts = Lane.get_released_ts(self.start_stat)
		self.set_state(Lane.Running if self.start_ts else Lane.Failed)

	def update(self, ts, start_stat, finish_stat):
		self.last_ts      = ts
		self.start_stat   = start_stat
		self.finish_stat  = finish_stat
		self.set_gates_status(Lane.gate_status(ts, start_stat), Lane.gate_status(ts, finish_stat))
		if self.state == Lane.Disconnected:
			self.set_state(Lane.Idle)
			return

		if self.state == Lane.Idle:
			if self.is_online():
				pressed_ts = Lane.get_pressed_ts(self.start_stat)
				if pressed_ts > self.idle_ts:
					self.set_state(Lane.Ready)
				return

		if self.state == Lane.Starting:
			if start_stat.bt_pressed:
				return
			self.do_start()

		if self.state == Lane.Running:
			finish_ts = Lane.get_pressed_ts(finish_stat)
			if finish_ts > self.start_ts:
				self.update_result(Lane.mils2sec(finish_ts - self.start_ts))
				self.set_state(Lane.Completed)
			else:
				self.update_result(Lane.mils2sec(finish_stat.last_ts - self.start_ts))

	def set_gates_status(self, start, finish):
		self.start_status  = start
		self.finish_status = finish

	def update_result(self, res):
		self.result = res

	def is_online(self):
		return self.start_status.online and self.finish_status.online

	def start(self):
		if self.state == Lane.Ready:
			if self.is_online():
				if self.start_stat.bt_pressed:
					self.set_state(Lane.Starting)
				else:
					self.do_start()
			else:
				self.set_state(Lane.Failed)

	def is_busy(self):
		return self.state == Lane.Starting or self.state == Lane.Running

	def stop(self):
		if not self.is_busy():
			return
		if self.state == Lane.Running:
			self.update_result(Lane.mils2sec(self.last_ts - self.start_ts))
		self.set_state(Lane.Completed)

	def reset(self):
		if self.state != Lane.Disconnected:
			self.set_state(Lane.Idle)

class Kronoz:
	# states
	Uninitialized = -1
	Disconnected  = 0
	Connecting    = 1
	Idle          = 2
	Ready         = 3
	Running       = 4
	Completed     = 5
	Failed        = 6
	state_names   = {
		Uninitialized : 'Uninitialized',
		Disconnected  : 'Disconnected',
		Connecting    : 'Connecting',
		Idle          : 'Idle',
		Ready         : 'Ready',
		Running       : 'Running',
		Completed     : 'Completed',
		Failed        : 'Failed'
	}

	def __init__(self):
		self.state = Kronoz.Uninitialized

	def set_state(self, st):
		if self.state != st:
			dbg('[K] ', '%s -> %s', (Kronoz.state_names[self.state], Kronoz.state_names[st]))
			self.state = st

	def get_lanes(self):
		return []

	@traced
	def start(self):
		if self.state != Kronoz.Ready:
			return
		started = False
		for l in self.get_lanes():
			l.start()
			if l.is_busy():
				started = True
		if started:
			self.set_state(Kronoz.Running)
		else:
			self.set_state(Kronoz.Completed)

	@traced
	def stop(self):
		if self.state != Kronoz.Running:
			return
		for l in self.get_lanes():
			l.stop()
		self.set_state(Kronoz.Completed)

	@traced
	def reset(self):
		if self.state != Kronoz.Completed:
			return
		for l in self.get_lanes():
			l.reset()
		self.set_state(Kronoz.Idle)

	def update(self, stat_set):
		if self.state == Kronoz.Failed:
			return
		if self.state == Kronoz.Connecting:
			self.set_state(Kronoz.Idle)
			info('connected to group #%u', stat_set.group)
		lanes = self.get_lanes()
		ready, running = False, False
		stats = stat_set.gates
		n = min(len(stats) // 2, len(lanes))
		for i in range(n):
			l = lanes[i]
			l.update(stat_set.ts, stats[2*i], stats[2*i+1])
			if l.is_busy():
				running = True
			if l.state == Lane.Ready:
				ready = True
		if self.state == Kronoz.Running and not running:
			self.set_state(Kronoz.Completed)
		if self.state == Kronoz.Idle and ready:
			self.set_state(Kronoz.Ready)

#### GUI implementation ####

class GUILane(Lane, QWidget, lane_Widget):
	def __init__(self, i):
		Lane.__init__(self, i)
		QWidget.__init__(self)
		lane_Widget.__init__(self)
		self.setupUi(self)
		self.fStart.setAutoFillBackground(True)
		self.fFinish.setAutoFillBackground(True)

	def set_state(self, st):
		old_st = self.state
		Lane.set_state(self, st)
		if st == old_st:
			return
		if st == Lane.Idle:
			setWidgetFogColor(self.lTime, QtCore.Qt.black)
		elif st == Lane.Failed:
			setWidgetFogColor(self.lTime, QtCore.Qt.red)
		elif st == Lane.Completed:
			setWidgetFogColor(self.lTime, QtCore.Qt.darkGreen)
		else: # Ready, Starting, Running
			setWidgetFogColor(self.lTime, QtCore.Qt.blue)

	@staticmethod
	def format_time(t):
		ti = int(t)
		return '%u:%02u.%02u' % (ti//60, ti%60, int(100*(t-ti)))

	def update_result(self, res):
		Lane.update_result(self, res)
		self.lTime.setText(GUILane.format_time(res))

	@staticmethod
	def get_alert_color(v, v0, v1):
		if v < v0:
			return QtCore.Qt.red
		elif v < v1:
			return QtCore.Qt.magenta
		else:
			return QtCore.Qt.black

	@staticmethod
	def show_gate_status(s, frame, pkt_stat, vcc, status):
		if s.pkt_receiption is not None:
			pkt_stat.setText('%u%%' % (100 * s.pkt_receiption))
			setWidgetFogColor(pkt_stat, GUILane.get_alert_color(s.pkt_receiption, .1, .5))
		if s.vcc is not None:
			vcc.setText('%.1fV' % s.vcc)
			setWidgetFogColor(vcc, GUILane.get_alert_color(s.vcc, 2.2, 2.7))
		if s.online:
			status.setText('online')
			setWidgetBkgColor(frame, QtCore.Qt.green if s.pressed else QtCore.Qt.cyan)
		else:				
			status.setText('offline')
			setWidgetBkgColor(frame, QtCore.Qt.lightGray)

	def set_gates_status(self, start, finish):
		Lane.set_gates_status(self, start, finish)
		GUILane.show_gate_status(start,  self.fStart,  self.staPktStat, self.staVcc, self.staStatus)
		GUILane.show_gate_status(finish, self.fFinish, self.finPktStat, self.finVcc, self.finStatus)


class GUI(Kronoz, QWidget, gui_MainWindow):
	poll_interval = 200
	def __init__(self, com, nLanes = 4):
		Kronoz.__init__(self)
		QWidget.__init__(self)
		gui_MainWindow.__init__(self)
		self.setupUi(self)
		self.lanes = [GUILane(i) for i in range(nLanes)]
		for l in self.lanes:
			self.laneList.addWidget(l)
		self.com = com
		self.btStart .clicked.connect(self.on_start)
		self.btStop  .clicked.connect(self.on_stop)
		self.btSave  .clicked.connect(self.save_results)
		self.btOpen  .clicked.connect(self.open_res_file)
		self.btBrowse.clicked.connect(self.browse_res_folder)
		self.shortcuts = (
			QShortcut(QKeySequence('1'), self.btStart,  self.btStart .click),
			QShortcut(QKeySequence('2'), self.btStop,   self.btStop  .click),
			QShortcut(QKeySequence('3'), self.btSave,   self.btSave  .click),
			QShortcut(QKeySequence('4'), self.btOpen,   self.btOpen  .click),
			QShortcut(QKeySequence('5'), self.btBrowse, self.btBrowse.click)
		)
		if com is not None:
			self.timer = QTimer()
			self.timer.timeout.connect(self.poll_timer)
			self.timer.start(self.poll_interval)
			self.set_state(Kronoz.Connecting)
		else:
			self.timer = None
			self.set_state(Kronoz.Disconnected)

	def get_lanes(self):
		return self.lanes

	@staticmethod
	def status_color(st):
		if st == Kronoz.Failed:
			return QtCore.Qt.red
		elif st == Kronoz.Disconnected:
			return QtCore.Qt.magenta
		else:
			return QtCore.Qt.black

	def set_state(self, st):
		old_st = self.state
		Kronoz.set_state(self, st)
		if st == old_st:
			return
		self.show_status(Kronoz.state_names[st], GUI.status_color(st))
		self.btStart.setEnabled(st == Kronoz.Ready)
		self.btStop .setEnabled(st == Kronoz.Running)
		self.btSave .setEnabled(st == Kronoz.Completed)
		if st == Kronoz.Failed:
			if self.timer is not None:
				self.timer.stop()
				self.timer = None

	@staticmethod
	def sbar_show_message(sb, msg, color):
		sb.showMessage(msg)
		setWidgetFogColor(sb, color)

	def show_status(self, msg, color=QtCore.Qt.black):
		GUI.sbar_show_message(self.sbar0, msg, color)

	def show_message(self, msg, color=QtCore.Qt.black):
		GUI.sbar_show_message(self.sbar1, msg, color)

	def on_start(self):
		self.start()

	def on_stop(self):
		self.stop()

	def save_results(self):
		try:
			res_file = codecs.open(res_filename, 'a', res_enc)
		except:
			errx('Failed to open results file %s', res_filename)
			return
		t = format_date_time()
		for l in self.lanes:
			if l.state == Lane.Completed:
				print(('%s\t%u\t%s\t%.3f' + res_eol) % (t, l.i, l.leName.text(), l.result), file=res_file)
		res_file.close()
		self.reset()

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
		if self.state == Kronoz.Failed:
			return
		s = read_stat(self.com)
		if s is None:
			self.set_state(Kronoz.Failed)
		else:
			self.update(s)

#### Controller interface ####

valid_controllers   = ['USB VID:PID=0403:6001', 'FTDIBUS\\VID_0403+PID_6001']
controller_baudrate = 115200
controller_timeout  = 1
controller_channels = 8

def find_port():
	for port, info, descr in comports():
		for c in valid_controllers:
			if descr.startswith(c):
				return port
	return None

def open_port(port):
	try:
		com = serial.Serial(port, timeout = controller_timeout, baudrate = controller_baudrate)
		if com.is_open:
			return com
		else:
			err('Failed to open', port)
			return None
	except:
		errx('Failed to open', port)
		return None

def read_stat(com):
	try:
		com.write(b's\r')
		prefix = com.read(6)
		if len(prefix) != 6 or prefix[0:1] != b'~':
			raise RuntimeError('invalid prefix: %s' % prefix)
		sz = int(prefix[1:5], base=16)
		resp = com.read(sz)
		if len(resp) != sz:
			raise RuntimeError('invalid response: %s' % resp)
		f = resp.split()
		ch_flds = 11
		if len(f) != 2 + controller_channels * ch_flds:
			raise RuntimeError('invalid response: %s' % resp)
		stat = StatSet(group = int(f[0]), ts = int(f[1]), gates=[])
		for ch in range(controller_channels):
			ch_f = f[2+ch*ch_flds:2+(ch+1)*ch_flds]
			stat.gates.append(GateStat(
				epoch=int(ch_f[0]), rep_total=int(ch_f[1]), rep_received=int(ch_f[2]), first_ts=int(ch_f[3]), last_ts=int(ch_f[4]),
				rep_sn=int(ch_f[5]), rep_ts=int(ch_f[6]), bt_pressed=int(ch_f[7]), pressed_ts=int(ch_f[8]), released_ts=int(ch_f[9]), vcc=int(ch_f[10])
			))
		return stat
	except:
		errx('Kronoz receiver failure')
		return None

#### Main function ####

def main():
	global gui
	args_ = []
	nLanes = 4
	for arg in sys.argv:
		if arg.startswith('-L'):
			nLanes = int(arg[2:])
		else:
			args_.append(arg)
	if not setup_env():
		return -1
	port = find_port()
	if not port:
		err('Kronoz receiver not found')
	info('Connecting to %s', port)
	com = open_port(port)
	app = QApplication(args_)
	app.setStyle(ui_style)
	gui = GUI(com, nLanes)
	gui.show()
	app.exec_()
	return 0

if __name__ == '__main__':
	sys.exit(main())
