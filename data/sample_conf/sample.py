
# copy this file to ~/.config/eyeditor/startup/sample.py

## support .editorconfig

import eye.helpers.projects

eye.helpers.projects.set_enabled(True)


## load $XDG_CONFIG_HOME/eyeditor/keyboard.ini

from eye.helpers.keys import load_keys_config

load_keys_config()


## PositionIndicator in status bar

from eye.connector import default_window_config
from eye.widgets.misc import PositionIndicator

@default_window_config
def win_status_bar(win):
	bar = win.statusBar()
	bar.addPermanentWidget(PositionIndicator())


## enable syntax coloring

import eye.helpers.lexer
import eye.helpers.lexercolor
import eye.pathutils

eye.helpers.lexer.auto_lexer.enabled = True
eye.helpers.lexercolor.set_enabled(True)

eye.helpers.lexercolor.use_scheme_file(eye.pathutils.data_path('colorschemes/solarized-light.eyescheme'))


## dim-color for non-focused editors

import eye.helpers.focus_light

eye.helpers.focus_light.set_enabled(True)


## auto-completion (and more) with YCM (requires to install https://github.com/Valloric/ycmd)

import os

has_ycm = False

for path in os.environ['PATH'].split(os.pathsep):
	if os.path.exists(os.path.join(path, 'ycmd')):
		has_ycm = True

if has_ycm:
	from eye.helpers.actions import register_shortcut
	import eye.helpers.ycm as ycm

	ycm.set_enabled(True)

	@register_shortcut('editor', 'F6')
	def go_to_definition(ed):
		ycm.do_go_to(ed, 'GoToDefinition')

	@register_shortcut('editor', 'Ctrl+Space')
	def auto_complete(ed):
		ycm.do_completion(ed)


## misc editor configuration

from eye.connector import default_editor_config
from eye.widgets.editor import Marker

@default_editor_config
def search_config(ed):
	ed.search.highlight = True

@default_editor_config
def view_config(ed):
	ed.setEdgeColumn(80)
	ed.setEdgeMode(ed.EdgeLine)

@default_editor_config
def marker_config(ed):
	ed.margins['lines'].show()
	ed.create_marker('foo', Marker(ed.RightTriangle))

@default_editor_config
def selection_config(ed):
	ed.setMultipleSelection(True)
	ed.setMultiPaste(True)
	ed.set_additional_selection_typing(True)

@default_editor_config
def brace(ed):
	ed.setBraceMatching(ed.StrictBraceMatch)
	ed.setCaretLineVisible(True)

# uncomment if you prefer using 4 spaces everytime
#@defaultEditorConfig
#def indentConfig(ed):
#	ed.setIndentationsUseTabs(False)
#	ed.setIndentationWidth(4)


## monospace font

from PyQt5.QtGui import QFont
from eye.connector import default_editor_config, default_lexer_config

def set_font(target):
	font = QFont('DejaVu Sans mono')
	font.setPointSize(12)
	target.setFont(font)

@default_editor_config
def font_config(ed):
	set_font(ed)

@default_lexer_config
def fontConfigLexer(ed, lex):
	eye.helpers.lexercolor.lexer_set_font_family(lex, 'DejaVu Sans mono')
	eye.helpers.lexercolor.lexer_set_font_point_size(lex, 12)


## code navigation history

import eye.helpers.nav_history

eye.helpers.nav_history.set_enabled(True)


## tab bar corner button for splitting

import eye.widgets.tabs

eye.widgets.tabs.auto_create_corner_splitter.enabled = True


### have a python console when pressing F2 (which can operate on eye)

from eye.helpers.actions import register_shortcut
from eye.widgets.eval_console import EvalConsole
from eye.helpers.qt_all import Qt
from eye.pathutils import get_config_file_path

@register_shortcut('window', 'F2', Qt.WindowShortcut)
def popConsole(win):
	if not hasattr(win, 'console'):
		console = EvalConsole()
		console.line.setHistoryFile(get_config_file_path('eval_console.history'))
		win.console = win.add_dockable(Qt.BottomDockWidgetArea, console)
	win.console.show()
	win.console.widget().setFocus()

