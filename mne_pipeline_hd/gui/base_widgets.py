# -*- coding: utf-8 -*-
"""
Pipeline-GUI for Analysis with MNE-Python
@author: Martin Schulz
@email: dev@earthman-music.de
@github: https://github.com/marsipu/mne_pipeline_hd
License: BSD (3-clause)
Written on top of MNE-Python
Copyright © 2011-2020, authors of MNE-Python (https://doi.org/10.3389/fnins.2013.00267)
inspired by Andersen, L. M. (2018) (https://doi.org/10.3389/fnins.2018.00006)
"""
import itertools
import sys
from inspect import getsourcefile
from os.path import abspath
from pathlib import Path

import numpy as np
import pandas
from PyQt5.QtCore import QItemSelectionModel, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QDialog, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
                             QListView,
                             QPushButton, QScrollArea, QSizePolicy,
                             QSpinBox,
                             QTabWidget, QTableView, QVBoxLayout, QWidget)

package_parent = str(Path(abspath(getsourcefile(lambda: 0))).parent.parent.parent)
sys.path.insert(0, package_parent)

from mne_pipeline_hd.gui.models import (BaseDictModel, BaseListModel, BasePandasModel, CheckDictEditModel,
                                        CheckDictModel, CheckListModel,
                                        EditDictModel, EditListModel, EditPandasModel, FileManagementModel)


class Base(QWidget):
    currentChanged = pyqtSignal(object, object)
    selectionChanged = pyqtSignal(object)
    dataChanged = pyqtSignal(object, object)

    def __init__(self, model, view, parent, title, verbose=False):
        super().__init__(parent)
        self.title = title
        self.verbose = verbose

        self.model = model
        self.view = view
        self.view.setModel(self.model)

        # Connect to custom Selection-Signal
        self.view.selectionModel().currentChanged.connect(self._current_changed)
        self.view.selectionModel().selectionChanged.connect(self._selection_changed)
        self.model.dataChanged.connect(self._data_changed)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        if self.title:
            title_label = QLabel(self.title)
            if len(self.title) <= 12:
                title_label.setFont(QFont('AnyStyle', 14))
            else:
                title_label.setFont(QFont('AnyStyle', 12))
            layout.addWidget(title_label)

        layout.addWidget(self.view)
        self.setLayout(layout)

    def get_current(self):
        try:
            current = self.model.getData(self.view.currentIndex())
        except (KeyError, IndexError):
            current = None

        return current

    def _current_changed(self, current_idx, previous_idx):
        current = self.model.getData(current_idx)
        previous = self.model.getData(previous_idx)

        self.currentChanged.emit(current, previous)

        if self.verbose:
            print(f'Current changed from {previous} to {current}')

    def get_selected(self):
        try:
            selected = [self.model.getData(idx) for idx in self.view.selectedIndexes()]
        except (KeyError, IndexError):
            selected = list()

        return selected

    def _selection_changed(self):
        # Somehow, the indexes got from selectionChanged don't appear to be right
        # (maybe some issue with QItemSelection?)
        selected = self.get_selected()

        self.selectionChanged.emit(selected)
        if self.verbose:
            print(f'Selection changed to {selected}')

    def _data_changed(self, index, _):
        data = self.model.getData(index)

        self.dataChanged.emit(data, index)
        if self.verbose:
            print(f'{data} changed at {index}')

    def content_changed(self):
        """Informs ModelView about external change made in data
        """
        self.model.layoutChanged.emit()

    def replace_data(self, new_data):
        """Replaces model._data with new_data
        """
        self.model._data = new_data
        self.content_changed()


class BaseList(Base):
    def __init__(self, model, view, extended_selection, parent, title, verbose=False):
        super().__init__(model, view, parent, title, verbose=verbose)

        if extended_selection:
            self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def select(self, values, clear_selection=True):
        indices = [i for i, x in enumerate(self.model._data) if x in values]

        if clear_selection:
            self.view.selectionModel().clearSelection()

        for idx in indices:
            index = self.model.createIndex(idx, 0)
            self.view.selectionModel().select(index, QItemSelectionModel.Select)


class SimpleList(BaseList):
    """A basic List-Widget to display the content of a list.

    Parameters
    ----------
    data : List of str | None
        Input a list with contents to display
    extended_selection: bool
        Set True, if you want to select more than one item in the list
    show_index: bool
        Set True if you want to display the list-index in front of each value
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent
    title : str | None
        An optional title
    verbose : bool
        Set True to see debugging for signals

    Notes
    -----
    If you change the contents of data outside of this class, call content_changed to update this widget.
    If you change the reference to data, call the appropriate replace_data.
    """

    def __init__(self, data=None, extended_selection=False, show_index=False, parent=None, title=None, verbose=False):
        super().__init__(model=BaseListModel(data, show_index=show_index), view=QListView(),
                         extended_selection=extended_selection, parent=parent, title=title, verbose=verbose)


class EditList(BaseList):
    """An editable List-Widget to display and manipulate the content of a list.

    Parameters
    ----------
    data : List of str | None
        Input a list with contents to display
    ui_buttons : bool
        If to display Buttons or not
    ui_button_pos: str
        The side on which to show the buttons, 'right', 'left', 'top' or 'bottom'
    show_index: bool
        Set True if you want to display the list-index in front of each value
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent
    title : str | None
        An optional title
    verbose : bool
        Set True to see debugging for signals

    Notes
    -----
    If you change the contents of the list outside of this class, call content_changed to update this widget.
    If you change the reference to data, call replace_data.
    """

    def __init__(self, data=None, ui_buttons=True, ui_button_pos='right', extended_selection=False,
                 show_index=False, parent=None, title=None, verbose=False, model=None):

        self.ui_buttons = ui_buttons
        self.ui_button_pos = ui_button_pos

        if model is None:
            model = EditListModel(data, show_index=show_index)

        super().__init__(model=model, view=QListView(),
                         extended_selection=extended_selection, parent=parent, title=title, verbose=verbose)

    def init_ui(self):
        if self.ui_button_pos in ['top', 'bottom']:
            layout = QVBoxLayout()
            bt_layout = QHBoxLayout()
        else:
            layout = QHBoxLayout()
            bt_layout = QVBoxLayout()

        if self.ui_buttons:
            addrow_bt = QPushButton('Add')
            addrow_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            addrow_bt.clicked.connect(self.add_row)
            bt_layout.addWidget(addrow_bt)

            rmrow_bt = QPushButton('Remove')
            rmrow_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            rmrow_bt.clicked.connect(self.remove_row)
            bt_layout.addWidget(rmrow_bt)

            edit_bt = QPushButton('Edit')
            edit_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            edit_bt.clicked.connect(self.edit_item)
            bt_layout.addWidget(edit_bt)

            layout.addLayout(bt_layout)

        if self.ui_button_pos in ['top', 'left']:
            layout.addWidget(self.view)
        else:
            layout.insertWidget(0, self.view)

        if self.title:
            super_layout = QVBoxLayout()
            title_label = QLabel(self.title)
            title_label.setFont(QFont('AnyStyle', 14))
            super_layout.addWidget(title_label)
            super_layout.addLayout(layout)
            self.setLayout(super_layout)
        else:
            self.setLayout(layout)

    # Todo: Add Rows at all possible positions
    def add_row(self):
        row = self.view.selectionModel().currentIndex().row() + 1
        if row == -1:
            row = 0
        self.model.insertRow(row)

    def remove_row(self):
        row_idxs = self.view.selectionModel().selectedRows()
        for row_idx in row_idxs:
            self.model.removeRow(row_idx.row())

    def edit_item(self):
        self.view.edit(self.view.selectionModel().currentIndex())


class CheckList(BaseList):
    """A Widget for a Check-List.

    Parameters
    ----------
    data : List of str | None
        Input a list with contents to display
    checked : List of str | None
        Input a list, which will contain the checked items from data (and which intial items will be checked)
    ui_buttons : bool
        If to display Buttons or not
    one_check : bool
        If only one Item in the CheckList can be checked at the same time
    show_index: bool
        Set True if you want to display the list-index in front of each value
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent
    title : str | None
        An optional title
    verbose : bool
        Set True to see debugging for signals

    Notes
    -----
    If you change the contents of data outside of this class, call content_changed to update this widget.
    If you change the reference to data, call replace_data or replace_checked.
    """

    checkedChanged = pyqtSignal(list)

    def __init__(self, data=None, checked=None, ui_buttons=True, ui_button_pos='right', one_check=False,
                 show_index=False, parent=None, title=None, verbose=False):

        self.ui_buttons = ui_buttons
        self.ui_button_pos = ui_button_pos

        super().__init__(model=CheckListModel(data, checked, one_check=one_check, show_index=show_index),
                         view=QListView(), extended_selection=False, parent=parent, title=title, verbose=verbose)

        self.model.dataChanged.connect(self._checked_changed)

    def init_ui(self):

        if self.ui_button_pos in ['top', 'bottom']:
            layout = QVBoxLayout()
            bt_layout = QHBoxLayout()
        else:
            layout = QHBoxLayout()
            bt_layout = QVBoxLayout()

        if self.ui_buttons:
            all_bt = QPushButton('All')
            all_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            all_bt.clicked.connect(self.select_all)
            bt_layout.addWidget(all_bt)

            clear_bt = QPushButton('Clear')
            clear_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            clear_bt.clicked.connect(self.clear_all)
            bt_layout.addWidget(clear_bt)

            layout.addLayout(bt_layout)

        if self.ui_button_pos in ['top', 'left']:
            layout.addWidget(self.view)
        else:
            layout.insertWidget(0, self.view)

        if self.title:
            super_layout = QVBoxLayout()
            title_label = QLabel(self.title)
            title_label.setFont(QFont('AnyStyle', 14))
            super_layout.addWidget(title_label)
            super_layout.addLayout(layout)
            self.setLayout(super_layout)
        else:
            self.setLayout(layout)

    def _checked_changed(self):
        self.checkedChanged.emit(self.model._checked)
        if self.verbose:
            print(f'Changed values: {self.model._checked}')

    def replace_checked(self, new_checked):
        """Replaces model._checked with new check_dict
        """
        self.model._checked = new_checked
        self.content_changed()

    def select_all(self):
        """Select all Items while leaving reference to model._checked intact"""
        for item in [i for i in self.model._data if i not in self.model._checked]:
            self.model._checked.append(item)
        # Inform Model about changes
        self.content_changed()
        self._checked_changed()

    def clear_all(self):
        """Deselect all Items while leaving reference to model._checked intact"""
        self.model._checked.clear()
        # Inform Model about changes
        self.content_changed()
        self._checked_changed()


class CheckDictList(BaseList):
    """A List-Widget to display the items of a list and mark them depending of their appearance in check_dict

    Parameters
    ----------
    data : List of str | None
        A list with items to display
    check_dict : dict | None
        A dictionary that may contain items from data as keys
    show_index: bool
        Set True if you want to display the list-index in front of each value
    yes_bt: int | None
        Supply a identifier for an icon to mark the items existing in check_dict, set None for standard icon
    no_bt: int | None
        Supply a identifier for an icon to mark the items not existing in check_dict, set None for standard icon
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent
    title : str | None
        An optional title
    verbose : bool
        Set True to see debugging for signals

    Notes
    -----
    If you change the contents of data outside of this class, call content_changed to update this widget.
    If you change the reference to data, call replace_data.
    If you change the reference to check_dict, call replace_check_dict.

    Identifiers for QT standard-icons:
    https://doc.qt.io/qt-5/qstyle.html#StandardPixmap-enum
    """

    def __init__(self, data=None, check_dict=None, extended_selection=False, show_index=False, yes_bt=None, no_bt=None,
                 parent=None, title=None, verbose=False):
        model = CheckDictModel(data, check_dict, show_index=show_index, yes_bt=yes_bt, no_bt=no_bt)
        super().__init__(model=model, view=QListView(),
                         extended_selection=extended_selection, parent=parent, title=title, verbose=verbose)

    def replace_check_dict(self, new_check_dict=None):
        """Replaces model.check_dict with new check_dict
        """
        if new_check_dict:
            self.model._check_dict = new_check_dict
        self.content_changed()


class CheckDictEditList(EditList):
    """A List-Widget to display the items of a list and mark them depending of their appearance in check_dict

    Parameters
    ----------
    data : List of str | None
        A list with items to display
    check_dict : dict | None
        A dictionary that may contain items from data as keys
    ui_buttons : bool
        If to display Buttons or not
    ui_button_pos: str
        The side on which to show the buttons, 'right', 'left', 'top' or 'bottom'
    show_index: bool
        Set True if you want to display the list-index in front of each value
    yes_bt: int | None
        Supply a identifier for an icon to mark the items existing in check_dict, set None for standard icon
    no_bt: int | None
        Supply a identifier for an icon to mark the items not existing in check_dict, set None for standard icon
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent
    title : str | None
        An optional title
    verbose : bool
        Set True to see debugging for signals

    Notes
    -----
    If you change the contents of data outside of this class, call content_changed to update this widget.
    If you change the reference to data, call replace_data.
    If you change the reference to check_dict, call replace_check_dict.

    Identifiers for QT standard-icons:
    https://doc.qt.io/qt-5/qstyle.html#StandardPixmap-enum
    """

    def __init__(self, data=None, check_dict=None, ui_buttons=True, ui_button_pos='right', extended_selection=False,
                 show_index=False, yes_bt=None, no_bt=None, parent=None, title=None, verbose=False):
        model = CheckDictEditModel(data, check_dict, show_index=show_index, yes_bt=yes_bt, no_bt=no_bt)
        super().__init__(data, ui_buttons, ui_button_pos, extended_selection, show_index, parent, title, verbose, model)

    def replace_check_dict(self, new_check_dict=None):
        """Replaces model.check_dict with new check_dict
        """
        if new_check_dict:
            self.model._check_dict = new_check_dict
        self.content_changed()


class BaseDict(Base):

    def __init__(self, model, view, parent, title, resize_rows=False, resize_columns=False, verbose=False):
        super().__init__(model, view, parent, title, verbose=verbose)
        self.verbose = verbose

        if resize_rows:
            model.layoutChanged.connect(self.view.resizeRowsToContents)
            model.layoutChanged.emit()
        if resize_columns:
            model.layoutChanged.connect(self.view.resizeColumnsToContents)
            model.layoutChanged.emit()

    def get_keyvalue_by_index(self, index, data_dict):
        """For the given index, make an entry in item_dict with the data at index as key and a dict as value defining
        if data is key or value and refering to the corresponding key/value of data depending on its type

        Parameters
        ----------
        index: Index in Model
        data_dict: Dictionary to store information about the data at index
        """
        data = self.model.getData(index)
        item_type = None
        counterpart = None
        if index.column() == 0:
            item_type = 'key'
            counterpart_idx = index.sibling(index.row(), 1)
            counterpart = self.model.getData(counterpart_idx)
        elif index.column() == 1:
            item_type = 'value'
            counterpart_idx = index.sibling(index.row(), 0)
            counterpart = self.model.getData(counterpart_idx)
        if data and item_type and counterpart:
            if data in data_dict:
                data_dict['counterpart'].append(counterpart)
            else:
                data_dict[data] = {'type': item_type, 'counterpart': [counterpart]}

        return data_dict

    def get_current(self):
        current_dict = dict()
        self.get_keyvalue_by_index(self.view.currentIndex(), current_dict)

        return current_dict

    def _current_changed(self, current_idx, previous_idx):
        current_dict = dict()
        previous_dict = dict()

        self.get_keyvalue_by_index(current_idx, current_dict)
        self.get_keyvalue_by_index(previous_idx, previous_dict)

        self.currentChanged.emit(current_dict, previous_dict)

        if self.verbose:
            print(f'Current changed from {previous_dict} to {current_dict}')

    def get_selected(self):
        selection_dict = dict()

        for idx in self.view.selectedIndexes():
            self.get_keyvalue_by_index(idx, selection_dict)

        return selection_dict

    def _selection_changed(self):
        # Somehow, the indexes got from selectionChanged don't appear to be right
        # (maybe some issue with QItemSelection?)
        selection_dict = self.selectionChanged.emit(self.get_selected())

        if self.verbose:
            print(f'Selection changed to {selection_dict}')

    def select(self, keys, values, clear_selection=True):
        key_indices = [i for i, x in enumerate(self.model._data.keys()) if x in keys]
        value_indices = [i for i, x in enumerate(self.model._data.values()) if x in values]

        if clear_selection:
            self.view.selectionModel().clearSelection()

        for idx in key_indices:
            index = self.model.createIndex(idx, 0)
            self.view.selectionModel().select(index, QItemSelectionModel.Select)

        for idx in value_indices:
            index = self.model.createIndex(idx, 1)
            self.view.selectionModel().select(index, QItemSelectionModel.Select)


class SimpleDict(BaseDict):
    """A Widget to display a Dictionary

    Parameters
    ----------
    data : dict | None
        Input a pandas DataFrame with contents to display
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent
    title : str | None
        An optional title
    resize_rows : bool
        Set True to resize the rows to contents
    resize_columns : bool
        Set True to resize the columns to contents
    verbose : bool
        Set True to see debugging for signals

    """

    def __init__(self, data=None, parent=None, title=None, resize_rows=False, resize_columns=False, verbose=False):
        super().__init__(model=BaseDictModel(data), view=QTableView(), parent=parent, title=title,
                         resize_rows=resize_rows, resize_columns=resize_columns, verbose=verbose)


class EditDict(BaseDict):
    """A Widget to display and edit a Dictionary

    Parameters
    ----------
    data : dict | None
        Input a pandas DataFrame with contents to display
    ui_buttons : bool
        If to display Buttons or not
    ui_button_pos: str
        The side on which to show the buttons, 'right', 'left', 'top' or 'bottom'
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent
    title : str | None
        An optional title
    resize_rows : bool
        Set True to resize the rows to contents
    resize_columns : bool
        Set True to resize the columns to contents
    verbose : bool
        Set True to see debugging for signals

    """

    def __init__(self, data=None, ui_buttons=True, ui_button_pos='right', parent=None, title=None,
                 resize_rows=False, resize_columns=False, verbose=False):

        self.ui_buttons = ui_buttons
        self.ui_button_pos = ui_button_pos

        super().__init__(model=EditDictModel(data), view=QTableView(), parent=parent, title=title,
                         resize_rows=resize_rows, resize_columns=resize_columns, verbose=verbose)

    def init_ui(self):
        if self.ui_button_pos in ['top', 'bottom']:
            layout = QVBoxLayout()
            bt_layout = QHBoxLayout()
        else:
            layout = QHBoxLayout()
            bt_layout = QVBoxLayout()

        if self.ui_buttons:
            addrow_bt = QPushButton('Add')
            addrow_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            addrow_bt.clicked.connect(self.add_row)
            bt_layout.addWidget(addrow_bt)

            rmrow_bt = QPushButton('Remove')
            rmrow_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            rmrow_bt.clicked.connect(self.remove_row)
            bt_layout.addWidget(rmrow_bt)

            edit_bt = QPushButton('Edit')
            edit_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            edit_bt.clicked.connect(self.edit_item)
            bt_layout.addWidget(edit_bt)

            layout.addLayout(bt_layout)

        if self.ui_button_pos in ['top', 'left']:
            layout.addWidget(self.view)
        else:
            layout.insertWidget(0, self.view)

        if self.title:
            super_layout = QVBoxLayout()
            title_label = QLabel(self.title)
            title_label.setFont(QFont('AnyStyle', 14))
            super_layout.addWidget(title_label)
            super_layout.addLayout(layout)
            self.setLayout(super_layout)
        else:
            self.setLayout(layout)

    def add_row(self):
        row = self.view.selectionModel().currentIndex().row() + 1
        if row == -1:
            row = 0
        self.model.insertRow(row)

    def remove_row(self):
        row_idxs = set([idx.row() for idx in self.view.selectionModel().selectedIndexes()])
        for row_idx in row_idxs:
            self.model.removeRow(row_idx)

    def edit_item(self):
        self.view.edit(self.view.selectionModel().currentIndex())


class BasePandasTable(Base):
    """
    The Base-Class for a table from a pandas DataFrame

    Parameters
    ----------
    model
        The model for the pandas DataFrame
    view
        The view for the pandas DataFrame
    title : str | None
        An optional title
    verbose : bool
        Set True to see debugging for signals
    """

    def __init__(self, model, view, parent, title, resize_rows=False, resize_columns=False, verbose=False):
        super().__init__(model, view, parent, title, verbose=verbose)
        self.verbose = verbose

        if resize_rows:
            model.layoutChanged.connect(self.view.resizeRowsToContents)
            model.layoutChanged.emit()
        if resize_columns:
            model.layoutChanged.connect(self.view.resizeColumnsToContents)
            model.layoutChanged.emit()

    def get_rowcol_by_index(self, index, data_list):
        """Get the data at index and the row and column of this data

        Parameters
        ----------
        index : QModelIndex
            The index to get data, row and column for
        data_list :
            The list in which the information about data, rows and columns is stored
        Notes
        -----
        Because this function is supposed to be called consecutively,
        the information is stored in an existing list (data_list)

        """
        data = self.model.getData(index)
        row = self.model.headerData(index.row(), orientation=Qt.Vertical, role=Qt.DisplayRole)
        column = self.model.headerData(index.column(), orientation=Qt.Horizontal, role=Qt.DisplayRole)

        data_list.append((data, row, column))

    def get_current(self):
        current_list = list()
        self.get_rowcol_by_index(self.view.currentIndex(), current_list)

        return current_list

    def _current_changed(self, current_idx, previous_idx):
        current_list = list()
        previous_list = list()

        self.get_rowcol_by_index(current_idx, current_list)
        self.get_rowcol_by_index(previous_idx, previous_list)

        self.currentChanged.emit(current_list, previous_list)

        if self.verbose:
            print(f'Current changed from {previous_list} to {current_list}')

    def get_selected(self):
        # Somehow, the indexes got from selectionChanged don't appear to be right
        # (maybe some issue with QItemSelection?)
        selection_list = list()
        for idx in self.view.selectedIndexes():
            self.get_rowcol_by_index(idx, selection_list)

        return selection_list

    def _selection_changed(self):
        selection_list = self.get_selected()
        self.selectionChanged.emit(selection_list)

        if self.verbose:
            print(f'Selection changed to {selection_list}')

    def select(self, values=None, rows=None, columns=None, clear_selection=True):
        """
        Select items in Pandas DataFrame by value or select complete rows/columns

        Parameters
        ----------
        values: list | None
            Names of values in DataFrame
        rows: list | None
            Names of rows(index)
        columns: list | None
            Names of columns
        clear_selection: bool | None
            Set True if you want to clear the selection before selecting

        """
        indexes = list()
        # Get indexes for matching items in pd_data (even if there are multiple matches)
        if values:
            for value in values:
                row, column = np.nonzero((self.model._data == value).values)
                for idx in zip(row, column):
                    indexes.append(idx)

        # Select complete rows
        if rows:
            # Convert names into indexes
            row_idxs = [list(self.model._data.index).index(row) for row in rows]
            n_cols = len(self.model._data.columns)
            for row in row_idxs:
                for idx in zip(itertools.repeat(row, n_cols), range(n_cols)):
                    indexes.append(idx)

        # Select complete columns
        if columns:
            # Convert names into indexes
            column_idxs = [list(self.model._data.columns).index(col) for col in columns]
            n_rows = len(self.model._data.index)
            for column in column_idxs:
                for idx in zip(range(n_rows), itertools.repeat(column, n_rows)):
                    indexes.append(idx)

        if clear_selection:
            self.view.selectionModel().clearSelection()

        for row, column in indexes:
            index = self.model.createIndex(row, column)
            self.view.selectionModel().select(index, QItemSelectionModel.Select)


class SimplePandasTable(BasePandasTable):
    """A Widget to display a pandas DataFrame

    Parameters
    ----------
    data : pandas.DataFrame | None
        Input a pandas DataFrame with contents to display
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent
    title : str | None
        An optional title
    resize_rows : bool
        Set True to resize the rows to contents
    resize_columns : bool
        Set True to resize the columns to contents
    verbose : bool
        Set True to see debugging for signals

    Notes
    -----
    If you change the Reference to data outside of this class,
    give the changed DataFrame to replace_data to update this widget
    """

    def __init__(self, data=None, parent=None, title=None, resize_rows=False, resize_columns=False, verbose=False):
        super().__init__(model=BasePandasModel(data), view=QTableView(), parent=parent, title=title,
                         resize_rows=resize_rows, resize_columns=resize_columns, verbose=verbose)


class EditPandasTable(BasePandasTable):
    """A Widget to display and edit a pandas DataFrame

    Parameters
    ----------
    data : pandas.DataFrame | None
        Input a pandas DataFrame with contents to display
    ui_buttons : bool
        If to display Buttons or not
    ui_button_pos: str
        The side on which to show the buttons, 'right', 'left', 'top' or 'bottom'
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent
    title : str | None
        An optional title
    resize_rows : bool
        Set True to resize the rows to contents
    resize_columns : bool
        Set True to resize the columns to contents
    verbose : bool
        Set True to see debugging for signals

    Notes
    -----
    If you change the Reference to data outside of this class,
    give the changed DataFrame to replace_data to update this widget
    """

    def __init__(self, data=None, ui_buttons=True, ui_button_pos='right', parent=None, title=None, resize_rows=False,
                 resize_columns=False, verbose=False):

        self.ui_buttons = ui_buttons
        self.ui_button_pos = ui_button_pos

        super().__init__(model=EditPandasModel(data), view=QTableView(), parent=parent, title=title,
                         resize_rows=resize_rows, resize_columns=resize_columns, verbose=verbose)

    def init_ui(self):
        if self.ui_button_pos in ['top', 'bottom']:
            layout = QVBoxLayout()
            bt_layout = QHBoxLayout()
        else:
            layout = QHBoxLayout()
            bt_layout = QVBoxLayout()

        if self.ui_buttons:
            addr_layout = QHBoxLayout()
            addr_bt = QPushButton('Add Row')
            addr_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            addr_bt.clicked.connect(self.add_row)
            addr_layout.addWidget(addr_bt)
            self.rows_chkbx = QSpinBox()
            self.rows_chkbx.setMinimum(1)
            addr_layout.addWidget(self.rows_chkbx)
            bt_layout.addLayout(addr_layout)

            addc_layout = QHBoxLayout()
            addc_bt = QPushButton('Add Column')
            addc_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            addc_bt.clicked.connect(self.add_column)
            addc_layout.addWidget(addc_bt)
            self.cols_chkbx = QSpinBox()
            self.cols_chkbx.setMinimum(1)
            addc_layout.addWidget(self.cols_chkbx)
            bt_layout.addLayout(addc_layout)

            rmr_bt = QPushButton('Remove Row')
            rmr_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            rmr_bt.clicked.connect(self.remove_row)
            bt_layout.addWidget(rmr_bt)

            rmc_bt = QPushButton('Remove Column')
            rmc_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            rmc_bt.clicked.connect(self.remove_column)
            bt_layout.addWidget(rmc_bt)

            edit_bt = QPushButton('Edit')
            edit_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            edit_bt.clicked.connect(self.edit_item)
            bt_layout.addWidget(edit_bt)

            editrh_bt = QPushButton('Edit Row-Header')
            editrh_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            editrh_bt.clicked.connect(self.edit_row_header)
            bt_layout.addWidget(editrh_bt)

            editch_bt = QPushButton('Edit Column-Header')
            editch_bt.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            editch_bt.clicked.connect(self.edit_col_header)
            bt_layout.addWidget(editch_bt)

            layout.addLayout(bt_layout)

        if self.ui_button_pos in ['top', 'left']:
            layout.addWidget(self.view)
        else:
            layout.insertWidget(0, self.view)

        if self.title:
            super_layout = QVBoxLayout()
            title_label = QLabel(self.title)
            title_label.setFont(QFont('AnyStyle', 14))
            super_layout.addWidget(title_label)
            super_layout.addLayout(layout)
            self.setLayout(super_layout)
        else:
            self.setLayout(layout)

    def update_data(self):
        """Has to be called, when model._data is rereferenced by for example add_row to keep external data updated

        Returns
        -------
        data : pandas.DataFrame
            The DataFrame of this widget

        Notes
        -----
        You can overwrite this function in a subclass e.g. to update an objects attribute
        (e.g. obj.data = self.model._data)
        """

        return self.model._data

    def add_row(self):
        row = self.view.selectionModel().currentIndex().row() + 1
        # Add row at the bottom if nothing is selected
        if row == -1 or len(self.view.selectionModel().selectedIndexes()) == 0:
            row = 0
        self.model.insertRows(row, self.rows_chkbx.value())
        self.update_data()

    def add_column(self):
        column = self.view.selectionModel().currentIndex().column() + 1
        # Add column to the right if nothing is selected
        if column == -1 or len(self.view.selectionModel().selectedIndexes()) == 0:
            column = 0
        self.model.insertColumns(column, self.cols_chkbx.value())
        self.update_data()

    def remove_row(self):
        rows = sorted(set([ix.row() for ix in self.view.selectionModel().selectedIndexes()]), reverse=True)
        for row in rows:
            self.model.removeRow(row)
        self.update_data()

    def remove_column(self):
        columns = sorted(set([ix.column() for ix in self.view.selectionModel().selectedIndexes()]), reverse=True)
        for column in columns:
            self.model.removeColumn(column)
        self.update_data()

    def edit_item(self):
        self.view.edit(self.view.selectionModel().currentIndex())

    def edit_row_header(self):
        row = self.view.selectionModel().currentIndex().row()
        old_value = self.model._data.index[row]
        text, ok = QInputDialog.getText(self, 'Change Row-Header', f'Change {old_value} in row {row} to:')
        if text and ok:
            self.model.setHeaderData(row, Qt.Vertical, text)

    def edit_col_header(self):
        column = self.view.selectionModel().currentIndex().column()
        old_value = self.model._data.columns[column]
        text, ok = QInputDialog.getText(self, 'Change Column-Header', f'Change {old_value} in column {column} to:')
        if text and ok:
            self.model.setHeaderData(column, Qt.Horizontal, text)


class FilePandasTable(BasePandasTable):
    """A Widget to display the files in a table (stored in a pandas DataFrame)

    Parameters
    ----------
    data : pandas.DataFrame | None
        Input a pandas DataFrame with contents to display
    parent : QWidget | None
        Parent Widget (QWidget or inherited) or None if there is no parent
    title : str | None
        An optional title
    verbose : bool
        Set True to see debugging for signals

    Notes
    -----
    If you change the Reference to data outside of this class,
    give the changed DataFrame to replace_data to update this widget
    """

    def __init__(self, data=None, parent=None, title=None, verbose=False):
        super().__init__(model=FileManagementModel(data), view=QTableView(), parent=parent, title=title,
                         resize_rows=True, resize_columns=True, verbose=verbose)


class SimpleDialog(QDialog):
    def __init__(self, widget, parent=None, modal=True, scroll=False, title=None, show_close_bt=True):
        super().__init__(parent)

        layout = QVBoxLayout()

        if title:
            layout.addWidget(QLabel(title))

        if scroll:
            scroll_area = QScrollArea()
            scroll_area.setWidget(widget)
            layout.addWidget(scroll_area)
        else:
            layout.addWidget(widget)

        if show_close_bt:
            close_bt = QPushButton('Close')
            close_bt.clicked.connect(self.close)
            layout.addWidget(close_bt)

        self.setLayout(layout)

        if modal:
            self.open()
        else:
            self.show()


class AssignWidget(QWidget):
    """

    """

    def __init__(self, items, properties, assignments, properties_editable=False,
                 parent=None, title=None, verbose=False):
        super().__init__(parent)
        self.title = title
        self.verbose = verbose

        self.items = items
        self.props = properties
        self.assignments = assignments
        self.props_editable = properties_editable

        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()

        self.items_w = CheckDictList(self.items, self.assignments, extended_selection=True, verbose=self.verbose)
        self.items_w.selectionChanged.connect(self.items_selected)
        layout.addWidget(self.items_w, 0, 0)

        if self.props_editable:
            self.props_w = EditList(self.props, extended_selection=False, verbose=self.verbose)
        else:
            self.props_w = SimpleList(self.props, extended_selection=False, verbose=self.verbose)
        layout.addWidget(self.props_w, 0, 1)

        assign_bt = QPushButton('Assign')
        assign_bt.setFont(QFont('AnyStyle', 13))
        assign_bt.clicked.connect(self.assign)
        layout.addWidget(assign_bt, 1, 0, 1, 2)

        show_assign_bt = QPushButton('Show Assignments')
        show_assign_bt.setFont(QFont('AnyStyle', 13))
        show_assign_bt.clicked.connect(self.show_assignments)
        layout.addWidget(show_assign_bt, 2, 0, 1, 2)

        if self.title:
            super_layout = QVBoxLayout()
            title_label = QLabel(self.title)
            title_label.setFont(QFont('AnyStyle', 14))
            super_layout.addWidget(title_label)
            super_layout.addLayout(layout)
            self.setLayout(super_layout)
        else:
            self.setLayout(layout)

    def items_selected(self, selected):
        # Get all unique values of selected items
        values = set([self.assignments[key] for key in selected if key in self.assignments])
        self.props_w.select(values)

    def assign(self):
        sel_items = self.items_w.get_selected()
        sel_prop = self.props_w.get_current()

        for item in sel_items:
            self.assignments[item] = sel_prop

        # Inform Model in CheckDict about change
        self.items_w.content_changed()

    def show_assignments(self):
        SimpleDialog(SimpleDict(self.assignments), parent=self, modal=False, scroll=True)


class AllBaseWidgets(QWidget):
    def __init__(self):
        super().__init__()

        self.exlist = ['Athena', 'Hephaistos', 'Zeus', 'Ares', 'Aphrodite', 'Poseidon']
        self.exattributes = ['strong', 'smart', 'bossy', 'fishy']
        self.exassignments = {'Athena': 'smart',
                              'Hephaistos': 'strong',
                              'Zeus': 'bossy',
                              'Poseidon': 'fishy'}
        self.exdict = {'Athena': 231,
                       'Hephaistos': 44,
                       'Zeus': 'Boss',
                       'Ares': 'War'}
        self.exchecked = ['Athena']
        self.expd = pandas.DataFrame([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]], columns=['A', 'B', 'C', 'D'])
        self.extree = {'A': {'Aa': 1,
                             'Ab': {'Ab1': 'Hermes',
                                    'Ab2': 'Hades'},
                             'Ac': [1, 2, 3, 4]},
                       'B': ['Appolo', 42, 128],
                       'C': (1, 2, 3)}

        # self.exlist = None
        # self.exattributes = None
        # self.exchecked = None
        # self.expd = None
        # self.extree = None
        # self.exdict = None

        self.widget_args = {'SimpleList': [self.exlist],
                            'EditList': [self.exlist],
                            'CheckList': [self.exlist, self.exchecked],
                            'CheckDictList': [self.exlist, self.exdict],
                            'CheckDictEditList': [self.exlist, self.exdict],
                            'SimpleDict': [self.exdict],
                            'EditDict': [self.exdict],
                            'SimplePandasTable': [self.expd],
                            'EditPandasTable': [self.expd],
                            'AssignWidget': [self.exlist, self.exattributes, self.exassignments]}

        self.widget_kwargs = {'SimpleList': {'extended_selection': True, 'title': 'BaseList', 'verbose': True},
                              'EditList': {'ui_button_pos': 'bottom', 'extended_selection': True, 'title': 'EditList',
                                           'verbose': True},
                              'CheckList': {'one_check': False, 'title': 'CheckList', 'verbose': True},
                              'CheckDictList': {'extended_selection': True, 'title': 'CheckDictList', 'verbose': True},
                              'CheckDictEditList': {'title': 'CheckDictEditList', 'verbose': True},
                              'SimpleDict': {'title': 'BaseDict', 'verbose': True},
                              'EditDict': {'ui_button_pos': 'left', 'title': 'EditDict', 'verbose': True},
                              'SimplePandasTable': {'title': 'BasePandasTable', 'verbose': True},
                              'EditPandasTable': {'title': 'EditPandasTable', 'verbose': True},
                              'AssignWidget': {'properties_editable': True, 'title': 'AssignWidget', 'verbose': True}}

        self.tab_widget = QTabWidget()

        self.init_ui()

        self.setGeometry(0, 0, 800, 400)

    def init_ui(self):
        layout = QVBoxLayout()
        for widget_name in self.widget_args:
            widget = globals()[widget_name](*self.widget_args[widget_name], **self.widget_kwargs[widget_name])
            setattr(self, widget_name, widget)
            self.tab_widget.addTab(widget, widget_name)

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    testw = AllBaseWidgets()
    testw.show()

    # Command-Line interrupt with Ctrl+C possible, easier debugging
    timer = QTimer()
    timer.timeout.connect(lambda: testw)
    timer.start(500)

    sys.exit(app.exec())
