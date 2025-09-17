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
from os.path import dirname, join
from locale import setlocale, LC_NUMERIC
from collections import namedtuple
from functools import partial
from mpv import MPV
from PyQt5 import uic
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QShortcut
from PyQt5.QtGui import QKeySequence
from qt_extras import SigBlock, ShutUpQT


__version__ = "1.0.0"

Range = namedtuple('Range', ['min', 'max', 'default', 'format'])
RANGES = {
	'contrast'	: Range(0.0, 2.0, 1.0, '{0:.2f}'),
	'brightness': Range(-0.5, 0.5, 0.0, '{0:.2f}'),
	'saturation': Range(0.0, 3.0, 1.0, '{0:.2f}'),
	'gamma'		: Range(0.1, 5.0, 1.0, '{0:.2f}')
}
SLIDER_MAX = 200

class Parameter:

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

	def __init__(self, options):
		super().__init__()
		with ShutUpQT():
			uic.loadUi(join(dirname(__file__), 'main_window.ui'), self)
		sc = QShortcut(QKeySequence('Ctrl+Q'), self)
		sc.activated.connect(self.close)
		sc = QShortcut(QKeySequence('ESC'), self)
		sc.activated.connect(self.close)

		self.frm_video.setAttribute(Qt.WA_DontCreateNativeAncestors)
		self.frm_video.setAttribute(Qt.WA_NativeWindow)
		wid = self.frm_video.winId()
		self.mpv = MPV(
			wid = str(int(self.frm_video.winId())),
			log_handler = print #, loglevel = 'debug'
		)
		self.b_play.toggled.connect(self.slot_play)
		self.mpv.observe_property('percent-pos', self.pos_change)

		self.parameters = { var: Parameter(var, rng) for var, rng in RANGES.items() }
		self.sliders = { var: getattr(self, 'sld_' + var) for var in RANGES }
		self.labels = { var: getattr(self, 'l_' + var) for var in RANGES }
		self.buttons = { var: getattr(self, 'b_' + var) for var in RANGES }

		for var, rng in RANGES.items():
			self.sliders[var].setMaximum(SLIDER_MAX)
			self.sliders[var].setValue(self.parameters[var].slider_value())
			self.labels[var].setText(self.parameters[var].label())
			self.buttons[var].clicked.connect(partial(self.slot_reset_var, var))
			self.sliders[var].valueChanged.connect(partial(self.slot_slider_value_changed, var))

		if options.Filename:
			self.mpv.play(options.Filename)

	def slot_slider_value_changed(self, var, value):
		self.parameters[var].set_from_slider_value(value)
		self.labels[var].setText(self.parameters[var].label())
		args = ['vf', 'set', 'eq=' + ':'.join(
			f'{p.var}={p.label()}' for p in self.parameters.values()
		)]
		logging.debug(args)
		self.mpv.command(*args)

	def slot_reset_var(self, var):
		self.parameters[var].value = RANGES[var].default
		self.sliders[var].setValue(self.parameters[var].slider_value())

	def pos_change(self, _, percent):
		if percent:
			with SigBlock(self.sld_position):
				self.sld_position.setValue(int(percent * 10))

	@pyqtSlot(bool)
	def slot_play(self, state):
		self.mpv.command("play" if state else "pause")
		self.b_play.setIcon(QIcon.fromTheme("media-playback-start" if state else "media-playback-pause"))



def main():
	"""
	Entry point, easy to reference from bin script.
	"""
	parser = argparse.ArgumentParser()
	parser.epilog = __doc__
	parser.add_argument('Filename', type = str, nargs = '?',
		help = 'Video file to setup for reencoding.')
	parser.add_argument("--verbose", "-v", action = "store_true",
		help = "Show more detailed debug information.")
	options = parser.parse_args()
	#log_level = logging.DEBUG if options.verbose else logging.ERROR
	log_level = logging.DEBUG
	log_format = "[%(filename)24s:%(lineno)4d] %(levelname)-8s %(message)s"
	logging.basicConfig(level = log_level, format = log_format)

	app = QApplication([])
	setlocale(LC_NUMERIC, 'C')
	main_window = MainWindow(options)
	main_window.show()
	sys.exit(app.exec())

if __name__ == "__main__":
	main()

#  end vid_filter_scripter/__init__.py
