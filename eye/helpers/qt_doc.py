# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Basic Qt documentation module

This module isn't imported anywhere. Its sole purpose is to generate a basic documentation of common Qt classes used
in EYE.

Since the PyQt docstrings only contain the signature of methods and no real documentation, this module is very basic
and should only be used when it's not possible to read the regular
`Qt documentation <https://doc.qt.io/qt-5/reference-overview.html>`_, which should be used instead.

* :any:`QObject`
* :any:`Qt`
* :any:`QPoint`

* :any:`QColor`
* :any:`QKeySequence`

* :any:`QWidget`
* :any:`QMainWindow`
* :any:`QMenu`
* :any:`QSplitter`
* :any:`QTabWidget`
"""

from PyQt5.QtCore import QObject, Qt, QPoint
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtWidgets import QWidget, QSplitter, QTabWidget, QMainWindow, QMenu

__all__ = (
	'QObject', 'Qt', 'QPoint',
	'QColor', 'QKeySequence',
	'QWidget', 'QMainWindow', 'QMenu', 'QSplitter', 'QTabWidget',
)
