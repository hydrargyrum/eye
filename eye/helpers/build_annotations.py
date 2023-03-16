# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Editor annotations from builders

This plugin will add annotations to open editors when a builder emits a warning or an error.
When a builder starts, it clears annotations of all open editors of files under the working directory of the builder.

The global styles `"builder/warning"` and `"builder/error"` are used for annotations. The styles are accessed with
:any:`eye.helpers.styles`.
"""

import os

from eye.connector import register_signal, category_objects, disabled
from eye.helpers.buffers import find_editor
from eye.helpers.styles import STYLES
from eye.pathutils import is_in

__all__ = ('set_enabled',)


def editors_for_project(path):
	path = os.path.dirname(path)
	for ed in category_objects('editor'):
		if is_in(ed.path, path):
			yield ed


@register_signal('builder', 'started')
@disabled
def on_build_start(builder):
	for ed in editors_for_project(builder.working_directory()):
		ed.clearAnnotations()


@register_signal('builder', 'warning_printed')
@disabled
def on_build_warning(builder, info):
	annotate(builder, info, 'warning')


@register_signal('builder', 'error_printed')
@disabled
def on_build_error(builder, info):
	annotate(builder, info, 'error')


def annotate(builder, info, msg_type):
	ed = find_editor(info['path'])
	if ed is None:
		return

	style = STYLES['builder/%s' % msg_type]
	ed.annotate_append_line(info['line'] - 1, info['message'], style)


def set_enabled(enabled=True):
	"""Enable or disable the plugin"""
	on_build_start.enabled = enabled
	on_build_error.enabled = enabled
	on_build_warning.enabled = enabled
