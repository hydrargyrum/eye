
# copy this file to ~/.config/eyeditor/startup/sample.py

## support .editorconfig

import eye.helpers.projects

eye.helpers.projects.setEnabled(True)


## load $XDG_CONFIG_HOME/eyeditor/keyboard.ini

from eye.helpers.keys import loadKeysConfig

loadKeysConfig()


## PositionIndicator in status bar

from eye.connector import defaultWindowConfig
from eye.widgets.misc import PositionIndicator

@defaultWindowConfig
def winStatusBar(win):
	bar = win.statusBar()
	bar.addPermanentWidget(PositionIndicator())


## enable syntax coloring

import eye.helpers.lexer
import eye.helpers.lexercolor
import eye.pathutils

eye.helpers.lexer.autoLexer.enabled = True
eye.helpers.lexercolor.setEnabled(True)

eye.helpers.lexercolor.useSchemeFile(eye.pathutils.dataPath('colorschemes/solarized-light.eyescheme'))


## dim-color for non-focused editors

import eye.helpers.focus_light

eye.helpers.focus_light.setEnabled(True)


## auto-completion (and more) with YCM (requires to install https://github.com/Valloric/ycmd)

import os

has_ycm = False

for path in os.environ['PATH'].split(os.pathsep):
	if os.path.exists(os.path.join(path, 'ycmd')):
		has_ycm = True

if has_ycm:
	from eye.helpers.actions import registerShortcut
	import eye.helpers.ycm as ycm

	ycm.setEnabled(True)

	@registerShortcut('editor', 'F6')
	def go_to_definition(ed):
		ycm.doGoTo(ed, 'GoToDefinition')

	@registerShortcut('editor', 'Ctrl+Space')
	def auto_complete(ed):
		ycm.doCompletion(ed)


## misc editor configuration

from eye.connector import defaultEditorConfig
from eye.widgets.editor import Marker

@defaultEditorConfig
def searchConfig(ed):
	ed.search.highlight = True

@defaultEditorConfig
def viewConfig(ed):
	ed.setEdgeColumn(80)
	ed.setEdgeMode(ed.EdgeLine)

@defaultEditorConfig
def markerConfig(ed):
	ed.margins['lines'].show()
	ed.createMarker('foo', Marker(ed.RightTriangle))

@defaultEditorConfig
def selectionConfig(ed):
	ed.setMultipleSelection(True)
	ed.setMultiPaste(True)
	ed.setAdditionalSelectionTyping(True)

@defaultEditorConfig
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
from eye.connector import defaultEditorConfig, defaultLexerConfig

def setFont(target):
	font = QFont('DejaVu Sans mono')
	font.setPointSize(12)
	target.setFont(font)

@defaultEditorConfig
def fontConfig(ed):
	setFont(ed)

@defaultLexerConfig
def fontConfigLexer(ed, lex):
	eye.helpers.lexercolor.lexerSetFontFamily(lex, 'DejaVu Sans mono')
	eye.helpers.lexercolor.lexerSetFontPointSize(lex, 12)


## code navigation history

import eye.helpers.nav_history

eye.helpers.nav_history.setEnabled(True)


## tab bar corner button for splitting

import eye.widgets.tabs

eye.widgets.tabs.autoCreateCornerSplitter.enabled = True


### have a python console when pressing F2 (which can operate on eye)

from eye.helpers.actions import registerShortcut
from eye.widgets.eval_console import EvalConsole
from eye.helpers.qt_all import Qt
from eye.pathutils import getConfigFilePath

@registerShortcut('window', 'F2', Qt.WindowShortcut)
def popConsole(win):
	if not hasattr(win, 'console'):
		console = EvalConsole()
		console.line.setHistoryFile(getConfigFilePath('eval_console.history'))
		win.console = win.addDockable(Qt.BottomDockWidgetArea, console)
	win.console.show()
	win.console.widget().setFocus()

