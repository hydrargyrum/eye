# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Editor annotations from builders

This plugin will add annotations to open editors when a builder emits a warning or an error.
When a builder starts, it clears annotations of all open editors of files under the working directory of the builder.

The global styles `"builder/warning"` and `"builder/error"` are used for annotations. The styles are accessed with
:any:`eye.helpers.styles`.
"""

import os

from ..connector import registerSignal, categoryObjects, disabled
from ..pathutils import isIn
from .buffers import findEditor
from .styles import STYLES


__all__ = ('setEnabled',)


def editorsForProject(path):
	path = os.path.dirname(path)
	for ed in categoryObjects('editor'):
		if isIn(ed.path, path):
			yield ed


@registerSignal('builder', 'started')
@disabled
def onBuildStart(builder):
	for ed in editorsForProject(builder.workingDirectory()):
		ed.clearAnnotations()


@registerSignal('builder', 'warningPrinted')
@disabled
def onBuildWarning(builder, info):
	annotate(builder, info, 'warning')


@registerSignal('builder', 'errorPrinted')
@disabled
def onBuildError(builder, info):
	annotate(builder, info, 'error')


def annotate(builder, info, msg_type):
	ed = findEditor(info['path'])
	if ed is None:
		return

	style = STYLES['builder/%s' % msg_type]
	ed.annotateAppendLine(info['line'] - 1, info['message'], style)


def setEnabled(enabled=True):
	"""Enable or disable the plugin"""
	onBuildStart.enabled = enabled
	onBuildError.enabled = enabled
	onBuildWarning.enabled = enabled
