EYE
---

EYE is a Qt based text/code editor designed to be customizable/scriptable.
It uses Scintilla as the base text widget. It currently supports:

* tabbed, multi-split, multi-window GUI
* syntax coloring
* project/directory level editing preferences
* recursive grep integration
* Python scriptability

Customizability
---------------

By default, EYE provides a basic UI with a tabbed window with one editor.
A few widgets and plugins are available but not enabled by default.

At startup, Python scripts contained in the user configuration directory are run.
These scripts can use the EYE API to configure the app as you want.

They can:

* enable built-in plugins (like automatic syntax coloring when a file is opened) and features
* create actions on keyboard shortcuts or react on other events
* customize the menus/toolbars or the rest of the UI
* make complete plugins

All of this is doable through the full Python API, the EYE API and the Qt components upon which EYE is based.

What plugins are available?
---------------------------

* simple recursive grep search
* backward/forward file navigation
* syntax coloring based on file extension
* theming
* macro recording/replay
* "project"-wide indentation style (with support for `.editorconfig <http://editorconfig.org/>`_)
* file-line bookmarks (not saved on quit though)
* autocompletion with YouCompleteMe

What plugins are planned?
-------------------------

* build system launch with error annotations in the source code
* semantic source coloring with clang api
* controlling a debugger
* more features for easing navigation and search

Where is the documentation?
---------------------------

The documentation is built with sphinx in the docs dir and can be `consulted online <https://eye.readthedocs.io/>`_.
It is also a work-in-progress.

Version
-------

EYE is currently in alpha state, say 0.0.1. When it's stable, it will use `semantic versioning <http://semver.org/>`_, for better plugins compatibility.

