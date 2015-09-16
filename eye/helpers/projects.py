# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt4.QtCore import QObject, QFileSystemWatcher, pyqtSignal, pyqtSlot
Signal = pyqtSignal
Slot = pyqtSlot

import fnmatch
import os
from ConfigParser import RawConfigParser, NoOptionError
from logging import getLogger
from weakref import WeakValueDictionary, ref
from StringIO import StringIO

from ..connector import registerSignal, disabled
from ..utils import exceptionLogging
from .. import pathutils
from .. import lexers


__all__ = ('Project', 'findProjectForFile', 'getProjectForFile', 'onOpenSave',
           'mergedOptionsForFile', 'applyOptionsDict')

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
		QObject.__init__(self)
		self.dir = None
		self.cfgpath = None
		self.cfg = None
		self.parentProject = None

	def _parseFile(self, cfgpath):
		# add a starting section so it becomes INI format
		with open(cfgpath) as fp:
			contents = fp.read()
		fp = StringIO('[_ROOT_]\n%s' % contents)

		cfg = RawConfigParser()
		with exceptionLogging(logger=LOGGER):
			cfg.readfp(fp, cfgpath)

		return cfg

	def load(self, cfgpath):
		assert not self.cfgpath

		self.cfg = self._parseFile(cfgpath)
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
		return sections

	def appliesTo(self, path):
		# TODO: support excludes
		return bool(pathutils.getCommonPrefix(self.dir, path))

	def pathRelativeToProject(self, path):
		return pathutils.getRelativePathIn(path, self.dir)

	def applyOptions(self, editor):
		options = mergedOptionsForFile(self, editor.path)
		applyOptionsDict(editor, options)


def parseBool(s, default=False):
	s = (s or '').lower()
	if s in ['true', 'yes', 'on', '1']:
		return True
	elif s in ['false', 'no', 'off', '0']:
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


def applyOptionsDict(editor, dct):
	val = dct.get('indent_style')
	if val == 'space':
		editor.setIndentationsUseTabs(False)
	elif val == 'tab':
		editor.setIndentationsUseTabs(True)
	elif val is not None:
		LOGGER.info('unknown indent_style: %r', val)

	val = dct.get('indent_size')
	try:
		val = int(val)
	except (ValueError, TypeError):
		LOGGER.info('indent_size is not a number:: %r', val)
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

	val = dct.get('insert_final_newline')
	if val == 'true':
		editor.saving.final_newline = False
	elif val == 'false':
		editor.saving.final_newline = False
	elif val is not None:
		LOGGER.info('unknown insert_final_newline: %r', val)

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
	project.load(filepath)
	PROJECT_CACHE[filepath] = project

	return project


@registerSignal('editor', 'fileOpened')
@registerSignal('editor', 'fileSavedAs')
@disabled
def onOpenSave(editor, path):
	project = getProjectForFile(path)
	if not project:
		return

	editor.project = project
	project.applyOptions(editor)
