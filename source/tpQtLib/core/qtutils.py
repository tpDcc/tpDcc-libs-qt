#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# """ ==================================================================
# Script Name: qtutils.py
# by Tomas Poveda
# Utility module that contains useful utilities functions for PySide
# ______________________________________________________________________
# ==================================================================="""

import os
import re
import sys
import inspect
import traceback
import subprocess
import contextlib

import tpPyUtils
from tpPyUtils import python, fileio, strings, path

QT_AVAILABLE = True
try:
    from Qt.QtCore import *
    from Qt.QtWidgets import *
    from Qt.QtGui import *
    from Qt import QtGui
    from Qt import QtCompat
    from Qt import __binding__
except ImportError as e:
    QT_AVAILABLE = False
    print('Impossible to load Qt libraries. Qt dependant functionality will be disabled!')

if QT_AVAILABLE:
    if __binding__ == 'PySide2':
        try:
            import shiboken2 as shiboken
        except ImportError:
            from PySide2 import shiboken2 as shiboken
    else:
        try:
            import shiboken
        except ImportError:
            try:
                from Shiboken import shiboken
            except ImportError:
                try:
                    from PySide import shiboken
                except Exception:
                    pass

from tpQtLib.core import color

# ==============================================================================

UI_EXTENSION = '.ui'
QWIDGET_SIZE_MAX = (1 << 24) - 1

# ==============================================================================


def is_pyqt():
    """
    Returns True if the current Qt binding is PyQt
    :return: bool
    """

    return 'PyQt' in __binding__

def is_pyqt4():
    """
    Retunrs True if the currente Qt binding is PyQt4
    :return: bool
    """

    return __binding__ == 'PyQt4'


def is_pyqt5():
    """
    Retunrs True if the currente Qt binding is PyQt5
    :return: bool
    """

    return __binding__ == 'PyQt5'


def is_pyside():
    """
    Returns True if the current Qt binding is PySide
    :return: bool
    """

    return __binding__ == 'PySide'


def is_pyside2():
    """
    Returns True if the current Qt binding is PySide2
    :return: bool
    """

    return __binding__ == 'PySide2'


def get_ui_library():
    """
    Returns the library that is being used
    """

    try:
        import PyQt5
        qt = 'PyQt5'
    except ImportError:
        try:
            import PyQt4
            qt = 'PyQt4'
        except ImportError:
            try:
                import PySide2
                qt = 'PySide2'
            except ImportError:
                try:
                    import PySide
                    qt = 'PySide'
                except ImportError:
                    raise ImportError("No valid Gui library found!")
    return qt


def wrapinstance(ptr, base=None):
    if ptr is None:
        return None

    ptr = long(ptr)
    if globals().has_key('shiboken'):
        if base is None:
            qObj = shiboken.wrapInstance(long(ptr), QObject)
            meta_obj = qObj.metaObject()
            cls = meta_obj.className()
            super_cls = meta_obj.superClass().className()
            if hasattr(QtGui, cls):
                base = getattr(QtGui, cls)
            elif hasattr(QtGui, super_cls):
                base = getattr(QtGui, super_cls)
            else:
                base = QWidget
        try:
            return shiboken.wrapInstance(long(ptr), base)
        except:
            from PySide.shiboken import wrapInstance
            return wrapInstance(long(ptr), base)
    elif globals().has_key('sip'):
        base = QObject
        return shiboken.wrapinstance(long(ptr), base)
    else:
        print('Failed to wrap object ...')
        return None


def unwrapinstance(object):
    """
    Unwraps objects with PySide
    """

    return long(shiboken.getCppPointer(object)[0])


@contextlib.contextmanager
def app():
    """
    Context to create a Qt app
    >>> with with qtutils.app():
    >>>     w = QWidget(None)
    >>>     w.show()
    :return:
    """

    app_ = None
    is_app_running = bool(QApplication.instance())
    if not is_app_running:
        app_ = QApplication(sys.argv)
        install_fonts()

    yield None

    if not is_app_running:
        sys.exit(app_.exec_())


def install_fonts(path):
    """
    Install all the fonts in the given directory path
    :param path: str
    """

    if not os.path.isdir(path):
        return

    path = os.path.abspath(path)
    font_data_base = QFontDatabase()
    for filename in os.listdir(path):
        if filename.endswith('.ttf'):
            filename = os.path.join(path, filename)
            result = font_data_base.addApplicationFont(filename)
            if result > 0:
                tpPyUtils.logger.debug('Added font {}'.format(filename))
            else:
                tpPyUtils.logger.debug('Impossible to add font {}'.format(filename))


def ui_path(cls):
    """
    Returns the UI path for the given widget class
    :param cls: type
    :return: str
    """

    name = cls.__name__
    ui_path = inspect.getfile(cls)
    dirname = os.path.dirname(ui_path)

    ui_path = dirname + '/resource/ui' + name + UI_EXTENSION
    if not os.path.exists(ui_path):
        ui_path = dirname + '/ui/' + name + UI_EXTENSION
    if not os.path.exists(ui_path):
        ui_path = dirname + '/' + name + UI_EXTENSION

    return ui_path


def load_widget_ui(widget, path=None):
    """
    Loads UI of the given widget
    :param widget: QWidget or QDialog
    :param path: str
    """

    if not path:
        path = ui_path(widget.__class__)

    cwd = os.getcwd()
    try:
        os.chdir(os.path.dirname(path))
        widget.ui = QtCompat.loadUi(path, widget)
    except Exception as e:
        pass
        # tpPyUtils.logger.debug('{} | {}'.format(e, traceback.format_exc()))
    finally:
        os.chdir(cwd)


def ui_loader(ui_file, widget=None):
    """
    Loads GUI from .ui file
    :param ui_file: str, path to the UI file
    :param widget: parent widget
    """

    if not ui_file:
        ui_file = ui_path(widget.__class__)

    ui = QtCompat.loadUi(ui_file)
    if not widget:
        return ui
    else:
        for member in dir(ui):
            if not member.startswith('__') and member is not 'staticMetaObject':
                setattr(widget, member, getattr(ui, member))
        return ui


def create_python_qrc_file(qrc_file, py_file):

    """
    Creates a Python file from a QRC file
    :param src_file: str, QRC file name
    """

    if not os.path.isfile(qrc_file):
        return

    pyside_rcc_exe_path = 'C:\\Python27\\Lib\\site-packages\\PySide\\pyside-rcc.exe'
    # pyside_rcc_exe_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'externals', 'pyside-rcc', 'pyside-rcc.exe')
    if not os.path.isfile(pyside_rcc_exe_path):
        print('RCC_EXE_PATH_DOES_NOT_EXISTS!!!!!!!!!!!!!')
    #     pyside_rcc_exe_path = filedialogs.OpenFileDialog(
    #         title='Select pyside-rcc.exe location folder ...',
    #     )
    #     pyside_rcc_exe_path.set_directory('C:\\Python27\\Lib\\site-packages\\PySide')
    #     pyside_rcc_exe_path.set_filters('EXE files (*.exe)')
    #     pyside_rcc_exe_path = pyside_rcc_exe_path.exec_()
    # if not os.path.isfile(pyside_rcc_exe_path):
        return
    # py_out = os.path.splitext(os.path.basename(src_file))[0]+'.py'
    # py_out_path = os.path.join(os.path.dirname(src_file), py_out)
    try:
        subprocess.check_output('"{0}" -o "{1}" "{2}"'.format(pyside_rcc_exe_path, py_file, qrc_file))
    except subprocess.CalledProcessError as e:
        raise RuntimeError('command {0} returned with error (code: {1}): {2}'.format(e.cmd, e.returncode, e.output))
    if not os.path.isfile(py_file):
        return

    fileio.replace(py_file, "from PySide import QtCore", "from Qt import QtCore")


def create_qrc_file(src_paths, dst_file):

    def tree(top='.',
             filters=None,
             output_prefix=None,
             max_level=4,
             followlinks=False,
             top_info=False,
             report=True):
        # The Element of filters should be a callable object or
        # is a byte array object of regular expression pattern.
        topdown = True
        total_directories = 0
        total_files = 0

        top_fullpath = os.path.realpath(top)
        top_par_fullpath_prefix = os.path.dirname(top_fullpath)

        if top_info:
            lines = top_fullpath
        else:
            lines = ""

        if filters is None:
            _default_filter = lambda x: not x.startswith(".")
            filters = [_default_filter]

        for root, dirs, files in os.walk(top=top_fullpath, topdown=topdown, followlinks=followlinks):
            assert root != dirs

            if max_level is not None:
                cur_dir = strings.strips(root, top_fullpath)
                path_levels = strings.strips(cur_dir, "/").count("/")
                if path_levels > max_level:
                    continue

            total_directories += len(dirs)
            total_files += len(files)

            for filename in files:
                for _filter in filters:
                    if callable(_filter):
                        if not _filter(filename):
                            total_files -= 1
                            continue
                    elif not re.search(_filter, filename, re.UNICODE):
                        total_files -= 1
                        continue

                    if output_prefix is None:
                        cur_file_fullpath = os.path.join(top_par_fullpath_prefix, root, filename)
                    else:
                        buf = strings.strips(os.path.join(root, filename), top_fullpath)
                        if output_prefix != "''":
                            cur_file_fullpath = os.path.join(output_prefix, buf.strip('/'))
                        else:
                            cur_file_fullpath = buf

                    lines = "%s%s%s" % (lines, os.linesep, cur_file_fullpath)

        lines = lines.lstrip(os.linesep)

        if report:
            report = "%d directories, %d files" % (total_directories, total_files)
            lines = "%s%s%s" % (lines, os.linesep * 2, report)

        return lines

    def scan_files(src_path="."):
        filters = ['.(png|jpg|gif)$']
        output_prefix = './'
        report = False
        lines = tree(src_path, filters=filters, output_prefix=output_prefix, report=report)

        lines = lines.split('\n')
        if "" in lines:
            lines.remove("")

        return lines

    def create_qrc_body(src_path, root_res_path, use_alias=True):

        res_folder_files = path.get_absolute_file_paths(src_path)
        lines = [os.path.relpath(f, root_res_path) for f in res_folder_files]

        if use_alias:
            buf = ['\t\t<file alias="{0}">{1}</file>\n'.format(os.path.splitext(os.path.basename(i))[0].lower().replace('-', '_'), i).replace('\\', '/') for i in lines]
        else:
            buf = ["\t\t<file>{0}</file>\n".format(i).replace('\\', '/') for i in lines]
        buf = "".join(buf)
        # buf = QRC_TPL % buf
        return buf

    # Clean existing resources files and append initial resources header text
    if dst_file:
        parent = os.path.dirname(dst_file)
        if not os.path.exists(parent):
            os.makedirs(parent)
        f = file(dst_file, "w")
        f.write('<RCC>\n')

        try:
            for res_folder in src_paths:
                res_path = os.path.dirname(res_folder)
                start_header = '\t<qresource prefix="{0}">\n'.format(os.path.basename(res_folder))
                qrc_body = create_qrc_body(res_folder, res_path)
                end_header = '\t</qresource>\n'
                res_text = start_header + qrc_body + end_header

                f = file(dst_file, 'a')
                f.write(res_text)

            # Write end header
            f = file(dst_file, "a")
            f.write('</RCC>')
            f.close()
        except RuntimeError:
            f.close()


def get_signals(class_obj):
    """
    Returns a list with all signals of a class
    :param class_obj: QObject
    """

    result = filter(lambda x: isinstance(x[1], Signal), vars(class_obj).iteritems())
    if class_obj.__base__ and class_obj.__base__ != QObject:
        result.extend(get_signals(class_obj.__base__))
    return result


def safe_delete_later(widget):
    """
    calls the deleteLater method on the given widget, but only
    in the necessary Qt environment
    :param widget: QWidget
    """

    if __binding__ in ('PySide', 'PyQt4'):
        widget.deleteLater()


def show_info(parent, title, info):
    """
    Show a info QMessageBox with the given info
    :return:
    """

    return QMessageBox.information(parent, title, info)


def show_question(parent, title, question):
    """
    Show a question QMessageBox with the given question text
    :param question: str
    :return:
    """

    flags = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    return QMessageBox.question(parent, title, question, flags)


def show_warning(parent, title, warning):
    """
    Shows a warning QMessageBox with the given warning text
    :param parent: QWidget
    :param title: str
    :param warning: str
    :return:
    """

    return QMessageBox.warning(parent, title, warning)

def show_error(parent, title, error):
    """
    Show a error QMessageBox with the given error
    :return:
    """

    return QMessageBox.critical(parent, title, error)


def clear_layout(layout):
    """
    Removes all the widgets added in the given layout
    :param layout: QLayout
    """

    while layout.count():
        child = layout.takeAt(0)
        if child.widget() is not None:
            child.widget().deleteLater()
        elif child.layout() is not None:
            clear_layout(child.layout())

    # for i in reversed(range(layout.count())):
    #     item = layout.itemAt(i)
    #     if item:
    #         w = item.widget()
    #         if w:
    #             w.setParent(None)


def image_to_clipboard(path):
    """
    Copies the image at path to the system's global clipboard
    :param path: str
    """

    image = QtGui.QImage(path)
    clipboard = QApplication.clipboard()
    clipboard.setImage(image, mode=QtGui.QClipboard.Clipboard)


def get_horizontal_separator():
    v_div_w = QWidget()
    v_div_l = QVBoxLayout()
    v_div_l.setAlignment(Qt.AlignLeft)
    v_div_l.setContentsMargins(0, 0, 0, 0)
    v_div_l.setSpacing(0)
    v_div_w.setLayout(v_div_l)
    v_div = QFrame()
    v_div.setMinimumHeight(30)
    v_div.setFrameShape(QFrame.VLine)
    v_div.setFrameShadow(QFrame.Sunken)
    v_div_l.addWidget(v_div)
    return v_div_w


def get_rounded_mask(width, height, radius_tl=10, radius_tr=10, radius_bl=10, radius_br=10):
    region = QtGui.QRegion(0, 0, width, height, QtGui.QRegion.Rectangle)

    # top left
    round = QtGui.QRegion(0, 0, 2*radius_tl, 2 * radius_tl, QtGui.QRegion.Ellipse)
    corner = QtGui.QRegion(0, 0, radius_tl, radius_tl, QtGui.QRegion.Rectangle)
    region = region.subtracted(corner.subtracted(round))

    # top right
    round = QtGui.QRegion(width - 2 * radius_tr, 0, 2 * radius_tr, 2 * radius_tr, QtGui.QRegion.Ellipse)
    corner = QtGui.QRegion(width - radius_tr, 0, radius_tr, radius_tr, QtGui.QRegion.Rectangle)
    region = region.subtracted(corner.subtracted(round))

    # bottom right
    round = QtGui.QRegion(width - 2 * radius_br, height-2*radius_br, 2 * radius_br, 2 * radius_br, QtGui.QRegion.Ellipse)
    corner = QtGui.QRegion(width - radius_br, height-radius_br, radius_br, radius_br, QtGui.QRegion.Rectangle)
    region = region.subtracted(corner.subtracted(round))

    # bottom left
    round = QtGui.QRegion(0, height - 2 * radius_bl, 2 * radius_bl, 2 * radius_br, QtGui.QRegion.Ellipse)
    corner = QtGui.QRegion(0, height - radius_bl, radius_bl, radius_bl, QtGui.QRegion.Rectangle)
    region = region.subtracted(corner.subtracted(round))

    return region


def distance_point_to_line(p, v0, v1):
    v = QtGui.QVector2D(v1 - v0)
    w = QtGui.QVector2D(p - v0)
    c1 = QtGui.QVector2D.dotProduct(w, v)
    c2 = QtGui.QVector2D.dotProduct(v, v)
    b = c1 * 1.0 / c2
    pb = v0 + v.toPointF() * b
    return QtGui.QVector2D(p - pb).length()


def qhash (inputstr):
    instr = ""
    if isinstance (inputstr, str):
        instr = inputstr
    elif isinstance (inputstr, unicode):
        instr = inputstr.encode ("utf8")
    else:
        return -1

    h = 0x00000000
    for i in range (0, len (instr)):
        h = (h << 4) + ord(instr[i])
        h ^= (h & 0xf0000000) >> 23
        h &= 0x0fffffff
    return h


def get_focus_widget():
    """
    Gets the currently focused widget
    :return: variant, QWidget || None
    """

    return QApplication.focusWidget()


def get_widget_at_mouse():
    """
    Get the widget under the mouse
    :return: variant, QWidget || None
    """

    current_pos = QtGui.QCursor().pos()
    widget = QApplication.widgetAt(current_pos)
    return widget


def is_valid_widget(widget):
    """
    Checks if a widget is a valid in the backend
    :param widget: QWidget
    :return: bool, True if the widget still has a C++ object, False otherwise
    """

    if widget is None:
        return False

    # Added try because Houdini does not includes Shiboken library by default
    # TODO: When Houdini app class implemented, add cleaner way
    try:
        if not shiboken.isValid(widget):
            return False
    except:
        return True

    return True


def close_and_cleanup(widget):
    """
    Call close and deleteLater on a widget safely
    NOTE: Skips the close call if the widget is already not visible
    :param widget: QWidget, widget to delete and close
    """
    if is_valid_widget(widget):
        if widget.isVisible():
            widget.close()
        widget.deleteLater()


def get_string_input(message, title='Rename', parent=None, old_name=None):
    """
    Shows a Input dialog to allow the user to input a new string
    :param message: str, mesage to show in the dialog
    :param title: str, title of the input dialog
    :param parent: QWidget (optional), parent widget for the input
    :param old_name: str (optional): old name where are trying to rename
    :return: str, new name
    """

    parent = None

    dialog = QInputDialog()
    flags = dialog.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint

    if not old_name:
        comment, ok = dialog.getText(parent, title, message, flags=flags)
    else:
        comment, ok = dialog.getText(parent, title, message, text=old_name, flags=flags)

    comment = comment.replace('\\', '_')

    if ok:
        return str(comment)


def get_comment(text_message='Add Comment', title='Save', comment_text='', parent=None):
    """
    Shows a comment dialog to allow user to input a new comment
    :param parent: QwWidget
    :param text_message: str, text to show before message input
    :param title: str, title of message dialog
    :param comment_text: str, default text for the commment
    :return: str, input comment write by the user
    """

    comment_dialog = QInputDialog()
    flags = comment_dialog.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    comment, ok = comment_dialog.getText(parent, title, text_message, flags=flags, text=comment_text)
    if ok:
        return comment


def get_file(directory, parent=None):
    """
    Show a open file dialog
    :param directory: str, root directory
    :param parent: QWidget
    :return: str, selected folder or None if no folder is selected
    """

    file_dialog = QFileDialog(parent)
    if directory:
        file_dialog.setDirectory(directory)
    directory = file_dialog.getOpenFileName()
    directory = python.force_list(directory)
    if directory:
        return directory


def get_folder(directory=None, title='Select Folder', parent=None):
    """
    Shows a open folder dialog
    :param directory: str, root directory
    :param title: str, select folder dialog title
    :param parent: QWidget
    :return: str, selected folder or None if no folder is selected
    """

    file_dialog = QFileDialog(parent)
    if directory:
        file_dialog.setDirectory(directory)
    directory = file_dialog.getExistingDirectory(parent, title)
    if directory:
        return directory


def get_permission(message=None, cancel=True, title='Permission', parent=None):
    """
    Shows a permission message box
    :param message: str, message to show to the user
    :param cancel: bool, Whether the user can cancel the operation or not
    :param title: str, title of the window
    :param parent: QWidget
    :return: bool
    """

    message_box = QMessageBox()
    message_box.setWindowTitle(title)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    if message:
        message_box.setText(message)
    if cancel:
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
    else:
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    message_box.setWindowFlags(flags)
    result = message_box.exec_()

    if result == QMessageBox.Yes:
        return True
    elif result == QMessageBox.No:
        return False
    elif result == QMessageBox.Cancel:
        return None

    return None


def get_save_permission(message, file_path=None, title='Permission', parent=None):
    """
    Shows a save path message box
    :param message: str, message to show to the user
    :param file_path: str, path you want to save
    :param title: str, title of the window
    :param parent: QWidget
    :return: bool
    """

    message_box = QMessageBox()
    message_box.setWindowTitle(title)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    if file_path:
        path_message = 'Path: {}'.format(file_path)
        message_box.setInformativeText(path_message)
    message_box.setWindowFlags(flags)
    save = message_box.addButton('Save', QMessageBox.YesRole)
    no_save = message_box.addButton('Do not save', QMessageBox.NoRole)
    cancel = message_box.addButton('Cancel', QMessageBox.RejectRole)
    message_box.exec_()

    if message_box.clickedButton() == save:
        return True
    elif message_box.clickedButton() == no_save:
        return False
    elif message_box.clickedButton() == cancel:
        return None

    return None


def get_line_layout(title, parent, *widgets):
    """
    Returns a QHBoxLayout with all given widgets added to it
    :param parent: QWidget
    :param title: str
    :param widgets: list<QWidget>
    :return: QHBoxLayout
    """

    layout = QHBoxLayout()
    layout.setContentsMargins(1, 1, 1, 1)
    if title and title != '':
        label = QLabel(title, parent)
        layout.addWidget(label)
    for w in widgets:
        if isinstance(w, QWidget):
            layout.addWidget(w)
        elif isinstance(w, QLayout):
            layout.addLayout(w)

    return layout


def get_column_layout(*widgets):
    """
    Returns a QVBoxLayout with all given widgets added to it
    :param widgets: list<QWidget>
    :return: QVBoxLayout
    """

    layout = QVBoxLayout()
    for w in widgets:
        if isinstance(w, QWidget):
            layout.addWidget(w)
        elif isinstance(w, QLayout):
            layout.addLayout(w)

    return layout


def get_top_level_widget(w):
    widget = w
    while True:
        parent = widget.parent()
        if not parent:
            break
        widget = parent

        return widget


def is_modifier():
    """
    Returns True if either the Alt key or Control key is down
    :return: bool
    """

    return is_alt_modifier() or is_control_modifier()


def is_alt_modifier():
    """
    Return True if the Alt key is down
    :return: bool
    """

    modifiers = QApplication.keyboardModifiers()
    return modifiers == Qt.AltModifier


def is_control_modifier():
    """
    Returns True if the Control key is down
    :return: bool
    """

    modifiers = QApplication.keyboardModifiers()
    return modifiers == Qt.ControlModifier


def is_shift_modifier():
    """
    Returns True if the Shift key is down
    :return: bool
    """

    modifiers = QApplication.keyboardModifiers()
    return modifiers == Qt.ShiftModifier


def to_qt_object(long_ptr, qobj=None):
    """
    Returns an instance of the Maya UI element as a QWidget
    """

    if not qobj:
        qobj = QWidget

    return wrapinstance(long_ptr, qobj)


def critical_message(message, parent=None):
    """
    Shows a critical message
    :param message: str
    :param parent: QWidget
    """

    parent = None
    message_box = QMessageBox(parent)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    message_box.setWindowFlags(flags)
    message_box.critical(parent, 'Critical Error', message)


def warning_message(message, parent=None):
    """
    Shows a warning message
    :param message: str
    :param parent: QWidget
    """

    parent = None
    message_box = QMessageBox(parent)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    message_box.setWindowFlags(flags)
    message_box.warning(parent, 'Warning', message)


def info_message(message, parent=None):
    """
    Shows a warning message
    :param message: str
    :param parent: QWidget
    """

    parent = None
    message_box = QMessageBox(parent)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    message_box.setWindowFlags(flags)
    message_box.setText(message)
    message_box.exec_()


def about_message(message, parent=None):
    """
    Shows an about message
    :param message: str
    :param parent: QWidget
    """

    parent = None
    message_box = QMessageBox(parent)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    message_box.setWindowFlags(flags)
    message_box.about(parent, 'About', message)


def change_button_color(
        button,
        text_color=200, bg_color=68, hi_color=68,
        hi_text=255, hi_background=[97, 132, 167],
        ds_color=[255, 128, 128],
        mode='common',
        toggle=False, hover=True, destroy=False,
        ds_width=1):

    text_color = python.to_3_list(text_color)
    bg_color = python.to_3_list(bg_color)
    hi_color = python.to_3_list(hi_color)
    hi_text = python.to_3_list(hi_text)
    ds_color = python.to_3_list(ds_color)

    if toggle and button.isChecked():
        bg_color = hi_color
    if hover:
        hv_color = map(lambda a: a+20, bg_color)
    else:
        hv_color = bg_color

    text_hex = color.convert_2_hex(text_color)
    bg_hex = color.convert_2_hex(bg_color)
    hv_hex = color.convert_2_hex(hv_color)
    hi_hex = color.convert_2_hex(hi_color)
    ht_hex = color.convert_2_hex(hi_text)
    hb_hex = color.convert_2_hex(hi_background)
    ds_hex = color.convert_2_hex(ds_color)

    if mode == 'common':
        button.setStyleSheet('color: ' + text_hex + ' ; background-color: ' + bg_hex)
    elif mode == 'button':
        if not destroy:
            button.setStyleSheet(
                'QPushButton{background-color: ' + bg_hex + '; color:  ' + text_hex + '; border-style:solid; border-width: ' + str(
                    ds_width) + 'px; border-color:' + ds_hex + '; border-radius: 0px;}' + \
                'QPushButton:hover{background-color: ' + hv_hex + '; color:  ' + text_hex + '; border-style:solid; border-width: ' + str(
                    ds_width) + 'px; border-color:' + ds_hex + '; border-radius: 0px;}' + \
                'QPushButton:pressed{background-color: ' + hi_hex + '; color: ' + text_hex + '; border-style:solid; border-width: ' + str(
                    ds_width) + 'px; border-color:' + ds_hex + '; border-radius: 0px;}')
        else:
            button.setStyleSheet(
                'QPushButton{background-color: ' + bg_hex + '; color:  ' + text_hex + ' ; border: black 0px}' + \
                'QPushButton:hover{background-color: ' + hv_hex + '; color:  ' + text_hex + ' ; border: black 0px}' + \
                'QPushButton:pressed{background-color: ' + hi_hex + '; color: ' + text_hex + '; border: black 2px}')
    elif mode == 'window':
        button.setStyleSheet('color: ' + text_hex + ';' + \
                             'background-color: ' + bg_hex + ';' + \
                             'selection-color: ' + ht_hex + ';' + \
                             'selection-background-color: ' + hb_hex + ';')


def change_border_style(btn):
    btn.setStyleSheet('QPushButton{border-style:solid; border-width: 2px; border-color: red ; border-radius: 1px;}' + \
                         'QPushButton:hover{border-style:solid; border-width: 2px; border-color: red ; border-radius: 1px;}' + \
                         'QPushButton:pressed{border-style:solid; border-width: 2px; border-color: red ; border-radius: 1px;}')


def create_flat_button(
        icon=None, icon_size=None,
        name='', text=200,
        background_color=[54, 51, 51],
        ui_color=68,
        border_color=180,
        push_col=120,
        checkable=True,
        w_max=None, w_min=None,
        h_max=None, h_min=None,
        policy=None,
        tip=None, flat=True,
        hover=True,
        destroy_flag=False,
        context=None,
):

    btn = QPushButton()
    btn.setText(name)
    btn.setCheckable(checkable)
    if icon:
        if isinstance(icon, QIcon):
            btn.setIcon(icon)
        else:
            btn.setIcon(QIcon(icon))
    btn.setFlat(flat)
    if flat:
        change_button_color(button=btn, text_color=text, bg_color=ui_color, hi_color=background_color, mode='button', hover=hover, destroy=destroy_flag, ds_color=border_color)
        btn.toggled.connect(lambda: change_button_color(button=btn, text_color=text, bg_color=ui_color, hi_color=background_color, mode='button', toggle=True, hover=hover, destroy=destroy_flag, ds_color=border_color))
    else:
        change_button_color(button=btn, text_color=text, bg_color=background_color, hi_color=push_col, mode='button', hover=hover, destroy=destroy_flag, ds_color=border_color)

    if w_max:
        btn.setMaximumWidth(w_max)
    if w_min:
        btn.setMinimumWidth(w_min)
    if h_max:
        btn.setMaximumHeight(h_max)
    if h_min:
        btn.setMinimumHeight(h_min)
    if icon_size:
        btn.setIconSize(QSize(*icon_size))
    if policy:
        btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
    if tip:
        btn.setToolTip(tip)
    if context:
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(context)

    return btn
