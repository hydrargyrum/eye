Qt basics
=========

EYE heavily uses the Qt toolkit, which is a toolkit for user interfaces, and EYE's UI is all based on Qt. Qt provides
a number of widgets used by EYE, like dialogs, tab bars, splitters, menus, etc.

When scripting and configuring EYE, these widgets are not abstracted away, or hidden behind another layer, which
means writing a plugin may require learning some basic things about Qt, but it also means that plugin code is on par
with the core EYE code, not a second-class citizen with limited control. Even if some stuff may be hardcoded in core
EYE code (and it may not be hardcoded forever), this is orthogonal, an abstraction layer wouldn't change this fact.

So, in order to use best the EYE API, it is important to understand some core Qt concepts. Reading a PyQt tutorial
is a good thing but this documentation introduces some of the most basic things.

Objects and widgets
-------------------

Qt is an object oriented toolkit, so every widget is an object. Furthermore, all widgets inherit the `QObject`
class, though there are subclasses of `QObject` which are not widgets.

All `QObject`s may have a parent `QObject`. This can be set manually with the `setParent()` method or by using the
`parent=` attribute when constructing an object. This can also be set behind the scenes when a widget belongs to a
window, etc.

Signals/Slots
-------------

In Qt, many objects can emit "signals", which broadcast state changes and events happenning.

Anything can listen to those signals and perform actions when they are emitted. Those actions could be put in various
functions.

In the Qt jargon, the signals would be connected to slots (the functions performing actions when the signal is
emitted).

For example, an :any:`eye.widgets.editor.Editor` emits signal :any:`eye.widgets.editor.Editor.fileSaved` to indicate
that the file contents have been saved to disk.
One could connect the `fileSaved` signal to a slot (function) displaying a transient success message in the status
bar.

EYE provides helpers to connect signals from whole categories of objects instead of individual objects in the
:doc:`eye.connector` module.

Memory handling
---------------

PyQt is a Python wrapper to the Qt toolkit, which is written in C++ and thus has a different way of handling memory
than Python libraries, not having a garbage collector.

This is important because in PyQt, if a `QObject` has no parent, its deletion is handled normally with Python's gc,
but if a `QObject` has a parent, and this parent is destroyed (for example, because it was garbage collected), the
child is also deleted, even if there were Python references to the child! To avoid that, a reference should have been
kept to the parent.

It's not necessary to always keep those rules in mind, but if segmentation faults happen while writing a plugin for
EYE, then the reason could be this special memory handling.
