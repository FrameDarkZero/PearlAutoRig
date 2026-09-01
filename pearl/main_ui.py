try:
    from PySide2 import QtWidgets
    from PySide2 import QtCore
    from PySide2 import QtGui
    from shiboken2 import wrapInstance
    from PySide2.QtWidgets import QAction

except ImportError:
    from PySide6 import QtWidgets
    from PySide6 import QtCore
    from PySide6 import QtGui
    from shiboken6 import wrapInstance
    from PySide6.QtGui import QAction

import maya.cmds as cmds
import maya.OpenMaya as om
import maya.OpenMayaUI as omui

import sys

from PearlAutoRig.pearl.arm_locator_ui import ArmLocatorUI
from PearlAutoRig.pearl.joint_ui import JointUI


LOCATOR_UI_REGISTRY = {
    "Left_Biped_Arm": ArmLocatorUI,
}


def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


class CollapsiblePage(QtWidgets.QWidget):
    """Top-level expandable page used by MainUI."""

    toggled = QtCore.Signal(bool)

    def __init__(self, title="", expanded=True, scrollable=False, parent=None):
        super().__init__(parent)

        self.scrollable = scrollable

        self.toggle_button = QtWidgets.QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(expanded)
        self.toggle_button.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )
        self.toggle_button.setArrowType(
            QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow
        )
        self.toggle_button.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed
        )
        self.toggle_button.setCursor(QtCore.Qt.PointingHandCursor)

        self.content_widget = QtWidgets.QWidget()

        if scrollable:
            self.content_container = QtWidgets.QScrollArea()
            self.content_container.setWidgetResizable(True)
            self.content_container.setFrameShape(QtWidgets.QFrame.NoFrame)
            self.content_container.setHorizontalScrollBarPolicy(
                QtCore.Qt.ScrollBarAlwaysOff
            )
            self.content_container.setVerticalScrollBarPolicy(
                QtCore.Qt.ScrollBarAsNeeded
            )
            self.content_container.setWidget(self.content_widget)
            self.content_container.setStyleSheet("""
                QScrollArea {
                    background: transparent;
                    border: none;
                }
                QScrollArea > QWidget > QWidget {
                    background: transparent;
                }
            """)
        else:
            self.content_container = self.content_widget

        self.content_container.setVisible(expanded)

        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_container)

        self.toggle_button.toggled.connect(self.on_toggled)

        self.setStyleSheet("""
            QToolButton {
                background-color: rgb(58, 58, 58);
                border: 1px solid rgb(90, 90, 90);
                border-radius: 6px;
                color: rgb(220, 220, 220);
                font-weight: bold;
                text-align: left;
                padding: 6px 8px;
            }
            QToolButton:hover {
                background-color: rgb(66, 66, 66);
            }
        """)

        self.on_toggled(expanded)

    @QtCore.Slot(bool)
    def on_toggled(self, checked):
        self.toggle_button.setArrowType(
            QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow
        )
        self.content_container.setVisible(checked)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
            if checked else QtWidgets.QSizePolicy.Maximum
        )

        self.updateGeometry()
        self.toggled.emit(checked)

    def set_content_widget(self, widget):
        self.content_layout.addWidget(widget)

    def apply_scrollbar_style(self, show_arrow_buttons=True):
        if not (
            self.scrollable
            and isinstance(self.content_container, QtWidgets.QScrollArea)
        ):
            return

        scroll_bar = self.content_container.verticalScrollBar()
        scroll_bar.setFixedWidth(14)

        if show_arrow_buttons:
            scroll_bar.setStyleSheet("""
                QScrollBar:vertical {
                    background: transparent;
                    width: 14px;
                    margin: 16px 0 16px 0;
                }
                QScrollBar::handle:vertical {
                    background: rgb(200, 140, 80);
                    border-radius: 4px;
                    min-height: 24px;
                }
                QScrollBar::handle:vertical:hover,
                QScrollBar::handle:vertical:pressed {
                    background: rgb(120, 160, 220);
                }
                QScrollBar::sub-line:vertical,
                QScrollBar::add-line:vertical {
                    background: rgb(140, 155, 150);
                    height: 16px;
                    subcontrol-origin: margin;
                    border-radius: 4px;
                }
                QScrollBar::sub-line:vertical {
                    subcontrol-position: top;
                }
                QScrollBar::add-line:vertical {
                    subcontrol-position: bottom;
                }
                QScrollBar::up-arrow:vertical,
                QScrollBar::down-arrow:vertical,
                QScrollBar::sub-page:vertical,
                QScrollBar::add-page:vertical {
                    background: transparent;
                }
            """)
        else:
            scroll_bar.setStyleSheet("""
                QScrollBar:vertical {
                    background: transparent;
                    width: 14px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: rgb(200, 140, 80);
                    border-radius: 4px;
                    min-height: 24px;
                }
                QScrollBar::handle:vertical:hover,
                QScrollBar::handle:vertical:pressed {
                    background: rgb(120, 160, 220);
                }
                QScrollBar::sub-line:vertical,
                QScrollBar::add-line:vertical,
                QScrollBar::up-arrow:vertical,
                QScrollBar::down-arrow:vertical,
                QScrollBar::sub-page:vertical,
                QScrollBar::add-page:vertical {
                    background: transparent;
                    height: 0px;
                }
            """)


class MainUI(QtWidgets.QWidget):
    """PEARL UI shell. Locator/Joints pages are supplied by separate widgets."""

    def __init__(self, parent=maya_main_window()):
        super().__init__(parent)

        self.setWindowFlags(QtCore.Qt.WindowType.Window)
        self.setWindowTitle("Joint Chain Builder")
        self.setMinimumSize(510, 565)

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(50, 50, 50))
        self.setPalette(palette)

        if sys.platform == "darwin":
            self.setWindowFlag(QtCore.Qt.Tool, True)

        self.builder = None
        self.locator_module = None
        self.current_locator_ui = None
        self.locator_ui_instances = {}
        
        self.create_actions()
        self.create_widgets()
        self.create_layout()
        self.create_connections()

        self.load_locator_ui(self.loc_module_combo_box.currentText().strip())
    
    # ------------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------------
    def create_actions(self):
        self.reset_settings_action = QAction("Reset Settings", self)
    
    # ------------------------------------------------------------------
    # WIDGETS / LAYOUT
    # ------------------------------------------------------------------
    def create_widgets(self):
        self.menu_bar = QtWidgets.QMenuBar()
        edit_menu = self.menu_bar.addMenu("Edit")
        edit_menu.addAction(self.reset_settings_action)
        
        self.locators_tab_widget = QtWidgets.QWidget()
        self.joints_tab_widget = QtWidgets.QWidget()

        self.locators_page = CollapsiblePage(
            "Locators",
            expanded=True,
            scrollable=True
        )
        self.joints_page = CollapsiblePage(
            "Joints",
            expanded=False,
            scrollable=True
        )

        self.locators_page.set_content_widget(self.locators_tab_widget)
        self.joints_page.set_content_widget(self.joints_tab_widget)

        self.loc_module_combo_box = QtWidgets.QComboBox()
        self.loc_module_combo_box.addItems(sorted(LOCATOR_UI_REGISTRY.keys()))
        self.loc_module_combo_box.setCurrentText("Left_Biped_Arm")

        palette = self.loc_module_combo_box.palette()
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(43, 43, 43))
        self.loc_module_combo_box.setPalette(palette)

        self.locator_ui_stack = QtWidgets.QStackedWidget()
        self.joint_ui = JointUI(parent=self.joints_tab_widget)
        self.cancel_btn = QtWidgets.QPushButton("Cancel")

    def create_layout(self):
        module_form_layout = QtWidgets.QFormLayout()
        module_form_layout.setContentsMargins(4, 0, 0, 0)
        module_form_layout.addRow("Locator Type:", self.loc_module_combo_box)

        locator_type_group = self.build_group_section(
            "Locator Type",
            module_form_layout
        )

        locators_tab_layout = QtWidgets.QVBoxLayout(self.locators_tab_widget)
        locators_tab_layout.setContentsMargins(8, 8, 8, 8)
        locators_tab_layout.setSpacing(8)
        locators_tab_layout.addWidget(locator_type_group)
        locators_tab_layout.addWidget(self.locator_ui_stack)

        joints_tab_layout = QtWidgets.QVBoxLayout(self.joints_tab_widget)
        joints_tab_layout.setContentsMargins(8, 8, 8, 8)
        joints_tab_layout.setSpacing(8)
        joints_tab_layout.addWidget(self.joint_ui)

        pages_layout = QtWidgets.QVBoxLayout()
        pages_layout.setContentsMargins(0, 0, 0, 0)
        pages_layout.setSpacing(8)
        pages_layout.addWidget(self.locators_page, 1)
        pages_layout.addWidget(self.joints_page, 1)
        pages_layout.addStretch()

        main_btn_layout = QtWidgets.QHBoxLayout()
        main_btn_layout.setContentsMargins(0, 10, 0, 5)
        main_btn_layout.setSpacing(6)
        main_btn_layout.addStretch()
        main_btn_layout.addWidget(self.cancel_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        main_layout.setMenuBar(self.menu_bar)
        main_layout.addLayout(pages_layout)
        main_layout.addLayout(main_btn_layout)

        self.locators_page.apply_scrollbar_style(show_arrow_buttons=True)
        self.joints_page.apply_scrollbar_style(show_arrow_buttons=True)

    def create_connections(self):
        self.loc_module_combo_box.currentTextChanged.connect(
            self.on_loc_module_changed
        )
        self.joint_ui.settings_changed.connect(
            self.on_joint_settings_changed
        )
        self.joint_ui.joints_constructed.connect(
            self.on_joints_constructed
        )
        self.cancel_btn.clicked.connect(self.close)

    def build_group_section(self, title, inner_layout):
        group_box = QtWidgets.QGroupBox(title)
        group_box.setStyleSheet("""
            QGroupBox {
                background-color: rgb(50, 50, 50);
                border: 1px solid rgb(90, 90, 90);
                border-radius: 6px;
                margin-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)

        layout = QtWidgets.QVBoxLayout(group_box)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(6)
        layout.addLayout(inner_layout)
        return group_box

    # ------------------------------------------------------------------
    # UI ROUTING
    # ------------------------------------------------------------------
    def load_locator_ui(self, locator_type):
        ui_class = LOCATOR_UI_REGISTRY.get(locator_type)

        if not ui_class:
            om.MGlobal.displayWarning(
                "No locator UI registered for: {}".format(locator_type)
            )
            self.current_locator_ui = None
            self.joint_ui.clear_active_locator()
            return

        locator_ui = self.locator_ui_instances.get(locator_type)

        if locator_ui is None:
            locator_ui = ui_class(
                parent=self.locator_ui_stack,
                loc_type=locator_type
            )
            locator_ui.set_joint_settings(self.joint_ui.get_settings())

            locator_ui.active_locator_changed.connect(
                self.on_active_locator_changed
            )
            locator_ui.active_locator_cleared.connect(
                self.on_active_locator_cleared
            )

            self.locator_ui_instances[locator_type] = locator_ui
            self.locator_ui_stack.addWidget(locator_ui)

        self.current_locator_ui = locator_ui
        self.locator_ui_stack.setCurrentWidget(locator_ui)

        if (
            locator_ui.locator_module
            and locator_ui.builder
            and locator_ui.current_locator_root
        ):
            module_data = locator_ui.locator_module_data.get(
                locator_ui.current_locator_root,
                {}
            )
            self.on_active_locator_changed(
                locator_ui.locator_module,
                module_data,
                locator_ui.current_locator_root
            )
        else:
            self.builder = None
            self.locator_module = None
            self.joint_ui.clear_active_locator()

    @QtCore.Slot(str)
    def on_loc_module_changed(self, text):
        self.load_locator_ui(text.strip())

    @QtCore.Slot(object, object, object)
    def on_active_locator_changed(
        self,
        locator_module,
        module_data,
        locator_root
    ):
        self.locator_module = locator_module
        self.builder = getattr(locator_module, "builder", None)
        self.joint_ui.set_active_locator(
            locator_module,
            module_data,
            locator_root
        )

    @QtCore.Slot()
    def on_active_locator_cleared(self):
        sender = self.sender()
        if sender is not None and sender is not self.current_locator_ui:
            return

        self.builder = None
        self.locator_module = None
        self.joint_ui.clear_active_locator()

    @QtCore.Slot(object)
    def on_joint_settings_changed(self, settings):
        if self.current_locator_ui:
            self.current_locator_ui.set_joint_settings(settings)

    @QtCore.Slot(str)
    def on_joints_constructed(self, locator_root):
        for locator_ui in self.locator_ui_instances.values():
            if locator_root in locator_ui.locator_module_data:
                locator_ui.handle_locator_consumed(locator_root)
                break

        self.builder = None
        self.locator_module = None

if __name__ == "__main__":    
    try:
        main_ui_instance.close()
        main_ui_instance.deleteLater()
    except (NameError, RuntimeError):
        pass

    main_ui_instance = MainUI()
    main_ui_instance.show()
    