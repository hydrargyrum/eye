# EYE

EYE is a Qt based text/code editor designed to be customizable/scriptable.
It uses Scintilla as the base text widget. It currently supports:
* tabbed, multi-split, multi-window GUI
* syntax coloring
* project/directory level editing preferences
* recursive grep integration
* Python scriptability

## Customizability

By default, EYE provides a basic UI with a tabbed window with one editor.
A few widgets and plugins are available but not enabled by default.
At startup, Python scripts contained in the user configuration directory are run.
These scripts can use the EYE API to configure the app as you want.
They can enable built-in plugins (like automatic syntax coloring when a file is opened) and features.
They have the ability to create actions on keyboard shortcuts or react on other events.
They can also customize the menus/toolbars or the rest of the UI.
They also have the opportunity of making complete plugins.
All of this is doable through the full Python API, the EYE API and the Qt components upon which EYE is based.

## What plugins are available?

* simple recursive grep search
* backward/forward file navigation
* syntax coloring based on file extension
* theming
* macro recording/replay
* "project"-wide indentation style (TODO support for [`.editorconfig`](http://editorconfig.org/))
* file-line bookmarks (not saved on quit though)

## What plugins are planned?

* autocompletion with YouCompleteMe
* build system launch with error annotations in the source code
* semantic source coloring with clang api
* controlling a debugger
* more features for easing navigation and search

## Why is Qt4 used instead of Qt5?

The project was started on Qt4 out of convenience, it is not an aim. It will be ported to Qt5 at some point, but help is welcome.

## Where is the documentation?

For now, there's only the plugins code, no documentation yet.
[PyQt4 docs](http://pyqt.sourceforge.net/Docs/PyQt4/index.html) are useful, and also the [QScintilla docs](http://pyqt.sourceforge.net/Docs/QScintilla2/).
