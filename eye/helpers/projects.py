# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt4.QtCore import QObject, QFileSystemWatcher, pyqtSignal, pyqtSlot
Signal = pyqtSignal
Slot = pyqtSlot

import fnmatch
import os
from ConfigParser import RawConfigParser
from logging import getLogger
from weakref import WeakValueDictionary, ref

from ..connector import registerSignal, disabled
from ..utils import exceptionLogging
from .. import pathutils
from .. import lexers


__all__ = ('Project', 'findProjectForFile', 'getProjectForFile', 'onOpenSave')


# TODO: use inotify/whatever to monitor changes to project file
# TODO: add a signal so plugins know when to apply options
# TODO: cache per directory, and look up in the cache before searching project file
# TODO: use a negative cache? to avoid looking each time if no project

LOGGER = getLogger(__name__)
PROJECT_CACHE = WeakValueDictionary()
PROJECT_FILENAME = '.eyeproject.ini'

class Project(QObject):
	def __init__(self):
		QObject.__init__(self)
		self.root = self.cfgpath = self.cfg = None
		#self.monitor = None

	def load(self, cfgpath):
		assert not self.cfgpath

		cfg = RawConfigParser()
		with exceptionLogging(logger=LOGGER):
			cfg.read([cfgpath])
		self.cfg = cfg
		self.root = os.path.dirname(cfgpath)
		self.cfgpath = cfgpath

		#self.monitor = QFileSystemWatcher([path])
		#self.monitor.fileChanged.connect(self.onFileChanged)

	def _applySectionOptions(self, editor, section):
		dct = dict(self.cfg.items(section))
		applyOptionsDict(editor, dct)

	def _sectionsForFile(self, relpath):
		sections = []
		for section in self.cfg.sections():
			if fnmatch.filter([relpath, os.path.basename(relpath)], section):
				sections.append(section)
		sections.sort(key=len)
		return sections

	def appliesTo(self, path):
		# TODO: support excludes
		return bool(pathutils.getCommonPrefix(self.root, path))

	def pathRelativeToRoot(self, path):
		return pathutils.getRelativePathIn(path, self.root)

	def applyOptions(self, editor):
		fullpath = editor.path
		relpath = self.pathRelativeToRoot(fullpath)
		sections = self._sectionsForFile(relpath)

		LOGGER.debug('for %r, applying project %r sections %r', fullpath, self.cfgpath, sections)

		for section in sections:
			self._applySectionOptions(editor, section)


def applyOptionsDict(editor, dct):
	k = 'indent.tabs'
	if k in dct:
		b = bool(int(dct[k]))
		editor.setIndentationsUseTabs(b)
	k = 'indent.width'
	if k in dct:
		i = int(dct[k])
		editor.setTabWidth(i)
		editor.setIndentationWidth(i)
	k = 'indent.tab_width'
	if k in dct:
		i = int(dct[k])
		editor.setTabWidth(i)

	k = 'lexer.extension'
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
