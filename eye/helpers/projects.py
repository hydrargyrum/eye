# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
Signal = pyqtSignal
Slot = pyqtSlot

import fnmatch
import os
from six.moves.configparser import RawConfigParser, NoOptionError, Error
from logging import getLogger
from weakref import WeakValueDictionary, ref
from six import StringIO

from ..connector import registerSignal, disabled
from ..utils import exceptionLogging
from .. import pathutils
from .. import lexers


__all__ = ('Project', 'findProjectForFile', 'getProjectForFile',
           'mergedOptionsForFile',
           'applyPreOptionsDict', 'applyOptionsDict',
           'onPreOpen', 'onOpenSave')

# uses .editorconfig format http://editorconfig.org/

# TODO: use inotify/whatever to monitor changes to project file
# TODO: add a signal so plugins know when to apply options
# TODO: cache per directory, and look up in the cache before searching project file
# TODO: use a negative cache? to avoid looking each time if no project

LOGGER = getLogger(__name__)
PROJECT_CACHE = WeakValueDictionary()
PROJECT_FILENAME = '.editorconfig'

class Project(QObject):
	def __init__(self):
		super(Project, self).__init__()
		self.dir = None
		self.cfgpath = None
		self.cfg = None
		self.parentProject = None

	def _parseFile(self, cfgpath):
		# add a starting section so it becomes INI format
		try:
			with open(cfgpath) as fp:
				contents = fp.read()
		except IOError:
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
		assert not self.cfgpath

		self.cfg = self._parseFile(cfgpath)
		if not self.cfg:
			return False

		self.dir = os.path.dirname(cfgpath)
		self.cfgpath = cfgpath
		LOGGER.debug('loaded config %r', self.cfgpath)

		try:
			opt = self.cfg.get('_ROOT_', 'root')
		except NoOptionError:
			isroot = True
		else:
			isroot = parseBool(opt, default=True)

		if not isroot:
			LOGGER.debug('searching parent project of %r', self.cfgpath)
			parent = os.path.dirname(self.dir)
			self.parentProject = findProjectForFile(parent)
		return True

	def _projectHierarchy(self):
		items = []
		current = self
		while current is not None:
			items.append(current)
			current = current.parentProject
		items.reverse()
		return items

	def _applySectionOptions(self, editor, section):
		dct = dict(self.cfg.items(section))
		applyOptionsDict(editor, dct)

	def _sectionsForFile(self, relpath):
		sections = []
		# TODO: use glob2re to support "**" and "{}"
		for section in self.cfg.sections():
			if fnmatch.filter([relpath, os.path.basename(relpath)], section):
				sections.append(section)
		sections.sort(key=len)

		if sections:
			LOGGER.debug('sections in %r apply for %r: %r', self.cfgpath, relpath, sections)
		else:
			LOGGER.debug('no sections in %r apply for %r', self.cfgpath, relpath)
		return sections

	def rootProject(self):
		current = self
		while current.parentProject is not None:
			current = current.parentProject
		return current

	def appliesTo(self, path):
		# TODO: support excludes
		return bool(pathutils.getCommonPrefix(self.dir, path))

	def pathRelativeToProject(self, path):
		return pathutils.getRelativePathIn(path, self.dir)

	def applyOptions(self, editor):
		options = mergedOptionsForFile(self, editor.path)
		if options:
			LOGGER.debug('applying options for editor %r', editor.path)
			applyOptionsDict(editor, options)
		else:
			LOGGER.debug('no options apply to editor %r', editor.path)

	def applyPreOptions(self, editor):
		options = mergedOptionsForFile(self, editor.path)
		if options:
			LOGGER.debug('applying pre-options for editor %r', editor.path)
			applyPreOptionsDict(editor, options)
		else:
			LOGGER.debug('no options apply to editor %r', editor.path)


TRUE_STRINGS = ['true', 'yes', 'on', '1']
FALSE_STRINGS = ['false', 'no', 'off', '0']

def parseBool(s, default=False):
	s = (s or '').lower()
	if s in TRUE_STRINGS:
		return True
	elif s in FALSE_STRINGS:
		return False
	else:
		return default


def mergedOptionsForFile(project, filepath):
	projects = project._projectHierarchy()
	options = {}
	for project in projects:
		relpath = project.pathRelativeToProject(filepath)
		for section in project._sectionsForFile(relpath):
			options.update(project.cfg.items(section))
	return options


def applyPreOptionsDict(editor, dct):
	val = dct.get('charset')
	if val is not None:
		try:
			''.encode(val)
		except LookupError:
			LOGGER.info('unknown charset: %r', val)
		else:
			editor.setEncoding(val)

	val = dct.get('insert_final_newline')
	if val == 'true':
		editor.setUseFinalNewline(True)
	elif val == 'false':
		editor.setUseFinalNewline(False)
	elif val is not None:
		LOGGER.info('unknown insert_final_newline: %r', val)


def applyOptionsDict(editor, dct):
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
		editor.setRemoveTrailingWhitespace(parseBool(val))

	k = 'eye.lexer_extension'
	if k in dct:
		lexer_type = lexers.extensionToLexer(dct[k])
		if lexer_type:
			editor.setLexer(lexer_type())


def findProjectForFile(path):
	return pathutils.findInAncestors(path, [PROJECT_FILENAME])


def getProjectForFile(path):
	found = findProjectForFile(path)
	if not found:
		LOGGER.debug('no project conf for %r', path)
		return

	project = PROJECT_CACHE.get(found)
	if project is not None:
		LOGGER.debug('found project %r in cache for %r', found, path)
	else:
		project = openProjectFile(found)
	if project is None:
		LOGGER.info('could not open project %r for %r', found, path)
		return

	if project.appliesTo(path):
		return project
	else:
		LOGGER.debug('project does not apply for %r', path)


def openProjectFile(filepath):
	LOGGER.info('loading project file %r', filepath)

	project = Project()
	if not project.load(filepath):
		return None
	PROJECT_CACHE[filepath] = project

	return project


@registerSignal('editor', 'fileAboutToBeOpened')
@disabled
def onPreOpen(editor, path):
	project = getProjectForFile(path)
	if not project:
		return

	editor.project = project
	project.applyPreOptions(editor)


@registerSignal('editor', 'fileOpened')
@registerSignal('editor', 'fileSavedAs')
@disabled
def onOpenSave(editor, path):
	project = getProjectForFile(path)
	if not project:
		return

	editor.project = project
	project.applyOptions(editor)
