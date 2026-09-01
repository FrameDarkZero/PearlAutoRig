try:
    from PySide2 import QtWidgets
    from PySide2 import QtCore
    from PySide2 import QtGui
except ImportError:
    from PySide6 import QtWidgets
    from PySide6 import QtCore
    from PySide6 import QtGui

import maya.cmds as cmds
import maya.OpenMaya as om


class JointUI(QtWidgets.QWidget):
    """Generic joint-construction UI for the currently active locator module."""

    settings_changed = QtCore.Signal(object)
    joints_constructed = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.builder = None
        self.locator_module = None
        self.locator_root = None
        self.module_data = None

        self.joint_result = {}
        self.current_joint_root = None

        self.display_LRA = False
        self.joint_size = 1.0
        self.end_orient = "parent"
        self.create_coplanar_mesh = False

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(50, 50, 50))
        self.setPalette(palette)

        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.refresh_joints_list()

    # ------------------------------------------------------------------
    # WIDGETS / LAYOUT
    # ------------------------------------------------------------------
    def create_widgets(self):
        self.joint_size_spin_box = QtWidgets.QDoubleSpinBox()
        self.joint_size_spin_box.setFixedWidth(70)
        self.joint_size_spin_box.setMinimum(0.001)
        self.joint_size_spin_box.setMaximum(1000.0)
        self.joint_size_spin_box.setValue(self.joint_size)
        self.joint_size_spin_box.setSingleStep(0.1)
        self.joint_size_spin_box.setToolTip(
            "Joint radius/size for constructed joints"
        )

        self.current_joints_list = QtWidgets.QListWidget()
        self.current_joints_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )
        self.current_joints_list.setFixedHeight(90)
        self.current_joints_list.setAlternatingRowColors(True)
        self.current_joints_list.setToolTip(
            "Click a created joint chain to select it in Maya"
        )

        self.display_LRA_cb = QtWidgets.QCheckBox("Display LRA")
        self.display_LRA_cb.setChecked(self.display_LRA)

        self.coplanar_mesh_cb = QtWidgets.QCheckBox("Coplanar Mesh")
        self.coplanar_mesh_cb.setChecked(self.create_coplanar_mesh)

        self.end_orient_combo_box = QtWidgets.QComboBox()
        self.end_orient_combo_box.addItems([" parent", " world"])
        self.end_orient_combo_box.setCurrentIndex(0)

        self.delete_joints_btn = QtWidgets.QPushButton("Delete Selected Joints")
        self.delete_joints_btn.setEnabled(False)

        self.refresh_joints_btn = QtWidgets.QPushButton("Refresh List")
        self.refresh_joints_btn.setEnabled(False)

        self.construct_joints_btn = QtWidgets.QPushButton("Construct Joints")
        self.construct_joints_btn.setEnabled(False)

        self.apply_palette_styling()

    def create_layout(self):
        joint_settings_form = QtWidgets.QFormLayout()
        joint_settings_form.addRow("Joint Size:", self.joint_size_spin_box)
        joint_settings_form.addRow("", self.display_LRA_cb)
        joint_settings_form.addRow("", self.coplanar_mesh_cb)
        joint_settings_form.addRow("End Orient:", self.end_orient_combo_box)

        joint_settings_group = self.build_group_section(
            "Joint Settings",
            joint_settings_form
        )
        joint_settings_group.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum
        )

        joint_btn_row = QtWidgets.QHBoxLayout()
        joint_btn_row.addWidget(self.refresh_joints_btn)
        joint_btn_row.addWidget(self.delete_joints_btn)
        joint_btn_row.addStretch()

        joints_list_layout = QtWidgets.QVBoxLayout()
        joints_list_layout.setContentsMargins(10, 10, 10, 10)
        joints_list_layout.setSpacing(10)
        joints_list_layout.addWidget(QtWidgets.QLabel("Created Joints:"))
        joints_list_layout.addWidget(self.current_joints_list)
        joints_list_layout.addLayout(joint_btn_row)

        self.joints_list_group = self.build_group_section(
            "Current Joints",
            joints_list_layout
        )
        self.joints_list_group.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum
        )

        joints_btn_layout = QtWidgets.QHBoxLayout()
        joints_btn_layout.setContentsMargins(4, 4, 4, 4)
        joints_btn_layout.setSpacing(6)
        joints_btn_layout.addStretch()
        joints_btn_layout.addWidget(self.construct_joints_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        main_layout.addWidget(joint_settings_group)
        main_layout.addWidget(self.joints_list_group)
        main_layout.addLayout(joints_btn_layout)
        main_layout.addStretch()

    def create_connections(self):
        self.display_LRA_cb.toggled.connect(self.on_display_lra)
        self.coplanar_mesh_cb.toggled.connect(self.on_coplanar_mesh)
        self.joint_size_spin_box.valueChanged.connect(self.on_joint_size_changed)
        self.end_orient_combo_box.currentTextChanged.connect(
            self.on_end_orient_changed
        )

        self.construct_joints_btn.clicked.connect(
            self.on_construct_joints_clicked
        )
        self.current_joints_list.itemClicked.connect(self.on_joint_item_clicked)
        self.refresh_joints_btn.clicked.connect(self.refresh_joints_list)
        self.delete_joints_btn.clicked.connect(self.on_delete_selected_joint)

    def apply_palette_styling(self):
        palette = self.joint_size_spin_box.palette()
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("white"))
        self.joint_size_spin_box.setPalette(palette)

        palette = self.end_orient_combo_box.palette()
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(43, 43, 43))
        self.end_orient_combo_box.setPalette(palette)

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
    # SHARED ACTIVE LOCATOR STATE
    # ------------------------------------------------------------------
    def get_settings(self):
        return {
            "display_LRA": self.display_LRA_cb.isChecked(),
            "joint_size": self.joint_size_spin_box.value(),
            "end_orient": self.end_orient_combo_box.currentText().strip().lower(),
            "create_coplanar_mesh": self.coplanar_mesh_cb.isChecked(),
        }

    def set_active_locator(self, locator_module, module_data, locator_root):
        self.locator_module = locator_module
        self.builder = getattr(locator_module, "builder", None) if locator_module else None
        self.module_data = module_data if module_data is not None else {}
        self.locator_root = locator_root

        settings = self.module_data or {}
        builder = self.builder

        display_lra = settings.get(
            "display_LRA",
            getattr(builder, "display_LRA", self.display_LRA)
        )
        joint_size = settings.get(
            "joint_size",
            getattr(builder, "joint_size", self.joint_size)
        )
        end_orient = settings.get(
            "end_orient",
            getattr(builder, "end_orient", self.end_orient)
        )
        coplanar = settings.get(
            "create_coplanar_mesh",
            getattr(builder, "create_coplanar_mesh", self.create_coplanar_mesh)
        )

        widgets = [
            self.display_LRA_cb,
            self.joint_size_spin_box,
            self.end_orient_combo_box,
            self.coplanar_mesh_cb,
        ]
        previous = [widget.blockSignals(True) for widget in widgets]

        self.display_LRA_cb.setChecked(bool(display_lra))
        self.joint_size_spin_box.setValue(float(joint_size))
        self.end_orient_combo_box.setCurrentText(
            " world" if str(end_orient).strip().lower() == "world" else " parent"
        )
        self.coplanar_mesh_cb.setChecked(bool(coplanar))

        for widget, was_blocked in zip(widgets, previous):
            widget.blockSignals(was_blocked)

        self.display_LRA = bool(display_lra)
        self.joint_size = float(joint_size)
        self.end_orient = str(end_orient).strip().lower()
        self.create_coplanar_mesh = bool(coplanar)

        can_construct = bool(
            self.builder
            and self.locator_root
            and cmds.objExists(self.locator_root)
        )
        self.construct_joints_btn.setEnabled(can_construct)

    def clear_active_locator(self):
        self.builder = None
        self.locator_module = None
        self.locator_root = None
        self.module_data = None
        self.construct_joints_btn.setEnabled(False)

    def update_active_state(self):
        settings = self.get_settings()

        self.display_LRA = settings["display_LRA"]
        self.joint_size = settings["joint_size"]
        self.end_orient = settings["end_orient"]
        self.create_coplanar_mesh = settings["create_coplanar_mesh"]

        if self.module_data is not None:
            self.module_data.update(settings)

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

        self.settings_changed.emit(settings)

    # ------------------------------------------------------------------
    # SETTINGS SLOTS
    # ------------------------------------------------------------------
    @QtCore.Slot(bool)
    def on_display_lra(self, checked):
        self.update_active_state()

    @QtCore.Slot(bool)
    def on_coplanar_mesh(self, checked):
        self.update_active_state()

    @QtCore.Slot(float)
    def on_joint_size_changed(self, value):
        self.update_active_state()

    @QtCore.Slot(str)
    def on_end_orient_changed(self, text):
        self.update_active_state()

    # ------------------------------------------------------------------
    # SCENE QUERIES / JOINT LIST
    # ------------------------------------------------------------------
    def find_scene_joint_roots(self):
        all_transforms = cmds.ls(type="transform") or []
        joint_roots = []

        for obj in all_transforms:
            if cmds.listRelatives(obj, parent=True):
                continue
            if obj.endswith("_mainGrp"):
                joint_roots.append(obj)

        return sorted(joint_roots)

    def find_connected_display_layers(self, root_obj):
        if not root_obj or not cmds.objExists(root_obj):
            return []

        objects_to_check = [root_obj]
        descendants = cmds.listRelatives(
            root_obj,
            allDescendents=True,
            fullPath=True
        ) or []
        objects_to_check.extend(descendants)

        found_layers = set()
        for obj in objects_to_check:
            layers = cmds.listConnections(obj, type="displayLayer") or []
            for layer in layers:
                if layer != "defaultLayer":
                    found_layers.add(layer)

        return sorted(found_layers)

    @QtCore.Slot()
    def refresh_joints_list(self):
        self.current_joints_list.clear()
        joint_roots = self.find_scene_joint_roots()

        if not joint_roots:
            self.current_joint_root = None
            self.refresh_joints_btn.setEnabled(False)
            self.delete_joints_btn.setEnabled(False)
            return

        self.current_joint_root = joint_roots[0]
        for obj_name in joint_roots:
            self.current_joints_list.addItem(obj_name)

        self.refresh_joints_btn.setEnabled(True)
        self.delete_joints_btn.setEnabled(True)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def on_joint_item_clicked(self, item):
        obj_name = item.text()
        if cmds.objExists(obj_name):
            cmds.select(obj_name, replace=True)
        else:
            om.MGlobal.displayWarning(
                "Object does not exist: {}".format(obj_name)
            )
            self.refresh_joints_list()

    @QtCore.Slot()
    def on_delete_selected_joint(self):
        item = self.current_joints_list.currentItem()
        if not item:
            om.MGlobal.displayWarning("No joint object selected.")
            return

        selected_name = item.text()
        if not cmds.objExists(selected_name):
            om.MGlobal.displayWarning(
                "Joint object does not exist: {}".format(selected_name)
            )
            self.refresh_joints_list()
            return

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
        except Exception as exc:
            om.MGlobal.displayWarning(
                "Failed to delete joint object: {}".format(exc)
            )
            return

        builder_root = getattr(self.builder, "jnt_main_grp", None) if self.builder else None
        if builder_root == selected_name and self.builder:
            self.builder.clear_cached_joint_state()
            self.joint_result = {}
            self.current_joint_root = None

        self.refresh_joints_list()

    # ------------------------------------------------------------------
    # CONSTRUCT JOINTS
    # ------------------------------------------------------------------
    @QtCore.Slot()
    def on_construct_joints_clicked(self):
        locator_root = self.locator_root

        if not locator_root:
            om.MGlobal.displayWarning(
                "Select a locator object from the Current Locators list first."
            )
            return

        if not cmds.objExists(locator_root):
            om.MGlobal.displayWarning(
                "Locator object does not exist: {}".format(locator_root)
            )
            self.clear_active_locator()
            return

        self.update_active_state()

        if self.locator_module and hasattr(self.locator_module, "create_joints"):
            result = self.locator_module.create_joints(
                delete_locators_after=False
            )
        elif self.builder and hasattr(
            self.builder,
            "construct_joints_from_locator_root"
        ):
            result = self.builder.construct_joints_from_locator_root(locator_root)
        else:
            om.MGlobal.displayWarning(
                "The active locator does not provide a joint-construction method."
            )
            return

        if not result:
            om.MGlobal.displayWarning("Failed to construct joints.")
            return

        self.joint_result = result

        display_layers = self.find_connected_display_layers(locator_root)
        for layer in display_layers:
            try:
                cmds.delete(layer)
            except Exception as exc:
                om.MGlobal.displayWarning(
                    "Failed to delete display layer {}: {}".format(layer, exc)
                )

        if cmds.objExists(locator_root):
            try:
                cmds.delete(locator_root)
            except Exception as exc:
                om.MGlobal.displayWarning(
                    "Failed to delete locator object {}: {}".format(
                        locator_root,
                        exc
                    )
                )

        if self.builder:
            self.builder.clear_cached_locator_state()

        if self.locator_module:
            self.locator_module.locs = {}

        consumed_root = locator_root
        self.clear_active_locator()
        self.refresh_joints_list()
        self.joints_constructed.emit(consumed_root)


if __name__ == "__main__":
    try:
        joint_ui.close()
        joint_ui.deleteLater()
    except (NameError, RuntimeError):
        pass

    joint_ui = JointUI()
    joint_ui.setWindowTitle("Joint UI")
    joint_ui.resize(510, 400)
    joint_ui.show()