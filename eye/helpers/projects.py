# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Plugin to support EditorConfig format

`EditorConfig <https://editorconfig.org/>`_ is a file format for configuring text editors for a project, like indent
style, encoding, etc. The format isn't tied to a particular text editor and is supported by many.

This sample should be enough for using editorconfig::

	import eye.helpers.projects
	eye.helpers.projects.onPreOpen.enabled = True
	eye.helpers.projects.onOpenSave.enabled = True
"""

from configparser import RawConfigParser, NoOptionError, Error
from io import StringIO
from logging import getLogger
import os
import re

from PyQt5.QtCore import QObject

from eye import pathutils, lexers
from eye.connector import register_signal, disabled, category_objects
from eye.helpers.confcache import ConfCache
from eye.qt import Slot
from eye.reutils import glob2re

__all__ = (
	'set_enabled',
	'Project', 'find_project_for_file', 'get_project_for_file',
	'merged_options_for_file',
	'apply_pre_options_dict', 'apply_options_dict',
	'on_pre_open', 'on_open_save',
)

# uses .editorconfig format https://editorconfig.org/

# TODO: use inotify/whatever to monitor changes to project file
# TODO: add a signal so plugins know when to apply options
# TODO: cache per directory, and look up in the cache before searching project file
# TODO: use a negative cache? to avoid looking each time if no project

LOGGER = getLogger(__name__)


PROJECT_FILENAME = '.editorconfig'


class Project(QObject):
	def __init__(self):
		super().__init__()
		self.dir = None
		self.cfgpath = None
		self.cfg = None
		self.sections_re = None
		self.parent_project = None

	def _parse_file(self, cfgpath):
		# add a starting section so it becomes INI format
		try:
			with open(cfgpath) as fp:
				contents = fp.read()
		except OSError:
			LOGGER.error('cannot read %r', cfgpath, exc_info=True)
			return None
		fp = StringIO('[_ROOT_]\n%s' % contents)

		cfg = RawConfigParser()
		try:
			cfg.readfp(fp, cfgpath)
		except Error:
			LOGGER.error('cannot parse %r', cfgpath, exc_info=True)
			return None

		return cfg

	def load(self, cfgpath):
		assert not self.cfgpath or cfgpath == self.cfgpath

		cfg = self._parse_file(cfgpath)
		if cfg is None:
			return False

		self.cfgpath = cfgpath
		self.cfg = cfg
		self.dir = os.path.dirname(cfgpath)
		self.parent_project = None

		self.sections_re = {}
		for section in self.cfg.sections():
			pattern = glob2re(section, double_star=True, sets=True, exact=True)
			LOGGER.debug('parsing section %r as %r', section, pattern)
			self.sections_re[section] = re.compile(pattern)

		LOGGER.debug('loaded config %r', self.cfgpath)

		try:
			opt = self.cfg.get('_ROOT_', 'root')
		except NoOptionError:
			isroot = True
		else:
			isroot = parse_bool(opt, default=True)

		if not isroot:
			LOGGER.debug('searching parent project of %r', self.cfgpath)
			parent = os.path.dirname(self.dir)
			self.parent_project = get_project_for_file(parent)
		return True

	def _project_hierarchy(self):
		items = []
		current = self
		while current is not None:
			items.append(current)
			current = current.parent_project
		items.reverse()
		return items

	def _apply_section_options(self, editor, section):
		dct = dict(self.cfg.items(section))
		apply_options_dict(editor, dct)

	def _sections_for_file(self, relpath):
		sections = []
		for section in self.cfg.sections():
			if self.sections_re[section].match(relpath) or self.sections_re[section].match(os.path.basename(relpath)):
				sections.append(section)
		sections.sort(key=len)

		if sections:
			LOGGER.debug('sections in %r apply for %r: %r', self.cfgpath, relpath, sections)
		else:
			LOGGER.debug('no sections in %r apply for %r', self.cfgpath, relpath)
		return sections

	def root_project(self):
		current = self
		while current.parent_project is not None:
			current = current.parent_project
		return current

	def is_ancestor_of(self, other):
		if self is other:
			return True
		elif other is None or other.isroot or other.parent_project is None:
			return False
		return self.is_ancestor_of(other.parent_project)

	def applies_to(self, path):
		# TODO: support excludes
		return bool(pathutils.get_common_prefix(self.dir, path))

	def path_relative_to_project(self, path):
		return pathutils.get_relative_path_in(path, self.dir)

	def apply_options(self, editor):
		options = merged_options_for_file(self, editor.path)
		if options:
			LOGGER.debug('applying options for editor %r', editor.path)
			apply_options_dict(editor, options)
		else:
			LOGGER.debug('no options apply to editor %r', editor.path)

	def apply_pre_options(self, editor):
		options = merged_options_for_file(self, editor.path)
		if options:
			LOGGER.debug('applying pre-options for editor %r', editor.path)
			apply_pre_options_dict(editor, options)
		else:
			LOGGER.debug('no options apply to editor %r', editor.path)


class ProjectCache(ConfCache):
	@Slot(str)
	def on_file_changed(self, path):
		"""Reload project and apply to editors"""
		project = self.cache.get(path)
		if project is None:
			return

		if not project.load(path):
			LOGGER.debug('could not reload project %r', path)
			return

		for editor in category_objects('editor'):
			if project.is_ancestor_of(getattr(editor, 'project', None)):
				LOGGER.debug('applying new project %r to editor %r', path, editor)

				if getattr(on_pre_open, 'enabled', True):
					on_pre_open(editor, editor.path)
				if getattr(on_open_save, 'enabled', True):
					on_open_save(editor, editor.path)


PROJECT_CACHE = ProjectCache()


TRUE_STRINGS = ['true', 'yes', 'on', '1']
FALSE_STRINGS = ['false', 'no', 'off', '0']


def parse_bool(s, default=False):
	"""Parse a string according to editorconfig and return a boolean value

	The recognized `True` values are "true", "yes", "on" and "1". The recognized `False` values are "false",
	"no", "off" and "0". The parsing is case insensitive. If `s` cannot be parsed, `default` is returned.
	"""
	s = (s or '').lower()
	if s in TRUE_STRINGS:
		return True
	elif s in FALSE_STRINGS:
		return False
	else:
		return default


def merged_options_for_file(project, filepath):
	projects = project._project_hierarchy()
	options = {}
	for project in projects:
		relpath = project.path_relative_to_project(filepath)
		for section in project._sections_for_file(relpath):
			options.update(project.cfg.items(section))
	return options


def apply_pre_options_dict(editor, dct):
	val = dct.get('charset')
	if val is not None:
		try:
			''.encode(val)
		except LookupError:
			LOGGER.info('unknown charset: %r', val)
		else:
			editor.set_encoding(val)

	val = dct.get('insert_final_newline')
	if val == 'true':
		editor.set_use_final_newline(True)
	elif val == 'false':
		editor.set_use_final_newline(False)
	elif val is not None:
		LOGGER.info('unknown insert_final_newline: %r', val)


def apply_options_dict(editor, dct):
	val = dct.get('indent_style')
	if val == 'space':
		editor.setIndentationsUseTabs(False)
	elif val == 'tab':
		editor.setIndentationsUseTabs(True)
	elif val is not None:
		LOGGER.info('unknown indent_style: %r', val)

	val = dct.get('indent_size')
	if val is not None:
		try:
			val = int(val)
		except ValueError:
			LOGGER.info('indent_size is not a number: %r', val)
		else:
			editor.setTabWidth(val)
			editor.setIndentationWidth(val)

	val = dct.get('end_of_line')
	if val == 'lf':
		editor.setEolMode(editor.SC_EOL_LF)
	elif val == 'cr':
		editor.setEolMode(editor.SC_EOL_CR)
	elif val == 'crlf':
		editor.setEolMode(editor.SC_EOL_CRLF)
	elif val is not None:
		LOGGER.info('unknown end_of_line: %r', val)

	val = dct.get('max_line_length')
	if val is not None:
		try:
			val = int(val)
		except ValueError:
			LOGGER.info('max_line_length is not a number: %r', val)
		else:
			editor.setEdgeColumn(val)

	val = dct.get('trim_trailing_whitespace')
	if val is not None:
		editor.set_remove_trailing_whitespace(parse_bool(val))

	k = 'eye.lexer_extension'
	if k in dct:
		lexer_type = lexers.extension_to_lexer(dct[k])
		if lexer_type:
			editor.setLexer(lexer_type())


def find_project_for_file(path):
	"""Find the nearest editorconfig file for a directory

	`path` can be any file or dir, `find_project_for_file` will search in the ancestors for a `.editorconfig` file.
	"""
	ret = pathutils.find_in_ancestors(path, [PROJECT_FILENAME])
	if ret is not None:
		return os.path.abspath(ret)


def get_project_for_file(path):
	"""Find and load an editorconfig for file

	`path` can be any file or dir, :any:`find_project_for_file` will search a `.editorconfig`, then this file will
	be loaded as a :any:`Project` and will be returned. If the `Project` was in cache, it will be returned
	directly.
	"""
	found = find_project_for_file(path)
	if not found:
		LOGGER.debug('no project conf for %r', path)
		return

	project = PROJECT_CACHE.get(found)
	if project is not None:
		LOGGER.debug('found project %r in cache for %r', found, path)
	else:
		project = open_project_file(found)
	if project is None:
		LOGGER.info('could not open project %r for %r', found, path)
		return

	if project.applies_to(path):
		return project
	else:
		LOGGER.debug('project does not apply for %r', path)


def open_project_file(filepath):
	"""Load and get a :any:`Project` object

	`filepath` is loaded as a editorconfig file and a :any:`Project` is returned.
	"""
	LOGGER.info('loading project file %r', filepath)

	project = Project()
	if not project.load(filepath):
		return None
	PROJECT_CACHE.add_conf(filepath, project)

	return project


@register_signal('editor', 'file_about_to_be_opened')
@disabled
def on_pre_open(editor, path):
	"""Handler when any file is about to be opened

	This handler will search a editorconfig for this editor widget, load it and apply options to the editor.
	"""

	project = get_project_for_file(path)
	if not project:
		return

	editor.project = project
	project.apply_pre_options(editor)


@register_signal('editor', 'file_opened')
@register_signal('editor', 'file_saved_as')
@disabled
def on_open_save(editor, path):
	"""Handler when any file is opened/saved

	This handler will search a editorconfig for this editor widget, load it and apply options to the editor.
	"""
	project = get_project_for_file(path)
	if not project:
		return

	editor.project = project
	project.apply_options(editor)


def set_enabled(enabled):
	"""Enable/disable the module

	When enabled, `.editorconfig` files are automatically applied when a file is loaded, or a file is
	saved in a tree where a `.editorconfig` is present.
	"""
	on_open_save.enabled = enabled
	on_pre_open.enabled = enabled
