#  vidfilter_scripter/vidfilter_scripter/__main__.py
#
#  Copyright 2026 Leon Dionne <ldionne@dridesign.sh.cn>
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
from locale import setlocale, LC_NUMERIC
from PyQt5.QtWidgets import QApplication
from qt_extras import exceptions_hook
from . import MainWindow, set_application_style


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
	log_level = logging.DEBUG if options.verbose else logging.ERROR
	log_format = "[%(filename)24s:%(lineno)4d] %(levelname)-8s %(message)s"
	logging.basicConfig(level = log_level, format = log_format)

	app = QApplication([])
	sys.excepthook = exceptions_hook
	set_application_style()
	setlocale(LC_NUMERIC, 'C')
	main_window = MainWindow(options.Filename)
	main_window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()


#  end vid_filter_scripter/__init__.py
