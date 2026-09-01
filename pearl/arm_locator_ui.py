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

from PearlAutoRig.pearl.joint_chain_builder import JointChainBuilder
from PearlAutoRig.pearl.arm_module import ArmModule
from PearlAutoRig.pearl.locator_preset_manager import LocatorPresetManager

MODULE_REGISTRY = {
    "Left_Biped_Arm": ArmModule,
}

def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


class ColorIndexWidget(QtWidgets.QWidget):
    """Compact widget to display and scroll through Maya color indices 0-31"""

    color_index_changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.maya_colors = []
        for i in range(32):
            rgb = cmds.colorIndex(i, query=True)
            # Returns a list of 3 floats: [red, green, blue]
            # Each value is between 0.0 and 1.0
            self.maya_colors.append(
                QtGui.QColor(
                    int(rgb[0] * 255),
                    int(rgb[1] * 255),
                    int(rgb[2] * 255)
                )
            )
            # This converts Maya color -> QColor object.
            # Output example: QtGui.QColor(51, 127, 204).
            # Used for UI drawing.

        self.current_index = 13

        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.update_display()

    def create_widgets(self):
        self.color_display = QtWidgets.QLabel()
        self.color_display.setFixedSize(80, 20)
        self.color_display.setFrameStyle(QtWidgets.QFrame.Box)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0, 31)
        self.slider.setValue(self.current_index)
        self.slider.setPageStep(1)
        self.slider.setFixedHeight(16)
        self.slider.setFixedWidth(200)

    def create_layout(self):
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(self.color_display)
        main_layout.addWidget(self.slider)
        main_layout.addStretch()

    def create_connections(self):
        self.slider.valueChanged.connect(self.on_slider_changed)

    @QtCore.Slot(int)
    def on_slider_changed(self, value):
        self.current_index = value
        self.update_display()
        self.color_index_changed.emit(self.current_index)

    def update_display(self):
        color = self.maya_colors[self.current_index]
        pixmap = QtGui.QPixmap(self.color_display.size())
        pixmap.fill(color)
        self.color_display.setPixmap(pixmap)
        self.color_display.setFrameStyle(QtWidgets.QFrame.NoFrame)

        rgb = (color.red(), color.green(), color.blue()) # (51, 127, 204)
        maya_rgb = self.get_maya_rgb_format()
        self.color_display.setToolTip(
            f"Color Index: {self.current_index}\nRGB: {rgb}\nMaya RGB: {maya_rgb}"
        )
        self.slider.setToolTip(
            f"Slide to change color index (0-31)\nCurrent: {self.current_index}"
        )

    def get_current_index(self):
        return self.current_index

    def get_current_color(self):
        return self.maya_colors[self.current_index]

    def get_current_rgb(self):
        color = self.maya_colors[self.current_index]
        return (color.red(), color.green(), color.blue())

    def get_maya_rgb_format(self):
        color = self.maya_colors[self.current_index]
        r = color.red() / 255.0
        g = color.green() / 255.0
        b = color.blue() / 255.0
        return f"[{r:.3f}, {g:.3f}, {b:.3f}]"
        # Converts back from rgb to Maya color (0-1).

    def set_index(self, index):
        self.slider.setValue(max(0, min(31, index)))
        # min(31, index) gives you the smallest of the two values. Capping the maximum value at 31.
        # max(0, result_from_above) gives you the largest of the two values. Capping the minimum value at 0.


class CollapsiblePage(QtWidgets.QWidget):
    """Top-level collapsible section for Locators / Joints only."""

    toggled = QtCore.Signal(bool)

    def __init__(self, title="", expanded=True, scrollable=False, parent=None):
        super().__init__(parent)

        self.scrollable = scrollable
        
        if expanded:
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding
            )
        else:
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Maximum
            )

        self.toggle_button = QtWidgets.QToolButton()
        # Clickable top bar. We are using the QToolButton as the section header.
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(expanded)
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(
            QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow
        )
        self.toggle_button.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed
        )
        # This controls button resizing.
        # (Horizontal, Vertical)
        # Horizontal = Expanding. The button stretches across available width.
        # Vertical = Fixed. The height stays stable.
        self.toggle_button.setCursor(QtCore.Qt.PointingHandCursor)

        self.content_widget = QtWidgets.QWidget()

        if self.scrollable:
            self.content_container = QtWidgets.QScrollArea()
            # Instead of showing content directly, we wrap it in a scroll area.
            self.content_container.setWidgetResizable(True)
            # The widget inside the scroll area should resize with the scroll area.
            self.content_container.setFrameShape(QtWidgets.QFrame.NoFrame)
            self.content_container.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.content_container.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
            # Only show scroll bar if content is taller than available space.
            self.content_container.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding
            )
            self.content_container.setWidget(self.content_widget)
            self.content_container.setVisible(expanded)
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

    @QtCore.Slot(bool)
    def on_toggled(self, checked):
        self.toggle_button.setArrowType(
            QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow
        )
        self.content_container.setVisible(checked)
        
        if checked:
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding
            )
        else:
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Maximum
            )
        
        self.updateGeometry() # recalculates layout
        self.toggled.emit(checked)

    def set_content_widget(self, widget):
        self.content_layout.addWidget(widget)

    def set_expanded(self, state):
        self.toggle_button.setChecked(state)
        # Because changing checked state triggers toggled, it also runs on_toggled.

    def is_expanded(self):
        return self.toggle_button.isChecked()
        # This asks: "Are you currently open?" Returns True or False. Useful to inspect current state.

    def set_scroll_max_height(self, height):
        if self.scrollable and isinstance(self.content_container, QtWidgets.QScrollArea):
            # This asks:
                # "Only set the max height IF:
                    # 1) This page is scrollable 
                    # AND
                    # 2) The container is actually a QScrollArea.
            # isinstance asks: "Is this object an instance of this class?" Returns a boolean.
            self.content_container.setMaximumHeight(height)
    
    def vertical_scrollbar(self):
        """Return the vertical scrollbar if this page is scrollable."""
        if self.scrollable and isinstance(self.content_container, QtWidgets.QScrollArea):
            return self.content_container.verticalScrollBar()
        return None

    def apply_scrollbar_style(self, show_arrow_buttons=True):
        """
        Apply a styled vertical scrollbar.
        If show_arrow_buttons=True, top and bottom arrow-button regions are styled too.
        """
        if not (self.scrollable and isinstance(self.content_container, QtWidgets.QScrollArea)):
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

                QScrollBar::handle:vertical:hover {
                    background: rgb(120, 160, 220);
                }

                QScrollBar::handle:vertical:pressed {
                    background: rgb(120, 160, 220);
                }

                QScrollBar::sub-line:vertical {
                    background: rgb(140, 155, 150);
                    height: 16px;
                    subcontrol-position: top;
                    subcontrol-origin: margin;
                    border-radius: 4px;
                }

                QScrollBar::add-line:vertical {
                    background: rgb(140, 155, 150);
                    height: 16px;
                    subcontrol-position: bottom;
                    subcontrol-origin: margin;
                    border-radius: 4px;
                }

                QScrollBar::up-arrow:vertical,
                QScrollBar::down-arrow:vertical {
                    width: 8px;
                    height: 8px;
                    background: transparent;
                }

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

                QScrollBar::handle:vertical:hover {
                    background: rgb(120, 160, 220);
                }

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
            
            # sub-line = top button
            # add-line = bottom button
            # up-arrow = top button arrow
            # down-arrow = bottom button arrow

class ArmLocatorUI(QtWidgets.QWidget):

    active_locator_changed = QtCore.Signal(object, object, object)
    active_locator_cleared = QtCore.Signal()

    GEOMETRY_OPT_VAR = "gianJointChainBuilderGeometry"
    OPT_PREFIX = "gian_joint_chain_builder_"

    VALID_CTRL_TYPES = [
        "circle_01",
        "circle_02",
        "circle_03",
        "sphere",
        "square",
        "cube",
        "diamond",
        "four_way_arrow"
    ]

    VALID_COLORS = range(0, 32)

    VALID_MODULES = [
        "Left_Biped_Arm",
    ]

    def __init__(self, parent=None, loc_type="Left_Biped_Arm"):
        super().__init__(parent)

        self.loc_type = loc_type

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(50, 50, 50))
        self.setPalette(palette)

        # Core builder/module state for the active arm locator rig.
        self.builder = None
        self.locator_module = None

        # Per-locator cached module data. This remains here because the locator UI
        # is the owner of locator creation, pose rebuilding, and locator selection.
        self.locator_result = {}
        self.locator_module_data = {}
        self.current_locator_root = None

        # Joint settings are displayed in JointUI, but locator creation still needs
        # these values when ArmModule is instantiated. MainUI keeps the two UIs in sync.
        self.joint_settings = {
            "display_LRA": False,
            "joint_size": 1.0,
            "end_orient": "parent",
            "create_coplanar_mesh": False,
        }

        self.initialize_defaults()
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def emit_active_locator(self):
        if not self.locator_module or not self.builder or not self.current_locator_root:
            return

        module_data = self.locator_module_data.get(self.current_locator_root, {})
        self.active_locator_changed.emit(
            self.locator_module,
            module_data,
            self.current_locator_root
        )

    def set_joint_settings(self, settings):
        if not settings:
            return

        for key in self.joint_settings:
            if key in settings:
                self.joint_settings[key] = settings[key]

        self.display_LRA = self.joint_settings["display_LRA"]
        self.joint_size = self.joint_settings["joint_size"]
        self.end_orient = self.joint_settings["end_orient"]
        self.create_coplanar_mesh = self.joint_settings["create_coplanar_mesh"]

        if self.locator_module:
            self.locator_module.display_LRA = self.display_LRA
            self.locator_module.joint_size = self.joint_size
            self.locator_module.end_orient = self.end_orient
            self.locator_module.create_coplanar_mesh = self.create_coplanar_mesh

        if self.builder:
            self.builder.display_LRA = self.display_LRA
            self.builder.joint_size = self.joint_size
            self.builder.end_orient = self.end_orient
            self.builder.create_coplanar_mesh = self.create_coplanar_mesh

        if self.current_locator_root in self.locator_module_data:
            module_data = self.locator_module_data[self.current_locator_root]
            module_data.update(self.joint_settings)

    def handle_locator_consumed(self, locator_root):
        self.locator_module_data.pop(locator_root, None)

        if self.current_locator_root == locator_root:
            self.current_locator_root = None
            self.locator_result = {}
            self.builder = None
            self.locator_module = None

        self.refresh_locator_list()

    # ------------------------------------------------------------------
    # DEFAULTS
    # ------------------------------------------------------------------
    def initialize_defaults(self):
        self.loc_module = "Left_Biped_Arm"
        self.use_prefix = True
        self.use_clavicle = True
        self.use_fingers = True
        self.finger_segments = 3
        self.use_thumb = True

        self.name = "arm_01"
        self.prefix = "L"
        self.suffix = "jnt"

        self.ctrl_type = "sphere"
        self.ctrl_size = 1.0
        self.ctrl_color = 13

        self.root_type = "diamond"
        self.root_size = 2.0
        self.root_color = 27

        self.global_type = "four_way_arrow"
        self.global_size = 3.0
        self.global_color = 26

        self.arm_default_joints = ["clavicle", "shoulder", "elbow", "wrist"]
        self.orientation = "x"
        self.display_LRA = False
        self.loc_size = 1.0
        self.joint_size = 1.0
        self.distance_between = 3.0
        self.end_orient = "parent"
        self.create_coplanar_mesh = False
        self.helper_distance = 5.0
        
        self.position_preset = "A-Pose"
        self.default_pose_names = ["A-Pose", "T-Pose"]
        self.add_custom_pose_label = "Add Custom Pose"
        
        self.finger_orientation_mode = "propagated"
        # "propagated" = root uses sphere, rest follow root plane
        # "per_joint" = every joint uses sphere direction

    # ------------------------------------------------------------------
    # WIDGETS
    # ------------------------------------------------------------------
    def create_widgets(self):
        self.name_le = QtWidgets.QLineEdit(self.name)
        self.name_le.setFixedWidth(105)

        self.prefix_cb = QtWidgets.QCheckBox("Prefix:")
        self.prefix_cb.setChecked(self.use_prefix)

        self.prefix_le = QtWidgets.QLineEdit(self.prefix)
        self.prefix_le.setFixedWidth(50)
        self.prefix_le.setVisible(self.use_prefix)

        self.suffix_le = QtWidgets.QLineEdit(self.suffix)
        self.suffix_le.setFixedWidth(50)

        self.prefix_le.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Preferred
        )
        self.suffix_le.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Preferred
        )

        self.size_double_spin_box = QtWidgets.QDoubleSpinBox()
        self.size_double_spin_box.setFixedWidth(70)
        self.size_double_spin_box.setMinimum(0.001)
        self.size_double_spin_box.setMaximum(1000.0)
        self.size_double_spin_box.setValue(self.loc_size)
        self.size_double_spin_box.setSingleStep(0.1)

        self.ctrl_type_combo_box = QtWidgets.QComboBox()
        self.ctrl_type_combo_box.addItems(self.VALID_CTRL_TYPES)
        self.ctrl_type_combo_box.setCurrentText(self.ctrl_type)

        self.root_type_combo_box = QtWidgets.QComboBox()
        self.root_type_combo_box.addItems(self.VALID_CTRL_TYPES)
        self.root_type_combo_box.setCurrentText(self.root_type)

        self.global_type_combo_box = QtWidgets.QComboBox()
        self.global_type_combo_box.addItems(self.VALID_CTRL_TYPES)
        self.global_type_combo_box.setCurrentText(self.global_type)

        self.global_color_widget = ColorIndexWidget()
        self.global_color_widget.set_index(self.global_color)
        self.root_color_widget = ColorIndexWidget()
        self.root_color_widget.set_index(self.root_color)
        self.ctrl_color_widget = ColorIndexWidget()
        self.ctrl_color_widget.set_index(self.ctrl_color)

        self.ctrl_size_spin_box = QtWidgets.QDoubleSpinBox()
        self.ctrl_size_spin_box.setFixedWidth(70)
        self.ctrl_size_spin_box.setMinimum(0.1)
        self.ctrl_size_spin_box.setMaximum(1000.0)
        self.ctrl_size_spin_box.setValue(self.ctrl_size)
        self.ctrl_size_spin_box.setSingleStep(0.5)

        self.root_size_spin_box = QtWidgets.QDoubleSpinBox()
        self.root_size_spin_box.setFixedWidth(70)
        self.root_size_spin_box.setMinimum(0.1)
        self.root_size_spin_box.setMaximum(1000.0)
        self.root_size_spin_box.setValue(self.root_size)
        self.root_size_spin_box.setSingleStep(0.5)

        self.global_size_spin_box = QtWidgets.QDoubleSpinBox()
        self.global_size_spin_box.setFixedWidth(70)
        self.global_size_spin_box.setMinimum(0.1)
        self.global_size_spin_box.setMaximum(1000.0)
        self.global_size_spin_box.setValue(self.global_size)
        self.global_size_spin_box.setSingleStep(0.5)

        self.clavicle_cb = QtWidgets.QCheckBox("Clavicle:")
        self.clavicle_cb.setChecked(self.use_clavicle)
        self.clavicle_le = QtWidgets.QLineEdit()
        self.clavicle_le.setFixedWidth(80)
        self.shoulder_le = QtWidgets.QLineEdit()
        self.shoulder_le.setFixedWidth(80)
        self.elbow_le = QtWidgets.QLineEdit()
        self.elbow_le.setFixedWidth(80)
        self.wrist_le = QtWidgets.QLineEdit()
        self.wrist_le.setFixedWidth(80)

        self.fingers_cb = QtWidgets.QCheckBox("Fingers:")
        self.fingers_cb.setChecked(self.use_fingers)
        self.fingers_spin_box = QtWidgets.QSpinBox()
        self.fingers_spin_box.setFixedWidth(80)
        self.fingers_spin_box.setMinimum(1)
        self.fingers_spin_box.setMaximum(4)
        self.fingers_spin_box.setValue(4)

        self.finger_segments_spin_box = QtWidgets.QSpinBox()
        self.finger_segments_spin_box.setFixedWidth(80)
        self.finger_segments_spin_box.setMinimum(1)
        self.finger_segments_spin_box.setMaximum(3)
        self.finger_segments_spin_box.setValue(self.finger_segments)
        self.finger_segments_spin_box.setToolTip(
            "1 = base/end, 2 = base/mid/end, 3 = full finger chain"
        )

        self.thumb_cb = QtWidgets.QCheckBox("Thumb")
        self.thumb_cb.setChecked(self.use_thumb)

        self.arm_pose_list = QtWidgets.QListWidget()
        self.arm_pose_list.setFixedHeight(90)
        self.arm_pose_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.pose_name_le = QtWidgets.QLineEdit()
        self.pose_name_le.setPlaceholderText("Custom Pose Name")
        self.delete_pose_btn = QtWidgets.QPushButton("Delete Pose")
        self.save_pose_btn = QtWidgets.QPushButton("Save Pose")
        self.load_pose_btn = QtWidgets.QPushButton("Load Pose")

        self.current_locators_list = QtWidgets.QListWidget()
        self.current_locators_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.current_locators_list.setFixedHeight(90)
        self.current_locators_list.setAlternatingRowColors(True)
        self.current_locators_list.setToolTip("Click a created object to select it in Maya")

        self.delete_selected_btn = QtWidgets.QPushButton("Delete Selected Locator")
        self.delete_selected_btn.setEnabled(False)
        self.refresh_locators_btn = QtWidgets.QPushButton("Refresh List")
        self.refresh_locators_btn.setEnabled(False)

        self.orientation_combo_box = QtWidgets.QComboBox()
        self.orientation_combo_box.addItems([" X", " Y", " Z"])
        self.orientation_combo_box.setCurrentIndex(0)

        self.distance_spin_box = QtWidgets.QDoubleSpinBox()
        self.distance_spin_box.setFixedWidth(70)
        self.distance_spin_box.setMinimum(0.0)
        self.distance_spin_box.setMaximum(1000.0)
        self.distance_spin_box.setValue(self.distance_between)
        self.distance_spin_box.setSingleStep(0.5)

        self.create_locators_btn = QtWidgets.QPushButton("Create Locators")

        self.apply_palette_styling()
        self.refresh_arm_pose_list()
        self.refresh_locator_list()

    # ------------------------------------------------------------------
    # LAYOUT
    # ------------------------------------------------------------------
    def create_layout(self):
        names_layout = QtWidgets.QHBoxLayout()
        names_layout.setContentsMargins(4, 4, 4, 4)
        names_layout.setSpacing(8)
        names_layout.addWidget(QtWidgets.QLabel("Name:"))
        names_layout.addWidget(self.name_le)

        prefix_layout = QtWidgets.QHBoxLayout()
        prefix_layout.setContentsMargins(0, 0, 0, 0)
        prefix_layout.setSpacing(5)
        prefix_layout.addWidget(self.prefix_cb)
        prefix_layout.addWidget(self.prefix_le)

        suffix_layout = QtWidgets.QHBoxLayout()
        suffix_layout.setContentsMargins(0, 0, 0, 0)
        suffix_layout.setSpacing(5)
        suffix_layout.addWidget(QtWidgets.QLabel("Suffix:"))
        suffix_layout.addWidget(self.suffix_le)

        names_layout.addSpacing(10)
        names_layout.addLayout(prefix_layout)
        names_layout.addSpacing(8)
        names_layout.addLayout(suffix_layout)
        names_layout.addStretch()

        loc_settings_layout = QtWidgets.QHBoxLayout()
        loc_settings_layout.setContentsMargins(5, 0, 0, 0)
        loc_settings_layout.addWidget(QtWidgets.QLabel("Locator Size:"))
        loc_settings_layout.addWidget(self.size_double_spin_box)
        loc_settings_layout.addSpacing(25)
        loc_settings_layout.addWidget(QtWidgets.QLabel("Orient:"))
        loc_settings_layout.addWidget(self.orientation_combo_box)
        loc_settings_layout.addStretch()

        global_layout = QtWidgets.QHBoxLayout()
        global_layout.setContentsMargins(5, 10, 0, 0)
        global_layout.setSpacing(10)
        global_layout.addWidget(QtWidgets.QLabel("Global Type:"))
        global_layout.addWidget(self.global_type_combo_box)
        global_layout.addSpacing(20)
        global_layout.addWidget(QtWidgets.QLabel("Global Scale:"))
        global_layout.addWidget(self.global_size_spin_box)
        global_layout.addStretch()

        root_layout = QtWidgets.QHBoxLayout()
        root_layout.setContentsMargins(14, 20, 0, 0)
        root_layout.setSpacing(10)
        root_layout.addWidget(QtWidgets.QLabel("Root Type:"))
        root_layout.addWidget(self.root_type_combo_box)
        root_layout.addSpacing(28)
        root_layout.addWidget(QtWidgets.QLabel("Root Scale:"))
        root_layout.addWidget(self.root_size_spin_box)
        root_layout.addStretch()

        ctrl_row_layout = QtWidgets.QHBoxLayout()
        ctrl_row_layout.setContentsMargins(20, 20, 0, 0)
        ctrl_row_layout.setSpacing(10)
        ctrl_row_layout.addWidget(QtWidgets.QLabel("Ctrl Type:"))
        ctrl_row_layout.addWidget(self.ctrl_type_combo_box)
        ctrl_row_layout.addSpacing(35)
        ctrl_row_layout.addWidget(QtWidgets.QLabel("Ctrl Scale:"))
        ctrl_row_layout.addWidget(self.ctrl_size_spin_box)
        ctrl_row_layout.addStretch()

        ctrl_color_layout = QtWidgets.QFormLayout()
        ctrl_color_layout.setContentsMargins(5, 30, 0, 0)
        ctrl_color_layout.setSpacing(10)
        ctrl_color_layout.addRow("Global Color:", self.global_color_widget)
        ctrl_color_layout.addRow("Root Color:", self.root_color_widget)
        ctrl_color_layout.addRow("Ctrl Color:", self.ctrl_color_widget)

        ctrl_layout = QtWidgets.QVBoxLayout()
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(0)
        ctrl_layout.addLayout(global_layout)
        ctrl_layout.addLayout(root_layout)
        ctrl_layout.addLayout(ctrl_row_layout)
        ctrl_layout.addLayout(ctrl_color_layout)

        clavicle_layout = QtWidgets.QHBoxLayout()
        clavicle_layout.setContentsMargins(5, 0, 0, 0)
        clavicle_layout.setSpacing(10)
        clavicle_layout.addWidget(self.clavicle_cb)
        clavicle_layout.addWidget(self.clavicle_le)
        clavicle_layout.addStretch()

        shoulder_layout = QtWidgets.QHBoxLayout()
        shoulder_layout.setContentsMargins(14, 0, 0, 0)
        shoulder_layout.addWidget(QtWidgets.QLabel("Shoulder:"))
        shoulder_layout.addSpacing(10)
        shoulder_layout.addWidget(self.shoulder_le)
        shoulder_layout.addSpacing(60)
        shoulder_layout.addWidget(self.fingers_cb)
        shoulder_layout.addWidget(self.fingers_spin_box)
        shoulder_layout.addStretch()

        elbow_layout = QtWidgets.QHBoxLayout()
        elbow_layout.setContentsMargins(28, 0, 0, 0)
        elbow_layout.addWidget(QtWidgets.QLabel("Elbow:"))
        elbow_layout.addSpacing(11)
        elbow_layout.addWidget(self.elbow_le)
        elbow_layout.addSpacing(60)
        elbow_layout.addWidget(self.thumb_cb)
        elbow_layout.addStretch()

        wrist_layout = QtWidgets.QHBoxLayout()
        wrist_layout.setContentsMargins(33, 0, 0, 0)
        wrist_layout.addWidget(QtWidgets.QLabel("Wrist:"))
        wrist_layout.addSpacing(11)
        wrist_layout.addWidget(self.wrist_le)
        wrist_layout.addSpacing(67)
        wrist_layout.addWidget(QtWidgets.QLabel("Segments:"))
        wrist_layout.addSpacing(4)
        wrist_layout.addWidget(self.finger_segments_spin_box)
        wrist_layout.addStretch()

        arm_joint_layout = QtWidgets.QVBoxLayout()
        arm_joint_layout.setContentsMargins(0, 10, 0, 0)
        arm_joint_layout.setSpacing(5)
        arm_joint_layout.addLayout(clavicle_layout)
        arm_joint_layout.addLayout(shoulder_layout)
        arm_joint_layout.addLayout(elbow_layout)
        arm_joint_layout.addLayout(wrist_layout)

        arm_pose_layout = QtWidgets.QVBoxLayout()
        arm_pose_layout.setContentsMargins(0, 10, 0, 0)
        arm_pose_layout.setSpacing(10)
        arm_pose_layout.addWidget(QtWidgets.QLabel("Pose Presets:"))
        arm_pose_layout.addWidget(self.arm_pose_list)
        arm_pose_layout.addWidget(self.pose_name_le)

        pose_btn_layout = QtWidgets.QHBoxLayout()
        pose_btn_layout.addStretch()
        pose_btn_layout.addWidget(self.load_pose_btn)
        pose_btn_layout.addWidget(self.save_pose_btn)
        pose_btn_layout.addWidget(self.delete_pose_btn)
        arm_pose_layout.addLayout(pose_btn_layout)

        locator_list_layout = QtWidgets.QVBoxLayout()
        locator_list_layout.setContentsMargins(10, 10, 10, 10)
        locator_list_layout.setSpacing(10)
        locator_list_layout.addWidget(QtWidgets.QLabel("Created Locators:"))
        locator_list_layout.addWidget(self.current_locators_list)

        locator_btn_row = QtWidgets.QHBoxLayout()
        locator_btn_row.setContentsMargins(0, 0, 0, 0)
        locator_btn_row.setSpacing(6)
        locator_btn_row.addWidget(self.refresh_locators_btn)
        locator_btn_row.addWidget(self.delete_selected_btn)
        locator_btn_row.addStretch()
        locator_list_layout.addLayout(locator_btn_row)

        loc_btn_layout = QtWidgets.QHBoxLayout()
        loc_btn_layout.setContentsMargins(4, 4, 4, 4)
        loc_btn_layout.setSpacing(6)
        loc_btn_layout.addStretch()
        loc_btn_layout.addWidget(self.create_locators_btn)

        self.naming_group = self.build_group_section("Naming", names_layout)
        self.loc_settings_group = self.build_group_section("Locator Settings", loc_settings_layout)
        self.ctrl_group = self.build_group_section("Controls", ctrl_layout)
        self.arm_joint_group = self.build_group_section("Arm Joints", arm_joint_layout)
        self.arm_pose_group = self.build_group_section("Arm Poses", arm_pose_layout)
        self.current_objs_group = self.build_group_section("Current Objects", locator_list_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        main_layout.addWidget(self.naming_group)
        main_layout.addWidget(self.loc_settings_group)
        main_layout.addWidget(self.ctrl_group)
        main_layout.addWidget(self.arm_joint_group)
        main_layout.addWidget(self.arm_pose_group)
        main_layout.addWidget(self.current_objs_group)
        main_layout.addLayout(loc_btn_layout)
        main_layout.addStretch()
    
    def create_connections(self):
        self.prefix_cb.toggled.connect(self.on_use_prefix_changed)
        self.clavicle_cb.toggled.connect(self.on_use_clavicle_changed)
        self.fingers_cb.toggled.connect(self.on_use_fingers_changed)

        self.arm_pose_list.itemClicked.connect(self.on_arm_pose_item_clicked)
        self.delete_pose_btn.clicked.connect(self.on_delete_pose_clicked)
        self.save_pose_btn.clicked.connect(self.on_save_pose_clicked)
        self.load_pose_btn.clicked.connect(self.on_load_pose_clicked)

        self.create_locators_btn.clicked.connect(self.on_create_locators_clicked)
        self.current_locators_list.currentItemChanged.connect(self.on_locator_item_changed)
        self.refresh_locators_btn.clicked.connect(self.refresh_locator_list)
        self.delete_selected_btn.clicked.connect(self.on_delete_selected_locator)
            
    # ------------------------------------------------------------------
    # UI STYLE / VISIBILITY
    # ------------------------------------------------------------------
    def apply_palette_styling(self):
        spin_boxes = [
            self.ctrl_size_spin_box,
            self.root_size_spin_box,
            self.global_size_spin_box,
            self.size_double_spin_box,
            self.distance_spin_box,
            self.fingers_spin_box,
            self.finger_segments_spin_box,
        ]

        for widget in spin_boxes:
            palette = widget.palette()
            palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
            palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("white"))
            widget.setPalette(palette)

        combo_boxes = [
            self.ctrl_type_combo_box,
            self.root_type_combo_box,
            self.global_type_combo_box,
            self.orientation_combo_box,
        ]

        for combo_box in combo_boxes:
            palette = combo_box.palette()
            palette.setColor(QtGui.QPalette.Button, QtGui.QColor(43, 43, 43))
            combo_box.setPalette(palette)
        
    def update_module_ui_visibility(self):
        # MainUI now decides which locator-specific widget is visible.
        return

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

        group_box_layout = QtWidgets.QVBoxLayout(group_box)
        group_box_layout.setContentsMargins(10, 14, 10, 10)
        group_box_layout.setSpacing(6)
        group_box_layout.addLayout(inner_layout)

        return group_box
    
    # ------------------------------------------------------------------
    # SCENE QUERIES
    # ------------------------------------------------------------------
    def find_scene_locator_roots(self):
        all_transforms = cmds.ls(type="transform") or []
        locator_roots = []

        for obj in all_transforms:
            # Only top-level transforms
            if cmds.listRelatives(obj, parent=True):
                continue

            if obj.endswith("_rigGrp"):
                locator_roots.append(obj)

        return sorted(locator_roots)
    
    def find_connected_display_layers(self, root_obj):
        if not root_obj or not cmds.objExists(root_obj):
            return []

        objects_to_check = [root_obj]
        descendants = cmds.listRelatives(root_obj, allDescendents=True, fullPath=True) or []
        objects_to_check.extend(descendants)

        found_layers = set()

        for obj in objects_to_check:
            layers = cmds.listConnections(obj, type="displayLayer") or []
            for layer in layers:
                if layer != "defaultLayer":
                    found_layers.add(layer)

        return sorted(found_layers)
    
    # ------------------------------------------------------------------
    # DATA / BUILDER CREATION
    # ------------------------------------------------------------------    
    def clean_offset_name_for_pose(self, offset_name, builder):
        short_name = offset_name.split("|")[-1]
        
        if builder.prefix:
            prefix = "{}_{}_".format(builder.prefix, builder.name)
        else:
            prefix = "{}_".format(builder.name)
        
        clean_name = short_name.replace(prefix, "")
        clean_name = clean_name.replace("_ctrl_offsetGrp", "")
        
        for finger in ["index", "middle", "ring", "pinkie", "thumb"]:
            if builder.name.endswith("_{}".format(finger)):
                clean_name = "{}_{}".format(
                    finger,
                    clean_name
                )

                return clean_name

        clean_name = self.get_semantic_arm_pose_key(
            clean_name,
            builder
        )

        return clean_name
    
    def get_semantic_arm_pose_key(self, clean_name, builder):
        if builder is not self.builder:
            return clean_name

        if not self.locator_module:
            return clean_name

        joint_names = getattr(self.locator_module, "joints", []) or []

        if len(joint_names) == 4:
            pose_keys = [
                "clavicle",
                "shoulder",
                "elbow",
                "wrist"
            ]

        elif len(joint_names) == 3:
            pose_keys = [
                "shoulder",
                "elbow",
                "wrist"
            ]

        else:
            return clean_name

        joint_name_map = dict(
            zip(
                joint_names,
                pose_keys
            )
        )

        return joint_name_map.get(
            clean_name,
            clean_name
        )
    
    def get_joint_names_from_ui(self):
        joints = []

        if self.clavicle_cb.isChecked():
            clavicle_name = self.clavicle_le.text().strip() or "clavicle"
            joints.append(clavicle_name)

        shoulder_name = self.shoulder_le.text().strip() or "shoulder"
        elbow_name = self.elbow_le.text().strip() or "elbow"
        wrist_name = self.wrist_le.text().strip() or "wrist"

        joints.extend([shoulder_name, elbow_name, wrist_name])

        return joints

    def get_settings_from_ui(self):
        prefix = self.prefix_le.text().strip() if self.prefix_cb.isChecked() else None

        return {
            "loc_type": self.loc_type,
            "name": self.name_le.text().strip(),
            "prefix": prefix,
            "suffix": self.suffix_le.text().strip(),
            "joints": self.get_joint_names_from_ui(),

            "ctrl_type": self.ctrl_type_combo_box.currentText().strip(),
            "ctrl_size": self.ctrl_size_spin_box.value(),
            "ctrl_color": self.ctrl_color_widget.get_current_index(),

            "root_type": self.root_type_combo_box.currentText().strip(),
            "root_size": self.root_size_spin_box.value(),
            "root_color": self.root_color_widget.get_current_index(),

            "global_type": self.global_type_combo_box.currentText().strip(),
            "global_size": self.global_size_spin_box.value(),
            "global_color": self.global_color_widget.get_current_index(),

            "orientation": self.orientation_combo_box.currentText().strip().lower(),
            "display_LRA": self.joint_settings["display_LRA"],
            "loc_size": self.size_double_spin_box.value(),
            "joint_size": self.joint_settings["joint_size"],
            "distance_between": self.distance_spin_box.value(),
            "end_orient": self.joint_settings["end_orient"],
            "create_coplanar_mesh": self.joint_settings["create_coplanar_mesh"],

            "fingers": self.fingers_cb.isChecked(),
            "finger_count": self.fingers_spin_box.value(),
            "thumb": self.thumb_cb.isChecked(),
            "finger_segments": self.finger_segments_spin_box.value(),
            "finger_orientation_mode": self.finger_orientation_mode,
            "position_preset": self.position_preset,
        }
    def create_builder_from_settings(self, settings):
        return JointChainBuilder(
            name=settings["name"],
            prefix=settings["prefix"],
            suffix=settings["suffix"],
            ctrl_type=settings["ctrl_type"],
            ctrl_size=settings["ctrl_size"],
            ctrl_color=settings["ctrl_color"],
            root_type=settings["root_type"],
            root_size=settings["root_size"],
            root_color=settings["root_color"],
            global_type=settings["global_type"],
            global_size=settings["global_size"],
            global_color=settings["global_color"],
            joints=settings["joints"],
            orientation=settings["orientation"],
            display_LRA=settings["display_LRA"],
            loc_size=settings["loc_size"],
            joint_size=settings["joint_size"],
            distance_between=settings["distance_between"],
            end_orient=settings["end_orient"],
            create_coplanar_mesh=settings["create_coplanar_mesh"]
        )
    
    def create_module_from_settings(self, settings):
        module_class = MODULE_REGISTRY.get(settings["loc_type"])
        
        if not module_class:
            om.MGlobal.displayWarning(
                "Unsupported module type: {}".format(settings["loc_type"])
            )
            return False

        new_module = module_class.from_settings(settings)
        
        result = new_module.create_locators()
        
        if not result:
            om.MGlobal.displayWarning("Failed to create locators.")
            return False
            
        self.locator_module = new_module
        self.builder = new_module.builder
        self.locator_result = result
        
        return new_module
    
    def store_locator_module_data(self):
        if not self.builder:
            return None

        locator_root = self.builder.loc_main_grp
        if not locator_root:
            return None

        settings = {
            "locator_module": self.locator_module,
            "loc_type": self.loc_type,
            "name": self.builder.name,
            "prefix": self.builder.prefix,
            "suffix": self.builder.suffix,
            "joints": self.builder.joints[:],

            "orientation": self.builder.orientation,
            "display_LRA": self.builder.display_LRA,
            "loc_size": self.builder.loc_size,
            "joint_size": self.builder.joint_size,
            "distance_between": self.builder.distance_between,
            "end_orient": self.builder.end_orient,
            "create_coplanar_mesh": self.builder.create_coplanar_mesh,

            "ctrl_type": self.builder.ctrl_type,
            "ctrl_size": self.builder.ctrl_size,
            "ctrl_color": self.builder.ctrl_color,
            "root_type": self.builder.root_type,
            "root_size": self.builder.root_size,
            "root_color": self.builder.root_color,
            "global_type": self.builder.global_type,
            "global_size": self.builder.global_size,
            "global_color": self.builder.global_color,

            "fingers": getattr(self.locator_module, "fingers", False),
            "finger_count": getattr(self.locator_module, "finger_count", 0),
            "thumb": getattr(self.locator_module, "thumb", False),
            "finger_segments": getattr(self.locator_module, "finger_segments", 3),
            "finger_orientation_mode": getattr(
                self.locator_module,
                "finger_orientation_mode",
                "propagated"
            ),
            "position_preset": getattr(
                self.locator_module,
                "position_preset",
                "A-Pose"
            ),
        }

        self.locator_module_data[locator_root] = settings
        self.current_locator_root = locator_root
        return settings
        
    def get_pose_module_key(self):
        return self.loc_type
            
    def collect_current_locator_positions(self):
        if not self.builder:
            om.MGlobal.displayWarning("No active builder.")
            return {}

        positions = {}

        def collect_from_builder(builder):
            for offset, ctrl in zip(builder.loc_ctrl_offsets, builder.loc_ctrls):
                if not cmds.objExists(offset):
                    continue

                clean_name = self.clean_offset_name_for_pose(offset, builder)

                # offset_translate = cmds.xform(offset, query=True, worldSpace=True, translation=True)
                if ctrl and cmds.objExists(ctrl):
                    offset_translate = cmds.xform(
                        ctrl,
                        query=True,
                        worldSpace=True,
                        translation=True
                    )
                else:
                    offset_translate = cmds.xform(
                        offset,
                        query=True,
                        worldSpace=True,
                        translation=True
                    )
                offset_rotate = cmds.xform(offset, query=True, worldSpace=True, rotation=True)

                ctrl_translate = [0, 0, 0]
                ctrl_rotate = [0, 0, 0]

                if ctrl and cmds.objExists(ctrl):
                    ctrl_translate = list(
                        cmds.getAttr(
                            "{}.translate".format(ctrl)
                        )[0]
                    )
                
                    rotate_values = []
                    
                    for axis in "XYZ":
                        rotate_attr = "{}.rotate{}".format(ctrl, axis)
                        
                        if cmds.getAttr(rotate_attr, settable=True):
                            rotate_values.append(
                                cmds.getAttr(rotate_attr)
                            )
                        else:
                            rotate_values.append(0.0)
                    
                    ctrl_rotate = rotate_values

                positions[clean_name] = {
                    "offset": {
                        "translate": list(offset_translate),
                        "rotate": list(offset_rotate)
                    },
                    "ctrl": {
                        "translate": list(ctrl_translate),
                        "rotate": list(ctrl_rotate)
                    }
                }

        collect_from_builder(self.builder)

        if self.locator_module:
            finger_locs = getattr(self.locator_module, "finger_locs", {}) or {}
            
            for finger_data in finger_locs.values():
                finger_builder = finger_data.get("builder")
                
                if finger_builder:
                    collect_from_builder(finger_builder)

        return positions
    
    def collect_finger_up_reference_positions(self):
        up_reference_positions = {}
        
        if not self.locator_module:
            return up_reference_positions
        
        finger_locs = getattr(self.locator_module, "finger_locs", {}) or {}
        
        for finger, finger_data in finger_locs.items():
            up_ref = finger_data.get("up_ref")
            finger_builder = finger_data.get("builder")
                                    
            if (not up_ref or not cmds.objExists(up_ref) or not finger_builder):
                continue
            
            finger_ctrls = getattr(
                finger_builder,
                "loc_ctrls",
                []
            ) or []
            
            driver_index = (
                self.locator_module
                .get_finger_up_driver_index(finger_builder)
            )
            
            if len(finger_ctrls) <= driver_index:
                continue
            driver_ctrl = finger_ctrls[driver_index]
            
            custom_rotation_attr = (
                "{}.customRotation".format(driver_ctrl)
            )
            
            saved_rotation = 0.0
            
            if cmds.objExists(custom_rotation_attr):
                saved_rotation = cmds.getAttr(
                    custom_rotation_attr
                )
                cmds.setAttr(custom_rotation_attr, 0.0)
                            
            neutral_world_position = cmds.xform(
                up_ref,
                query=True,
                worldSpace=True,
                translation=True
            )
            
            if cmds.objExists(custom_rotation_attr):
                cmds.setAttr(custom_rotation_attr, saved_rotation)
                                        
            up_reference_positions[finger] = {
                "world_translate": list(
                    neutral_world_position
                )
            }
        
        return up_reference_positions
    
    def collect_finger_custom_rotations(self):
        finger_rotations = {}

        if not self.locator_module:
            return finger_rotations

        finger_locs = getattr(
            self.locator_module,
            "finger_locs",
            {}
        ) or {}

        for finger, finger_data in finger_locs.items():
            finger_builder = finger_data.get("builder")

            if not finger_builder:
                continue

            finger_ctrls = getattr(
                finger_builder,
                "loc_ctrls",
                []
            ) or []

            driver_index = (
                self.locator_module
                .get_finger_up_driver_index(
                    finger_builder
                )
            )

            if len(finger_ctrls) <= driver_index:
                continue

            driver_ctrl = finger_ctrls[driver_index]

            custom_rotation_attr = ("{}.customRotation".format(driver_ctrl)
            )

            if not cmds.objExists(custom_rotation_attr):
                continue

            finger_rotations[
                "{}_rotation".format(
                    finger
                )
            ] = cmds.getAttr(
                custom_rotation_attr
            )

        return finger_rotations
        
    def collect_pose_data(self):
        pose_data = self.collect_current_locator_positions()
        
        if not pose_data:
            return {}
        
        finger_rotations = self.collect_finger_custom_rotations()
        
        pose_data["metadata"] = {
            "orientation": (
                self.orientation_combo_box
                .currentText()
                .strip()
                .lower()
            ),
            
            "finger_up_references":
                self.collect_finger_up_reference_positions()
        }
        
        pose_data.update(finger_rotations)
            
        return pose_data
                    
    def set_active_locator_from_selected_list_item(self):
        item = self.current_locators_list.currentItem()

        if not item:
            om.MGlobal.displayWarning(
                "Select a locator chain from the Created Locators list first."
            )
            return False

        locator_root = item.text()

        if not cmds.objExists(locator_root):
            om.MGlobal.displayWarning(
                "Selected locator chain no longer exists: {}".format(locator_root)
            )
            self.refresh_locator_list()
            return False

        module_data = self.locator_module_data.get(locator_root)
        if not module_data:
            om.MGlobal.displayWarning(
                "No stored module data found for selected locator chain: {}".format(locator_root)
            )
            return False

        selected_locator_module = module_data.get("locator_module")
        if not selected_locator_module:
            om.MGlobal.displayWarning(
                "No locator module found for selected locator chain: {}".format(locator_root)
            )
            return False

        selected_builder = getattr(selected_locator_module, "builder", None)
        if not selected_builder:
            om.MGlobal.displayWarning(
                "No builder found for selected locator chain: {}".format(locator_root)
            )
            return False

        self.current_locator_root = locator_root
        self.locator_module = selected_locator_module
        self.builder = selected_builder
        self.locator_result = getattr(selected_locator_module, "locs", {}) or {}

        self.emit_active_locator()
        return True
    
    def get_selected_pose_name_for_creation(self):
        item = self.arm_pose_list.currentItem()

        if not item:
            return "A-Pose"

        item_type = item.data(QtCore.Qt.UserRole)

        if item_type in ["divider", "add"]:
            return "A-Pose"

        return item.text()
    
    # ------------------------------------------------------------------
    # UI SLOTS: BASIC OPTION CHANGES
    # ------------------------------------------------------------------
    @QtCore.Slot(str)
    def on_loc_module_changed(self, text):
        self.loc_module = text.strip()

    @QtCore.Slot(bool)
    def on_use_prefix_changed(self, checked):
        self.use_prefix = checked
        self.prefix_le.setVisible(checked)

    @QtCore.Slot(bool)
    def on_use_clavicle_changed(self, checked):
        self.use_clavicle = checked
        self.clavicle_le.setVisible(checked)

    @QtCore.Slot(bool)
    def on_use_fingers_changed(self, checked):
        self.use_fingers = checked
        self.fingers_spin_box.setVisible(checked)
        self.finger_segments_spin_box.setVisible(checked)
        self.thumb_cb.setEnabled(checked)
    
    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def on_arm_pose_item_clicked(self, item):
        item_type = item.data(QtCore.Qt.UserRole)
        
        if item_type == "divider":
            return
        
        if item_type == "add":
            self.pose_name_le.setText("Custom Pose 01")
            self.position_preset = "A-Pose"
            return
        
        self.position_preset = item.text()
        
        if item_type == "custom":
            self.pose_name_le.setText(item.text())
        else:
            self.pose_name_le.clear()
    
    @QtCore.Slot()
    def on_delete_pose_clicked(self):
        item = self.arm_pose_list.currentItem()
        
        if not item:
            om.MGlobal.displayWarning("Select a custom pose to delete.")
            return
        
        item_type = item.data(QtCore.Qt.UserRole)
        pose_name = item.text()
        
        if item_type != "custom":
            om.MGlobal.displayWarning("Only custom poses can be deleted.")
            return
        
        deleted = LocatorPresetManager.delete_preset(
            self.get_pose_module_key(),
            pose_name
        )
                
        if not deleted:
            om.MGlobal.displayWarning("Could not delete pose: {}".format(pose_name))
            return
        
        self.position_preset = "A-Pose"
        self.pose_name_le.clear()
        self.refresh_arm_pose_list(selected_pose="A-Pose")
        
        om.MGlobal.displayInfo("Deleted custom pose: {}".format(pose_name))
    
    def delete_locator_rig_for_rebuild(self, locator_root):
        if not locator_root or not cmds.objExists(locator_root):
            return
        
        display_layers = (
            self.find_connected_display_layers(locator_root)
        )
        
        for layer in display_layers:
            cmds.delete(layer)
        
        cmds.delete(locator_root)
        
        self.locator_module_data.pop(locator_root, None)
    
    @QtCore.Slot()
    def on_save_pose_clicked(self):
        if not self.set_active_locator_from_selected_list_item():
            return

        item = self.arm_pose_list.currentItem()

        if not item:
            om.MGlobal.displayWarning("Select a pose first.")
            return

        item_type = item.data(QtCore.Qt.UserRole)
        
        #
        if item_type == "default":
            om.MGlobal.displayWarning("A-Pose and T-Pose cannot be overwritten. Create a custom pose instead.")
            return

        pose_name = self.pose_name_le.text().strip()

        if not pose_name:
            pose_name = "Custom Pose 01"

        if pose_name in self.default_pose_names:
            om.MGlobal.displayWarning("{} is protected cannot be overwritten.".format(pose_name))
            return
        #
        # To update default poses. Comment this section out ^^^ and uncomment below comment.
        
        # pose_name = "A-Pose"
        
        pose_data = self.collect_pose_data()
        
        if not pose_data:
            return
                
        LocatorPresetManager.save_preset(
            self.get_pose_module_key(),
            pose_name,
            pose_data
        )
        
        self.position_preset = pose_name
        self.refresh_arm_pose_list(selected_pose=pose_name)

        om.MGlobal.displayInfo(
            "Saved pose '{}' under bucket '{}' with {} keys.".format(
                pose_name,
                self.get_pose_module_key(),
                len(pose_data)
            )
        )
    
    def create_locator_module_from_pose(self, settings, pose_name):
        settings = dict(settings)
        settings["position_preset"] = pose_name

        new_module = self.create_module_from_settings(settings)
        if not new_module:
            return False

        self.position_preset = pose_name
        self.current_locator_root = None

        self.store_locator_module_data()
        self.refresh_locator_list(select_root=self.current_locator_root)

        self.refresh_locators_btn.setEnabled(True)
        self.delete_selected_btn.setEnabled(True)
        self.emit_active_locator()
        return True
    
    @QtCore.Slot()
    def on_load_pose_clicked(self):
        if not self.set_active_locator_from_selected_list_item():
            return
        
        item = self.arm_pose_list.currentItem()
        
        if not item:
            om.MGlobal.displayWarning("Select a pose to load.")
            return
        
        item_type = item.data(QtCore.Qt.UserRole)
        
        if item_type in ["divider", "add"]:
            om.MGlobal.displayWarning("Select an existing pose to load.")
            return
        
        pose_name = item.text()
        
        pose_data = LocatorPresetManager.load_preset(
            self.get_pose_module_key(),
            pose_name
        )
        
        if not pose_data:
            om.MGlobal.displayWarning("Could not load pose: {}".format(pose_name))
            return
        
        locator_root = self.current_locator_root
        module_data = self.locator_module_data[locator_root]
                
        settings = {
            key: value
            for key, value in module_data.items()
            if key != "locator_module"
        }
        
        settings["position_preset"] = pose_name
        
        self.delete_locator_rig_for_rebuild(locator_root)
        
        self.builder = None
        self.locator_module = None
        self.locator_result = {}
        self.current_locator_root = None
        
        success = self.create_locator_module_from_pose(
            settings,
            pose_name
        )
        
        if not success:
            om.MGlobal.displayWarning(
                "Failed to rebuild locator module "
                "using pose: {}".format(
                    pose_name
                )
            )
            return
        
        self.refresh_arm_pose_list(selected_pose=pose_name)
            
    # ------------------------------------------------------------------
    # UI SLOTS: CREATE / REFRESH
    # ------------------------------------------------------------------    
    @QtCore.Slot()
    def on_create_locators_clicked(self):
        settings = self.get_settings_from_ui()
        selected_pose = self.get_selected_pose_name_for_creation()

        pose_data = LocatorPresetManager.load_preset(
            settings["loc_type"],
            selected_pose
        )

        if not pose_data:
            om.MGlobal.displayWarning(
                "Could not load pose: {}. Using A-Pose.".format(selected_pose)
            )
            selected_pose = "A-Pose"
            self.refresh_arm_pose_list(selected_pose="A-Pose")

        old_locator_module = self.locator_module
        old_builder = self.builder
        old_locator_result = self.locator_result
        old_current_locator_root = self.current_locator_root

        success = self.create_locator_module_from_pose(settings, selected_pose)

        if not success:
            self.locator_module = old_locator_module
            self.builder = old_builder
            self.locator_result = old_locator_result
            self.current_locator_root = old_current_locator_root
            self.refresh_locator_list(select_root=old_current_locator_root)
            self.refresh_locators_btn.setEnabled(bool(self.locator_result))
            self.delete_selected_btn.setEnabled(bool(self.locator_result))
            if self.locator_module and self.builder:
                self.emit_active_locator()
            return
            
    @QtCore.Slot()
    def refresh_locator_list(self, select_root=None):
        self.current_locators_list.blockSignals(True)
        self.current_locators_list.clear()

        locator_roots = self.find_scene_locator_roots()

        for obj_name in locator_roots:
            self.current_locators_list.addItem(obj_name)

        has_items = bool(locator_roots)
        self.refresh_locators_btn.setEnabled(has_items)
        self.delete_selected_btn.setEnabled(has_items)

        target_root = select_root or self.current_locator_root
        selected_item = None

        if target_root:
            for index in range(self.current_locators_list.count()):
                item = self.current_locators_list.item(index)
                if item.text() == target_root:
                    selected_item = item
                    break

        if selected_item is None and self.current_locators_list.count():
            selected_item = self.current_locators_list.item(0)

        if selected_item:
            self.current_locators_list.setCurrentItem(selected_item)
            self.current_locator_root = selected_item.text()
        else:
            self.current_locator_root = None

        self.current_locators_list.blockSignals(False)

        if selected_item and selected_item.text() in self.locator_module_data:
            self.set_active_locator_from_selected_list_item()
        elif not selected_item:
            self.active_locator_cleared.emit()
    
    @QtCore.Slot()
    def refresh_arm_pose_list(self, selected_pose=None):
        self.arm_pose_list.clear()
        
        # Default protected poses
        for pose_name in self.default_pose_names:
            item = QtWidgets.QListWidgetItem(pose_name)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            item.setData(QtCore.Qt.UserRole, "default")
            self.arm_pose_list.addItem(item)
        
        # Divider
        divider = QtWidgets.QListWidgetItem("────────────")
        divider.setFlags(QtCore.Qt.NoItemFlags)
        divider.setData(QtCore.Qt.UserRole, "divider")
        self.arm_pose_list.addItem(divider)
        
        data = LocatorPresetManager.load_all_presets()

        module_key = self.get_pose_module_key()
        module_data = data.get(module_key, {})
        
        custom_pose_names = sorted(
            pose_name
            for pose_name in module_data.keys()
            if pose_name not in self.default_pose_names
        )
        
        for pose_name in sorted(custom_pose_names):
            item = QtWidgets.QListWidgetItem(pose_name)
            item.setData(QtCore.Qt.UserRole, "custom")
            self.arm_pose_list.addItem(item)
        
        # Add Custom Pose Row
        add_item = QtWidgets.QListWidgetItem(self.add_custom_pose_label)
        add_item.setData(QtCore.Qt.UserRole, "add")
        self.arm_pose_list.addItem(add_item)
        
        # Reselect
        target_pose = selected_pose or self.position_preset
        
        for i in range(self.arm_pose_list.count()):
            item = self.arm_pose_list.item(i)
            if item.text() == target_pose:
                self.arm_pose_list.setCurrentItem(item)
                return
            
        self.arm_pose_list.setCurrentItem(add_item)
    
    # ------------------------------------------------------------------
    # UI SLOTS: LIST SELECTION
    # ------------------------------------------------------------------    
    @QtCore.Slot(QtWidgets.QListWidgetItem, QtWidgets.QListWidgetItem)
    def on_locator_item_changed(self, current, previous):
        if not current:
            return

        if not self.set_active_locator_from_selected_list_item():
            return

        cmds.select(current.text(), replace=True)
        
    # ------------------------------------------------------------------
    # UI SLOTS: DELETE
    # ------------------------------------------------------------------
    @QtCore.Slot()
    def on_delete_selected_locator(self):
        item = self.current_locators_list.currentItem()
        if not item:
            om.MGlobal.displayWarning("No locator object selected.")
            return

        selected_name = item.text()

        if not cmds.objExists(selected_name):
            om.MGlobal.displayWarning(
                "Locator object does not exist: {}".format(selected_name)
            )
            self.refresh_locator_list()
            return

        deleted = False
        display_layers = self.find_connected_display_layers(selected_name)

        for layer in display_layers:
            try:
                cmds.delete(layer)
            except Exception as exc:
                om.MGlobal.displayWarning(
                    "Failed to delete display layer {}: {}".format(layer, exc)
                )

        try:
            cmds.delete(selected_name)
            deleted = True
            self.locator_module_data.pop(selected_name, None)
        except Exception as exc:
            om.MGlobal.displayWarning(
                "Failed to delete locator object: {}".format(exc)
            )

        builder_root = getattr(self.builder, "loc_main_grp", None) if self.builder else None
        if builder_root == selected_name and self.builder:
            self.builder.clear_cached_locator_state()
            if self.locator_module:
                self.locator_module.locs = {}
            self.locator_result = {}
            self.current_locator_root = None
            self.builder = None
            self.locator_module = None
            self.active_locator_cleared.emit()

        self.refresh_locator_list()

        if not deleted:
            om.MGlobal.displayWarning("Locator object could not be deleted.")

if __name__ == "__main__":
    try:
        arm_locator_ui.close()
        arm_locator_ui.deleteLater()
    except (NameError, RuntimeError):
        pass

    arm_locator_ui = ArmLocatorUI()
    arm_locator_ui.setWindowTitle("Arm Locator UI")
    arm_locator_ui.resize(510, 700)
    arm_locator_ui.show()