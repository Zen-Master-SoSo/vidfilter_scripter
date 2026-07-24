#  vid_filter_scripter/__init__.py
#
#  Copyright 2025 Leon Dionne <ldionne@dridesign.sh.cn>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
"""
An mpv front-end which creates a mencoder script with video adjustments.
"""
import sys, logging, argparse
from os.path import dirname, join, splitext
from locale import setlocale, LC_NUMERIC
from collections import namedtuple
from functools import partial
from mpv import MPV
from PyQt5 import uic
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTime, QTimer, QDir
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QFileDialog, QShortcut, QWidget
from PyQt5.QtGui import QKeySequence, QIcon
from qt_extras import SigBlock, ShutUpQT, exceptions_hook
from xdg_soso import XDGSetup

__version__ = "1.3.0"


Param = namedtuple('Param',	[	'min',	'max',	'default',	'format'])
PARAMS = {
		'contrast'	: Param(	0.0,	2.0,		1.0,	'{0:.2f}'),
		'brightness': Param(	-0.5,	0.5,		0.0,	'{0:.2f}'),
		'saturation': Param(	0.0,	3.0,		1.0,	'{0:.2f}'),
		'gamma'		: Param(	0.1,	5.0,		1.0,	'{0:.2f}')
}
SLIDER_MAX = 325
APP_PATH = dirname(__file__)


class VidfilterScripterSetup(XDGSetup):

	def __init__(self):
		super().__init__('vidfilter_scripter', 'Vidfilter Scripter')
		self._comment = "An mpv front-end which creates a mencoder script with video adjustments."
		self._application_icon = join(dirname(__file__), 'res', 'icon.svg')
		self._categories = ['AudioVideo', 'AudioVideoEditing', 'Video']
		self._keywords = ['Video', 'Settings', 'Brightness', 'Contrast', 'ffmpeg', 'mpv']


class Parameter:
	"""
	An abstraction of one of the filter parameters.
	"""

	def __init__(self, var, rng):
		self.var = var
		self.value = rng.default
		self.range = rng.max - rng.min
		self.scale = SLIDER_MAX / self.range
		self.offset = rng.min * self.scale
		self.format = rng.format

	def slider_value(self):
		return round(self.value * self.scale - self.offset)

	def set_from_slider_value(self, value):
		self.value = (value + self.offset) / self.scale

	def label(self):
		return self.format.format(self.value)


class MainWindow(QMainWindow):
	"""
	Main interface, hosting MPV instance.
	"""

	def __init__(self, filename):
		super().__init__()
		with ShutUpQT():
			uic.loadUi(join(APP_PATH, 'res', 'main_window.ui'), self)
		self.filename = filename

		sc = QShortcut(QKeySequence('Ctrl+Q'), self)
		sc.activated.connect(self.close)
		sc = QShortcut(QKeySequence('ESC'), self)
		sc.activated.connect(self.close)
		sc = QShortcut(QKeySequence('F5'), self)
		sc.activated.connect(set_application_style)
		sc = QShortcut(QKeySequence('SPACE'), self)
		sc.activated.connect(self.toggle_play)
		sc = QShortcut(QKeySequence('RIGHT'), self)
		sc.activated.connect(self.nudge_forwards)
		sc = QShortcut(QKeySequence('LEFT'), self)
		sc.activated.connect(self.nudge_backwards)

		self.mouse_controls_position = False

		self.frm_video.setAttribute(Qt.WA_DontCreateNativeAncestors)
		self.frm_video.setAttribute(Qt.WA_NativeWindow)
		self.mpv = MPV(
			wid = int(self.frm_video.winId()),
			log_handler = print,
			loglevel = 'fatal'
		)

		self.parameters = { var: Parameter(var, rng) for var, rng in PARAMS.items() }
		self.sliders = { var: getattr(self, 'sld_' + var) for var in PARAMS }
		self.labels = { var: getattr(self, 'l_' + var) for var in PARAMS }
		self.buttons = { var: getattr(self, 'b_' + var) for var in PARAMS }

		app_path = dirname(__file__)
		for var, rng in PARAMS.items():
			self.sliders[var].setMaximum(SLIDER_MAX)
			self.sliders[var].setValue(self.parameters[var].slider_value())
			self.labels[var].setText(self.parameters[var].label())
			self.buttons[var].setIcon(QIcon(join(app_path, 'res', f'{var}.svg')))
			self.buttons[var].clicked.connect(partial(self.slot_reset_var, var))
			self.sliders[var].valueChanged.connect(partial(self.slot_slider_value_changed, var))

		self.b_play.toggled.connect(self.slot_play)
		self.b_okay.clicked.connect(self.slot_create_script)

		self.video_duration = None
		self.percent_pos = None
		self.mpv.observe_property('percent-pos', self.player_pos_change)
		self.mpv.observe_property('duration', self.player_duration_change)
		self.sld_position.sliderPressed.connect(self.slot_pos_press)
		self.sld_position.sliderReleased.connect(self.slot_pos_release)
		self.sld_position.sliderMoved.connect(self.slot_pos_moved)
		self.sld_position.setTracking(True)

		QTimer.singleShot(0, self.layout_complete)

	@pyqtSlot()
	def layout_complete(self):
		if not self.filename:
			self.filename, _ = QFileDialog.getOpenFileName(self,
				"Open a video file", QDir.homePath())
		if self.filename:
			self.mpv.play(self.filename)
		else:
			self.close()

	@pyqtSlot()
	def slot_pos_press(self):
		"""
		Triggered by the user pressing mouse on the position slider.
		"""
		self.mouse_controls_position = True

	@pyqtSlot()
	def slot_pos_release(self):
		"""
		Triggered by the user releasing the mouse from the position slider.
		"""
		self.mouse_controls_position = False

	@pyqtSlot(int)
	def slot_pos_moved(self, value):
		"""
		Responds to the user moving the mouse while pressed over the position slider.
		"""
		self.mpv.command('set', 'percent-pos', str(value / 10))

	def nudge_forwards(self):
		"""
		Triggered by the user pressing the "cursor right" key
		"""
		value = self.percent_pos + 5.0
		if value < 100.0:
			self.mpv.command('set', 'percent-pos', value)

	def nudge_backwards(self):
		"""
		Triggered by the user pressing the "cursor left" key
		"""
		value = self.percent_pos - 5.0
		if value > 0.0:
			self.mpv.command('set', 'percent-pos', value)

	def player_pos_change(self, _, percent):
		"""
		Responds to position change reported by MPV
		"""
		self.percent_pos = percent
		if self.mouse_controls_position or percent is None:
			return
		with SigBlock(self.sld_position):
			self.sld_position.setValue(int(percent * 10))

	def player_duration_change(self, _, duration):
		"""
		Responds to MPV reporting the duration of the loaded video.
		"""
		self.video_duration = round(duration) if duration else None

	def slot_slider_value_changed(self, var, value):
		self.parameters[var].set_from_slider_value(value)
		self.labels[var].setText(self.parameters[var].label())
		args = ['vf', 'set', self.eq_filter()]
		self.mpv.command(*args)

	def slot_reset_var(self, var):
		self.parameters[var].value = PARAMS[var].default
		self.sliders[var].setValue(self.parameters[var].slider_value())

	def toggle_play(self):
		"""
		Toggles play/pause depending on the state of the play button.
		"""
		self.b_play.click()

	@pyqtSlot(bool)
	def slot_play(self, state):
		self.mpv.command('set', 'pause', 'yes' if state else 'no')
		self.b_play.setIcon(QIcon.fromTheme("media-playback-start" if state else "media-playback-pause"))

	def slot_create_script(self):
		self.b_play.setChecked(True)
		dlg = MakeDialog(self)
		dlg.exec()

	def eq_filter(self):
		return 'eq=' + ':'.join(f'{p.var}={p.label()}' for p in self.parameters.values())

	# pylint: disable-next = invalid-name
	def closeEvent(self, _):
		self.mpv.terminate()


class MakeDialog(QDialog):
	"""
	Popup dialog which displays and saves the finished bash/ffmpeg script.
	"""

	def __init__(self, parent):
		super().__init__(parent)
		with ShutUpQT():
			uic.loadUi(join(APP_PATH, 'res', 'make_dialog.ui'), self)
		sc = QShortcut(QKeySequence('ESC'), self)
		sc.activated.connect(self.close)
		self.spn_length.setMaximum(min(240, self.parent().video_duration))
		start_max = self.parent().video_duration - 30
		self.te_start.setMaximumTime(QTime(0, start_max // 60, start_max % 60))
		start = min(start_max, self.parent().video_duration // 4, 5 * 60)
		self.te_start.setTime(QTime(0, start // 60, start % 60))
		self.cmb_height.addItems(['360p', '480p', '640p', '720p', '1080p'])
		self.cmb_height.setCurrentText('640p')
		self.chk_test.toggled.connect(self.slot_test_mode_changed)
		self.cmb_height.currentTextChanged.connect(self.slot_height_changed)
		self.te_start.timeChanged.connect(self.start_time_changed)
		self.spn_length.valueChanged.connect(self.test_len_changed)
		self.b_copy.clicked.connect(self.slot_copy)
		self.b_save.clicked.connect(self.slot_save)
		self.generate_script()

	@pyqtSlot(str)
	def slot_height_changed(self, _):
		self.generate_script()

	@pyqtSlot(QTime)
	def start_time_changed(self, _):
		self.generate_script()

	@pyqtSlot(int)
	def test_len_changed(self, _):
		self.generate_script()

	@pyqtSlot(bool)
	def slot_test_mode_changed(self, state):
		self.lbl2.setEnabled(state)
		self.lbl3.setEnabled(state)
		self.te_start.setEnabled(state)
		self.spn_length.setEnabled(state)
		self.generate_script()

	def generate_script(self):
		infile = self.parent().filename

		height = self.cmb_height.currentText()
		if height == '1080p':
			video_settings = '-b:v 2100k -maxrate 2650k -bufsize 2048k'
		elif height == '720p':
			video_settings = '-b:v 1500k -maxrate 1900k -bufsize 2048k'
		elif height == '640p':
			video_settings = '-b:v 1200k -maxrate 1500k -bufsize 2048k'
		elif height == '480p':
			video_settings = '-b:v 675k -maxrate 840k -bufsize 1024k'
		else:
			video_settings = '-vprofile baseline -b:v 300k -maxrate 375k -bufsize 512k'

		path, _ = splitext(infile)
		outfile = f'{path}-{height}.mp4'
		height = height.rstrip('p')
		video_filter = f'-vf scale=-2:{height},' + self.parent().eq_filter()

		time_opt = None
		if self.chk_test.isChecked():
			ss = self.te_start.time()
			time_opt = f'-ss {ss.minute():d}:{ss.second():02d} -t {self.spn_length.value()}'

		front_opts = [
			'ffmpeg -hide_banner -nostats -loglevel error',
			f'-i "{infile}"'
		]
		if time_opt:
			front_opts.append(time_opt)
		back_opts = [
			'-map_metadata -1',
			'-c:v libx264 -preset slow -tune film',
			'-c:a aac -ab 96k -ac 2',
			video_settings,
			video_filter,
			'-f mp4 -movflags faststart -strict -2'
		]

		first_pass_text = " \\\n\t".join(front_opts + ['-pass 1'] + back_opts + ['-y /dev/null'])
		second_pass_text = " \\\n\t".join(front_opts + ['-pass 2'] + back_opts + [f'-y "{outfile}"'])

		self.te_script.setPlainText("\n".join([
			'echo -n "First pass: " ; date',
			'',
			first_pass_text,
			'',
			'echo -n "Second pass: " ; date',
			'',
			second_pass_text,
			'',
			'echo -n "Finshed: " ; date',
			f'echo "Wrote \\"{outfile}\\""'
		]))

	@pyqtSlot()
	def slot_copy(self):
		QApplication.instance().clipboard().setText(self.te_script.toPlainText())

	@pyqtSlot()
	def slot_save(self):
		filename, _ = QFileDialog.getSaveFileName(
			self,
			"Export script ...",
			join(QDir.homePath(), 'reencode.sh'),
			"Bash script (*.sh)"
		)
		if filename:
			with open(filename, 'w', encoding = 'utf-8') as fob:
				fob.write(self.te_script.toPlainText())


def set_application_style():
	with open(join(APP_PATH, 'res', 'style.css'), 'r', encoding = 'utf-8') as cssfile:
		QApplication.instance().setStyleSheet(cssfile.read())


#  end vid_filter_scripter/__init__.py
