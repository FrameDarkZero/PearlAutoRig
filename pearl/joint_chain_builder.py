import maya.cmds as cmds
import maya.OpenMaya as om

from PearlAutoRig.pearl.custom_locator import CustomLocator
from PearlAutoRig.pearl.three_point_joint_chain import ThreePointJointChain
from GiancarloHelpers import GiancarloHelpers
from GiancarloCurveLibrary import GiancarloCurveLibrary


class JointChainBuilder(object):
    
    def __init__(
        self,
        name,
        suffix,
        ctrl_type,
        ctrl_size,
        ctrl_color,
        root_type,
        root_size,
        root_color,
        global_type,
        global_size,
        global_color,
        joints,
        prefix=None,
        orientation="x",
        display_LRA=False,
        loc_size=1.0,
        joint_size=1.0,
        distance_between=3,
        end_orient="parent",
        create_coplanar_mesh=False,
        create_global_root=True,
        create_display_layer=True,
        display_layer=None,
        use_locator_orientation=False,
        use_cross_as_secondary=False
    ):
        self.name = name
        self.prefix = prefix
        self.ctrl_type = ctrl_type
        self.ctrl_size = ctrl_size
        self.ctrl_color = ctrl_color
        self.root_type = root_type
        self.root_size = root_size
        self.root_color = root_color
        self.global_type = global_type
        self.global_size = global_size
        self.global_color = global_color
        self.orientation = str(orientation).lower()
        self.display_LRA = display_LRA
        self.loc_size = loc_size
        self.joint_size = joint_size
        self.distance_between = distance_between
        self.suffix = suffix
        self.end_orient = str(end_orient).lower()
        self.create_coplanar_mesh = create_coplanar_mesh
        self.create_global_root = create_global_root
        self.create_display_layer = create_display_layer
        self.display_layer = display_layer
        self.use_locator_orientation = use_locator_orientation
        self.use_cross_as_secondary = use_cross_as_secondary
        
        self.loc_main_grp = None
        self.root_ctrl = None
        self.root_offset = None
        self.global_ctrl = None
        self.global_offset = None
        self.loc_display_layer = None
        self.locators = []
        self.branches = []
        self.loc_ctrls = []
        self.loc_ctrl_offsets = []
        
        self.coplanar_facet = None
        self.coplanar_clusters = []
        self.built_joints = []
        self.jnt_display_layer = None
        self.jnt_main_grp = None
        self.jnt_mesh_grp = None
        self.jnt_joints_grp = None
        self.jnt_cluster_grp = None
        
        if self.orientation not in ["x", "y", "z"]:
            om.MGlobal.displayWarning(f"Unsupported orientation: {orientation}")
            return
        
        if self.end_orient not in ["parent", "world"]:
            om.MGlobal.displayWarning(f"Unsupported end_orient: {end_orient}")
            return
        
        if len(set(joints)) != len(joints):
            om.MGlobal.displayWarning("Duplicate names found in input.")
            return
        else:
            self.joints = joints
    
    def build_locator_name(self, joint_name):
        if self.prefix:
            return f"{self.prefix}_{self.name}_{joint_name}_loc"
        return f"{self.name}_{joint_name}_loc"

    def build_ctrl_name(self, joint_name):
        if self.prefix:
            return f"{self.prefix}_{self.name}_{joint_name}_ctrl"
        return f"{self.name}_{joint_name}_ctrl"

    def build_ctrl_offset_name(self, joint_name):
        if self.prefix:
            return f"{self.prefix}_{self.name}_{joint_name}_ctrl_offsetGrp"
        return f"{self.name}_{joint_name}_ctrl_offsetGrp"

    def build_main_group_names(self):
        if self.prefix:
            return {
                "loc_main_grp": f"{self.prefix}_{self.name}_{self.suffix}_rigGrp",
                "loc_grp": f"{self.prefix}_{self.name}_locGrp",
                "loc_ctrl_grp": f"{self.prefix}_{self.name}_locCtrlGrp",
                "loc_cluster_grp": f"{self.prefix}_{self.name}_{self.suffix}_locClsGrp",
                "branch_grp": f"{self.prefix}_{self.name}_{self.suffix}_branchGrp",
                "jnt_main_grp": f"{self.prefix}_{self.name}_{self.suffix}_mainGrp",
                "jnt_mesh_grp": f"{self.prefix}_{self.name}_{self.suffix}_meshGrp",
                "jnt_joints_grp": f"{self.prefix}_{self.name}_{self.suffix}_jntGrp",
                "jnt_cluster_grp": f"{self.prefix}_{self.name}_{self.suffix}_clusterGrp",
            }
        else:
            return {
                "loc_main_grp": f"{self.name}_{self.suffix}_rigGrp",
                "loc_grp": f"{self.name}_locGrp",
                "loc_ctrl_grp": f"{self.name}_locCtrlGrp",
                "loc_cluster_grp": f"{self.name}_{self.suffix}_locClsGrp",
                "branch_grp": f"{self.name}_{self.suffix}_branchGrp",
                "jnt_main_grp": f"{self.name}_{self.suffix}_mainGrp",
                "jnt_mesh_grp": f"{self.name}_{self.suffix}_meshGrp",
                "jnt_joints_grp": f"{self.name}_{self.suffix}_jntGrp",
                "jnt_cluster_grp": f"{self.name}_{self.suffix}_clusterGrp",
            }

    def get_orientation_settings(self):
        if self.orientation == "x":
            return {
                "aimVector": (1, 0, 0),
                "upVector": (0, 1, 0),
                "helper_axis": "x"
            }
        elif self.orientation == "y":
            return {
                "aimVector": (0, 1, 0),
                "upVector": (-1, 0, 0),
                "helper_axis": "y"
            }
        else:
            return {
                "aimVector": (0, 0, 1),
                "upVector": (1, 0, 0),
                "helper_axis": "z"
            }
    
    def get_joint_orientation_settings(self):
        orientation_map = {
            "x": {
                "primary_axis": "x",
                "secondary_axis": "y",
                "secondary_world_orient": "y",
                "cross_product": "z",
            },
            "y": {
                "primary_axis": "y",
                "secondary_axis": "-x",
                "secondary_world_orient": "y",
                "cross_product": "z",
            },
            "z": {
                "primary_axis": "z",
                "secondary_axis": "x",
                "secondary_world_orient": "y",
                "cross_product": "y",
            }
        }

        return orientation_map.get(self.orientation)
    
    def distance_between_points(self, p1, p2):
        vec = om.MVector(
            p2[0] - p1[0],
            p2[1] - p1[1],
            p2[2] - p1[2]
        )
        return vec.length()

    def get_min_helper_distance(self):
        return max(self.loc_size * 4.0, 1.0)

    def get_auto_helper_distance_from_positions(self, positions):
        if not positions or len(positions) < 2:
            return self.get_min_helper_distance()

        lengths = []
        for i in range(len(positions) - 1):
            seg_len = self.distance_between_points(positions[i], positions[i + 1])
            if seg_len > 1e-8:
                lengths.append(seg_len)

        if not lengths:
            return self.get_min_helper_distance()

        avg_len = sum(lengths) / float(len(lengths))
        return max(avg_len * 0.5, self.get_min_helper_distance())

    def get_auto_helper_distance_for_pair(self, parent_pos, child_pos):
        seg_len = self.distance_between_points(parent_pos, child_pos)
        if seg_len < 1e-8:
            return self.get_min_helper_distance()

        return max(seg_len * 0.5, self.get_min_helper_distance())

    def get_helper_distance(self, positions=None, parent_pos=None, child_pos=None):
        if parent_pos is not None and child_pos is not None:
            return self.get_auto_helper_distance_for_pair(parent_pos, child_pos)

        if positions is not None:
            return self.get_auto_helper_distance_from_positions(positions)

        return max(self.distance_between * 0.5, self.get_min_helper_distance())
    
    def rename_built_joint_chain(self, built_joints, prefix_names):
        for i in reversed(range(len(built_joints))):
            joint = built_joints[i]

            matches = cmds.ls(joint, long=True)
            if not matches:
                om.MGlobal.displayWarning("Could not find joint to rename: {}".format(joint))
                continue

            if i < len(prefix_names):
                new_name = "{}_{}".format(prefix_names[i], self.suffix)
            else:
                new_name = "joint_{}_{}".format(i, self.suffix)

            cmds.rename(matches[0], new_name)

        root_name = "{}_{}".format(prefix_names[0], self.suffix)
        root_matches = cmds.ls(root_name, long=True)

        if not root_matches:
            om.MGlobal.displayWarning("Could not find renamed root joint: {}".format(root_name))
            return []

        ordered_joints = []
        current = root_matches[0]

        while current:
            ordered_joints.append(current)

            children = cmds.listRelatives(
                current,
                children=True,
                type="joint",
                fullPath=True
            ) or []

            current = children[0] if children else None

        return ordered_joints
    
    def create_locators(self):
        self.locators = []
        self.branches = []
        self.loc_ctrls = []
        self.loc_ctrl_offsets = []
        self.loc_main_grp = None
        self.loc_display_layer = None

        group_names = self.build_main_group_names()
        
        if self.prefix:
            layer_name = f"{self.prefix}_{self.name}_loc_display"
            root_name = f"{self.prefix}_{self.name}_root_ctrl"
            root_offset_name = f"{self.prefix}_{self.name}_root_offsetGrp"
            global_name = f"{self.prefix}_{self.name}_global_ctrl"
            global_offset_name = f"{self.prefix}_{self.name}_global_offsetGrp"
        else:
            layer_name = f"{self.name}_loc_display"
            root_name = f"{self.name}_root_ctrl"
            root_offset_name = f"{self.name}_root_offsetGrp"
            global_name = f"{self.name}_global_ctrl"
            global_offset_name = f"{self.name}_global_offsetGrp"

        # Duplicate checks FIRST
        names_to_check = list(group_names.values())
        names_to_check.append(layer_name)

        if self.create_global_root:
            names_to_check.extend([
                root_name,
                root_offset_name,
                global_name,
                global_offset_name
            ])

        for joint_name in self.joints:
            locator_name = self.build_locator_name(joint_name)
            ctrl_name = self.build_ctrl_name(joint_name)
            ctrl_offset_name = self.build_ctrl_offset_name(joint_name)

            names_to_check.extend([
                locator_name,
                ctrl_name,
                ctrl_offset_name,
            ])

        # Add future branch names too
        for i in range(max(0, len(self.joints) - 1)):
            branch_name = f"{self.name}_{self.suffix}_branch_{i + 1}"
            names_to_check.append(branch_name)
            names_to_check.append(f"{branch_name}_frontCluster")
            names_to_check.append(f"{branch_name}_endCluster")

        for obj_name in names_to_check:
            if cmds.objExists(obj_name):
                om.MGlobal.displayWarning(f"{obj_name} found in scene already.")
                return

        # Only create groups AFTER checks pass
        self.loc_main_grp = cmds.group(empty=True, name=group_names["loc_main_grp"])
        self.loc_grp = cmds.group(empty=True, name=group_names["loc_grp"])
        self.loc_ctrl_grp = cmds.group(empty=True, name=group_names["loc_ctrl_grp"])
        self.loc_cluster_grp = cmds.group(empty=True, name=group_names["loc_cluster_grp"])
        self.branch_grp = cmds.group(empty=True, name=group_names["branch_grp"])

        if len(self.joints) < 1:
            om.MGlobal.displayWarning("Expected at least 1 joint name.")
            return

        # ---------------------------------
        # Create locators
        # ---------------------------------
        for i, joint_name in enumerate(self.joints):
            position = (i * self.distance_between, 0, 0)

            loc_obj = CustomLocator(
                name=joint_name,
                prefix=self.prefix,
                chain_name=self.name,
                orientation=self.orientation
            )
            loc = loc_obj.get_locator_name()

            cmds.xform(loc, worldSpace=True, translation=position)
            cmds.setAttr(f"{loc}.scale", self.loc_size, self.loc_size, self.loc_size, type="double3")
            cmds.makeIdentity(loc, apply=True, scale=True)

            self.locators.append(loc)

        # ---------------------------------
        # Create branches between every pair
        # ---------------------------------
        cluster_handles = []

        for i in range(len(self.locators) - 1):
            branch_name = f"{self.name}_{self.suffix}_branch_{i + 1}"
            branch_data = self.create_cylinder(
                name=branch_name,
                organize=False,
                assign_shader=False
            )

            self.branches.append(branch_data["cylinder"])

            front_cluster_handle = branch_data["front_cluster_handle"]
            end_cluster_handle = branch_data["end_cluster_handle"]

            # front goes to child, end goes to parent
            cmds.matchTransform(front_cluster_handle, self.locators[i + 1], position=True)
            cmds.matchTransform(end_cluster_handle, self.locators[i], position=True)

            cmds.parentConstraint(self.locators[i + 1], front_cluster_handle, maintainOffset=True)
            cmds.parentConstraint(self.locators[i], end_cluster_handle, maintainOffset=True)

            cluster_handles.extend([front_cluster_handle, end_cluster_handle])

        # ---------------------------------
        # Organize cluster handles / branches
        # ---------------------------------
        if cluster_handles:
            cmds.parent(cluster_handles, self.loc_cluster_grp)

        cmds.setAttr(f"{self.loc_cluster_grp}.visibility", False)
        GiancarloHelpers.lock_and_hide_attrs(
            self.loc_cluster_grp,
            ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"],
            lock=True,
            hide=True,
            channelBox=False
        )

        if self.branches:
            cmds.parent(self.branches, self.branch_grp)

        GiancarloHelpers.lock_and_hide_attrs(
            self.branch_grp,
            ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"],
            lock=True,
            hide=True,
            channelBox=False
        )
        cmds.setAttr(f"{self.branch_grp}.overrideEnabled", True)
        cmds.setAttr(f"{self.branch_grp}.overrideDisplayType", 2)
        cmds.setAttr(f"{self.branch_grp}.inheritsTransform", False)

        # ---------------------------------
        # Shader branches if they exist
        # ---------------------------------
        if self.branches:
            branch_shader = GiancarloHelpers.create_and_assign_lambert_shader(
                name="branch_lambert",
                shape_node=self.branches[0],
                hsv=(175.384, 0, 0.032)
            )

            for branch in self.branches[1:]:
                cmds.sets(branch, edit=True, forceElement=branch_shader + "SG")

        # ---------------------------------
        # Aim chain if there is more than 1 locator
        # ---------------------------------
        if len(self.locators) > 1:
            self.setup_aim_chain()

        # ---------------------------------
        # Parent / controls
        # ---------------------------------
        cmds.parent(self.locators, self.loc_grp)
        self.create_locator_ctrls()

        # Parent all main groups under one top-level group
        if self.create_global_root:
            root_global_ctrls = self.create_global_root_ctrl()

            if not root_global_ctrls:
                om.MGlobal.displayWarning("Failed to create root/global controls.")
                return

            self.loc_ctrls[0:0] = [
                root_global_ctrls["global"],
                root_global_ctrls["root"]
            ]

            self.loc_ctrl_offsets[0:0] = [
                root_global_ctrls["global_offset"],
                root_global_ctrls["root_offset"]
            ]

            cmds.parent(
                self.loc_grp,
                self.loc_ctrl_grp,
                self.loc_cluster_grp,
                self.branch_grp,
                root_global_ctrls["root"]
            )

            cmds.parent(root_global_ctrls["global_offset"], self.loc_main_grp)

        else:
            cmds.parent(
                self.loc_grp,
                self.loc_ctrl_grp,
                self.loc_cluster_grp,
                self.branch_grp,
                self.loc_main_grp
            )
        
        if self.display_layer and cmds.objExists(self.display_layer):
            cmds.editDisplayLayerMembers(
                self.display_layer,
                self.loc_grp,
                noRecurse=False
            )
            self.loc_display_layer = self.display_layer

        elif self.create_display_layer:
            self.loc_display_layer = GiancarloHelpers.create_display_layer(
                name=layer_name,
                members=self.loc_grp,
                reference=True
            )
            cmds.setAttr(f"{self.loc_display_layer}.color", 13)
        
        cmds.select(clear=True)
        
        return {
            "locators": self.locators,
            "loc_ctrls": self.loc_ctrls,
            "loc_ctrl_offsets": self.loc_ctrl_offsets,
            "loc_main_grp": self.loc_main_grp,
            "loc_grp": self.loc_grp,
            "loc_ctrl_grp": self.loc_ctrl_grp,
            "branch_grp": self.branch_grp,
            "loc_cluster_grp": self.loc_cluster_grp
        }
            
    def create_global_root_ctrl(self):
        self.global_ctrl = None
        self.global_offset = None
        self.root_ctrl = None
        self.root_offset = None
        
        if self.prefix:
            root_name = f"{self.prefix}_{self.name}_root_ctrl"
            root_offset_name = f"{self.prefix}_{self.name}_root_offsetGrp"
            global_name = f"{self.prefix}_{self.name}_global_ctrl"
            global_offset_name = f"{self.prefix}_{self.name}_global_offsetGrp"
        
        else:
            root_name = f"{self.name}_root_ctrl"
            root_offset_name = f"{self.name}_root_offsetGrp"
            global_name = f"{self.name}_global_ctrl"
            global_offset_name = f"{self.name}_global_offsetGrp"
                        
        self.root_ctrl = self.create_ctrls(ctrl_type=self.root_type, name=root_name, size=self.root_size, color=self.root_color)
        self.root_offset = cmds.group(empty=True, name=root_offset_name)
        cmds.parent(self.root_ctrl, self.root_offset)
        self.global_ctrl = self.create_ctrls(ctrl_type=self.global_type, name=global_name, size=self.global_size, color=self.global_color)
        self.global_offset = cmds.group(self.global_ctrl, name=global_offset_name)
        
        if self.root_type != "diamond":
            cmds.setAttr(f"{self.root_ctrl}.rotateZ", 90)
        if self.root_type == "circle_03":
            cmds.setAttr(f"{self.root_ctrl}.rotateY", 90)
        cmds.setAttr(f"{self.global_offset}.rotateZ", 90)
        cmds.makeIdentity(self.root_ctrl, apply=True, rotate=True)
        cmds.makeIdentity(self.global_offset, apply=True, rotate=True)
        
        align_target = None
        if self.loc_ctrls:
            align_target = self.loc_ctrls[0]
        elif self.locators:
            align_target = self.locators[0]
        
        if align_target:
            cmds.matchTransform(self.global_offset, align_target, position=True)
            cmds.matchTransform(self.root_offset, align_target, position=True)
        
        cmds.parent(self.root_offset, self.global_ctrl)
        
        return {"root": self.root_ctrl, "root_offset": self.root_offset, "global": self.global_ctrl, "global_offset": self.global_offset}
    
    def setup_aim_chain(self):
        if not self.locators or len(self.locators) < 2:
            om.MGlobal.displayWarning("Need at least 2 locators to create aim chain.")
            return

        settings = self.get_orientation_settings()
        aim_vector = settings["aimVector"]
        up_vector = settings["upVector"]

        # ---------------------------------
        # Aim every locator except the last
        # ---------------------------------
        for i in range(len(self.locators) - 1):
            source = self.locators[i]
            target = self.locators[i + 1]

            cmds.aimConstraint(
                target,
                source,
                maintainOffset=False,
                aimVector=aim_vector,
                upVector=up_vector,
                worldUpType="object",
                worldUpObject=target
            )

        # ---------------------------------
        # Special handling for the last locator
        # Use separate aim/up helpers
        # ---------------------------------
        if len(self.locators) >= 2:
            prev_loc = self.locators[-2]
            last_loc = self.locators[-1]

            if self.prefix:
                aim_helper_name = f"{self.prefix}_{self.name}_endAimHelper_loc"
                up_helper_name = f"{self.prefix}_{self.name}_endUpHelper_loc"
                helper_grp_name = f"{self.prefix}_{self.name}_endHelper_offsetGrp"
            else:
                aim_helper_name = f"{self.name}_endAimHelper_loc"
                up_helper_name = f"{self.name}_endUpHelper_loc"
                helper_grp_name = f"{self.name}_endHelper_offsetGrp"

            # Cleanup stale helpers if they already exist
            for obj in [helper_grp_name, aim_helper_name, up_helper_name]:
                if cmds.objExists(obj):
                    cmds.delete(obj)

            # ---------------------------------
            # Get world positions
            # ---------------------------------
            prev_pos = cmds.xform(prev_loc, query=True, worldSpace=True, translation=True)
            last_pos = cmds.xform(last_loc, query=True, worldSpace=True, translation=True)

            # Chain direction = prev -> last
            chain_vec = om.MVector(
                last_pos[0] - prev_pos[0],
                last_pos[1] - prev_pos[1],
                last_pos[2] - prev_pos[2]
            )

            if chain_vec.length() < 1e-8:
                om.MGlobal.displayWarning("Last two locators are too close together to compute aim direction.")
                return

            chain_vec.normalize()

            # ---------------------------------
            # Choose a stable world up seed
            # ---------------------------------
            world_up_seed = om.MVector(0, 1, 0)

            # If chain is nearly parallel to world Y, switch seed
            if abs(chain_vec * world_up_seed) > 0.999:
                world_up_seed = om.MVector(0, 0, 1)

            # Build a perpendicular up direction
            side_vec = chain_vec ^ world_up_seed
            if side_vec.length() < 1e-8:
                world_up_seed = om.MVector(1, 0, 0)
                side_vec = chain_vec ^ world_up_seed

            side_vec.normalize()

            up_dir = side_vec ^ chain_vec
            up_dir.normalize()

            # ---------------------------------
            # Create helpers
            # ---------------------------------
            helper_grp = cmds.group(empty=True, name=helper_grp_name)
            aim_helper = cmds.spaceLocator(name=aim_helper_name)[0]
            up_helper = cmds.spaceLocator(name=up_helper_name)[0]

            cmds.parent(aim_helper, helper_grp)
            cmds.parent(up_helper, helper_grp)

            helper_distance = self.get_helper_distance(
                parent_pos=prev_pos,
                child_pos=last_pos
            )

            aim_helper_pos = om.MVector(last_pos[0], last_pos[1], last_pos[2]) + (chain_vec * helper_distance)
            up_helper_pos = om.MVector(last_pos[0], last_pos[1], last_pos[2]) + (up_dir * helper_distance)
            
            cmds.xform(aim_helper, ws=True, t=(aim_helper_pos.x, aim_helper_pos.y, aim_helper_pos.z))
            cmds.xform(up_helper, ws=True, t=(up_helper_pos.x, up_helper_pos.y, up_helper_pos.z))

            # ---------------------------------
            # Aim the last locator using separate helpers
            # ---------------------------------
            cmds.aimConstraint(
                aim_helper,
                last_loc,
                maintainOffset=False,
                aimVector=aim_vector,
                upVector=up_vector,
                worldUpType="object",
                worldUpObject=up_helper
            )

            cmds.delete(helper_grp)
            cmds.select(clear=True)
    
    def create_cylinder(
        self,
        name,
        organize=False,
        main_grp_name=None,
        mesh_grp_name=None,
        cluster_grp_name=None,
        assign_shader=True
    ):
        cylinder = cmds.polyCylinder(
            name=name,
            radius=self.loc_size / 5,
            constructionHistory=False
        )[0]

        cmds.setAttr(f"{cylinder}.rotateZ", 90)
        cmds.makeIdentity(cylinder, apply=True, rotate=True)

        front_cluster = cmds.cluster(
            f"{cylinder}.vtx[0:19]",
            name=name + "_frontCluster"
        )

        front_cluster_handle = front_cluster[1]
        front_cluster = front_cluster[0]

        end_cluster = cmds.cluster(
            f"{cylinder}.vtx[20:39]",
            name=name + "_endCluster"
        )

        end_cluster_handle = end_cluster[1]
        end_cluster = end_cluster[0]

        main_grp = None
        mesh_grp = None
        cluster_grp = None

        if assign_shader:
            shader = GiancarloHelpers.create_and_assign_lambert_shader(
                name="branch_lambert",
                shape_node=cylinder,
                hsv=(175.384, 0, 0.032)
            )

        if organize:
            main_grp = cmds.group(
                empty=True,
                name=main_grp_name or f"{name}_mainGrp"
            )

            mesh_grp = cmds.group(
                empty=True,
                name=mesh_grp_name or f"{name}_meshGrp"
            )

            cluster_grp = cmds.group(
                empty=True,
                name=cluster_grp_name or f"{name}_clusterGrp"
            )

            cmds.parent(cylinder, mesh_grp)

            cmds.parent(
                front_cluster_handle,
                end_cluster_handle,
                cluster_grp
            )

            cmds.parent(mesh_grp, cluster_grp, main_grp)

            cmds.setAttr(f"{cluster_grp}.visibility", False)

        cmds.select(clear=True)

        return {
            "cylinder": cylinder,
            "front_cluster": front_cluster,
            "front_cluster_handle": front_cluster_handle,
            "end_cluster": end_cluster,
            "end_cluster_handle": end_cluster_handle,
            "main_grp": main_grp,
            "mesh_grp": mesh_grp,
            "cluster_grp": cluster_grp
        }
    
    def locator_positions(self):
        positions = []
        selection = self.locators
        
        if selection:
            for obj in selection:
                positions.append(cmds.xform(obj, query=True, worldSpace=True, translation=True))
        else:
            om.MGlobal.displayWarning("No matching locators found")
            return
            
        return positions
    
    def apply_locator_root_naming(self, locator_root):
        if not locator_root:
            return False

        short_name = locator_root.split("|")[-1]

        if not short_name.endswith("_rigGrp"):
            om.MGlobal.displayWarning(f"Selected locator root does not end with '_rigGrp': {short_name}")
            return False

        base = short_name[:-len("_rigGrp")]  # remove trailing _rigGrp
        parts = base.split("_")

        if len(parts) < 2:
            om.MGlobal.displayWarning(f"Could not parse locator root naming: {short_name}")
            return False

        # suffix is always the last token before _rigGrp
        parsed_suffix = parts[-1]

        # remaining tokens are either:
        #   [name parts...]
        # or
        #   [prefix, name parts...]
        remaining = parts[:-1]

        if len(remaining) >= 2:
            parsed_prefix = remaining[0]
            parsed_name = "_".join(remaining[1:])
        else:
            parsed_prefix = None
            parsed_name = remaining[0]

        self.prefix = parsed_prefix
        self.name = parsed_name
        self.suffix = parsed_suffix
        
        return True
    
    def construct_joints_from_locator_root(self, locator_root):
        if not locator_root or not cmds.objExists(locator_root):
            om.MGlobal.displayWarning("Invalid locator root.")
            return
        
        if not self.apply_locator_root_naming(locator_root):
            return
        
        descendant_nodes = cmds.listRelatives(
            locator_root,
            allDescendents=True,
            type="transform",
            fullPath=False
        ) or []

        ordered_locators = []

        for joint_name in self.joints:
            matches = []

            expected_suffix = f"_{joint_name}_loc"
            for node in descendant_nodes:
                if node.endswith(expected_suffix) and cmds.objExists(node):
                    matches.append(node)

            if len(matches) == 0:
                om.MGlobal.displayWarning(
                    f"Expected locator for joint '{joint_name}' not found under selected locator root."
                )
                return
            
            # Duplicate check
            if len(matches) > 1:
                om.MGlobal.displayWarning(
                    f"Multiple locators matched joint '{joint_name}' under selected locator root: {matches}"
                )
                return

            ordered_locators.append(matches[0])

        self.locators = ordered_locators
        self.loc_main_grp = locator_root

        result = self.construct_joints()
        return result
    
    def create_joints_from_locator_orientation(self):
        built_joints = []

        if not self.locators:
            om.MGlobal.displayWarning("No locators found.")
            return built_joints

        for joint in self.joints:
            if self.prefix:
                joint_name = f"{self.prefix}_{self.name}_{joint}_{self.suffix}"
            else:
                joint_name = f"{self.name}_{joint}_{self.suffix}"

            if cmds.objExists(joint_name):
                om.MGlobal.displayWarning(f"{joint_name} found in scene already.")
                return built_joints

        cmds.select(clear=True)

        for i, locator in enumerate(self.locators):
            joint_name = (
                f"{self.prefix}_{self.name}_{self.joints[i]}_{self.suffix}"
                if self.prefix
                else f"{self.name}_{self.joints[i]}_{self.suffix}"
            )

            joint = cmds.createNode("joint", name=joint_name)

            locator_matrix = cmds.xform(
                locator,
                query=True,
                worldSpace=True,
                matrix=True
            )

            cmds.xform(joint, worldSpace=True, matrix=locator_matrix)

            cmds.makeIdentity(
                joint,
                apply=True,
                translate=False,
                rotate=True,
                scale=False,
                normal=False,
                preserveNormals=True
            )

            if cmds.attributeQuery("radius", node=joint, exists=True):
                cmds.setAttr(f"{joint}.radius", self.joint_size)

            built_joints.append(joint)

        for i in range(1, len(built_joints)):
            child_world_matrix = cmds.xform(
                built_joints[i],
                query=True,
                worldSpace=True,
                matrix=True
            )

            cmds.parent(built_joints[i], built_joints[i - 1])

            cmds.xform(
                built_joints[i],
                worldSpace=True,
                matrix=child_world_matrix
            )

        if self.end_orient == "parent" and built_joints:
            end_joint = built_joints[-1]

            cmds.setAttr(f"{end_joint}.jointOrientX", 0)
            cmds.setAttr(f"{end_joint}.jointOrientY", 0)
            cmds.setAttr(f"{end_joint}.jointOrientZ", 0)

            cmds.setAttr(f"{end_joint}.rotateX", 0)
            cmds.setAttr(f"{end_joint}.rotateY", 0)
            cmds.setAttr(f"{end_joint}.rotateZ", 0)

        return built_joints
        
    def create_joints(self, joint_positions):    
        for joint in self.joints:
            if self.prefix:
                joint_name = f"{self.prefix}_{self.name}_{joint}_{self.suffix}"
            else:
                joint_name = f"{self.name}_{joint}_{self.suffix}"

            if cmds.objExists(joint_name):
                om.MGlobal.displayWarning(f"{joint_name} found in scene already.")
                return

        if not joint_positions:
            return

        if self.prefix:
            prefix_names = [f"{self.prefix}_{self.name}_{joint}" for joint in self.joints]
        else:
            prefix_names = [f"{self.name}_{joint}" for joint in self.joints]

        settings = self.get_joint_orientation_settings()

        if not settings:
            om.MGlobal.displayWarning(f"Unsupported orientation: {self.orientation}")
            return

        # -----------------------------
        # 2-joint case
        # -----------------------------
        if len(joint_positions) == 2:
            builder_locators = self.locators if len(self.locators) == 2 else []
            builder_prefix = self.prefix if self.prefix else "TMP"
                
            if len(builder_locators) != 2:
                raise RuntimeError("Expected exactly 2 locators.")

            parent_locator = builder_locators[0]
            child_locator = builder_locators[1]

            parent_pos = cmds.xform(parent_locator, q=True, ws=True, t=True)
            child_pos = cmds.xform(child_locator, q=True, ws=True, t=True)

            cmds.select(clear=True)

            joint_01 = cmds.joint(
                name=f"{prefix_names[0]}_{self.suffix}",
                position=parent_pos,
                radius=self.joint_size
            )
            joint_02 = cmds.joint(
                name=f"{prefix_names[1]}_{self.suffix}",
                position=child_pos,
                radius=self.joint_size
            )

            # ---------------------------------
            # Create helper (same as your test)
            # ---------------------------------
            helper_loc = cmds.spaceLocator(
                name=f"{builder_prefix}_{self.name}_helper_loc"
            )[0]

            helper_offset = cmds.group(
                helper_loc,
                name=f"{helper_loc}_offsetGrp"
            )

            cmds.matchTransform(helper_offset, joint_01, position=True, rotation=True)

            helper_axis = settings["cross_product"]
            helper_distance = self.get_helper_distance(
                parent_pos=parent_pos,
                child_pos=child_pos
            )

            cmds.setAttr(
                f"{helper_loc}.translate{helper_axis.upper()}",
                helper_distance
            )

            builder = ThreePointJointChain(
                locators=[],
                prefix=builder_prefix,
                name=self.name,
                suffix=self.suffix,
                primary_axis=settings["primary_axis"],
                secondary_axis=settings["secondary_axis"],
                secondary_world_orient=settings["secondary_world_orient"],
                end_orient="parent",
                create_coplanar_mesh=False
            )

            builder.reorient_joint(
                joint_01=joint_01,
                joint_02=joint_02,
                helper_loc=helper_loc,
                primary_axis=settings["primary_axis"],
                secondary_axis=settings["secondary_axis"],
                secondary_world_orient=settings["secondary_world_orient"]
            )

            if self.end_orient == "parent":
                if cmds.listRelatives(joint_02, parent=True):
                    cmds.parent(joint_02, world=True)

                cmds.parent(joint_02, joint_01)

                cmds.setAttr(f"{joint_02}.jointOrientX", 0)
                cmds.setAttr(f"{joint_02}.jointOrientY", 0)
                cmds.setAttr(f"{joint_02}.jointOrientZ", 0)

                cmds.setAttr(f"{joint_02}.rotateX", 0)
                cmds.setAttr(f"{joint_02}.rotateY", 0)
                cmds.setAttr(f"{joint_02}.rotateZ", 0)

            elif self.end_orient == "world":
                child_world_matrix = cmds.xform(joint_02, q=True, ws=True, m=True)

                cmds.parent(joint_02, world=True)

                cmds.setAttr(f"{joint_02}.jointOrientX", 0)
                cmds.setAttr(f"{joint_02}.jointOrientY", 0)
                cmds.setAttr(f"{joint_02}.jointOrientZ", 0)

                cmds.setAttr(f"{joint_02}.rotateX", 0)
                cmds.setAttr(f"{joint_02}.rotateY", 0)
                cmds.setAttr(f"{joint_02}.rotateZ", 0)

                cmds.parent(joint_02, joint_01)
                cmds.xform(joint_02, ws=True, m=child_world_matrix)

                cmds.makeIdentity(
                    joint_02,
                    apply=True,
                    translate=False,
                    rotate=True,
                    scale=False,
                    normal=False,
                    preserveNormals=True
                )

            else:
                cmds.delete(helper_offset)
                cmds.error('end_orient must be "parent" or "world".')

            cmds.delete(helper_offset)

            return [joint_01, joint_02]
            
        # -----------------------------
        # 3-joint case
        # -----------------------------
        elif len(joint_positions) == 3:
            builder_locators = self.locators if len(self.locators) == 3 else []
            builder_prefix = self.prefix if self.prefix else "TMP"
            
            secondary_world_vector = None

            if self.use_locator_orientation and self.loc_ctrls:
                secondary_world_vector = self.get_world_axis_from_node(
                    self.loc_ctrls[0],
                    axis=settings["secondary_axis"]
                )
           
            secondary_world_vector_01 = None
            secondary_world_vector_02 = None

            if self.use_locator_orientation and self.loc_ctrls:
                secondary_world_vector_01 = self.get_world_axis_from_node(
                    self.loc_ctrls[0],
                    axis=settings["secondary_axis"]
                )

                secondary_world_vector_02 = self.get_world_axis_from_node(
                    self.loc_ctrls[1],
                    axis=settings["secondary_axis"]
                )
                
            builder = ThreePointJointChain(
                locators=builder_locators,
                prefix=builder_prefix,
                name=self.name,
                suffix=self.suffix,
                primary_axis=settings["primary_axis"],
                secondary_axis=settings["secondary_axis"],
                secondary_world_orient=settings["secondary_world_orient"],
                secondary_world_vector=secondary_world_vector,
                end_orient=self.end_orient,
                create_coplanar_mesh=self.create_coplanar_mesh,
                use_cross_as_secondary=self.use_cross_as_secondary,
                secondary_world_vector_01=secondary_world_vector_01,
                secondary_world_vector_02=secondary_world_vector_02,
            )

            result = builder.build()
            built_joints = result.get("joints", [])
            self.coplanar_facet = result.get("facet", None)
            self.coplanar_clusters = result.get("clusters", None)

            if len(built_joints) != 3:
                raise RuntimeError("ThreePointJointChain did not return exactly 3 joints.")

            renamed_joints = self.rename_built_joint_chain(
                built_joints,
                prefix_names
            )

            return renamed_joints

        # -----------------------------
        # 4 or more joints
        # -----------------------------
        elif len(joint_positions) > 3:
            builder_locators = self.locators if len(self.locators) == len(joint_positions) else []
            builder_prefix = self.prefix if self.prefix else "TMP"

            if len(builder_locators) != len(joint_positions):
                raise RuntimeError("Locator count does not match joint_positions count.")

            # Build the last 3 joints first
            last_three_locators = builder_locators[-3:]
            
            secondary_world_vector = None

            if self.use_locator_orientation and self.loc_ctrls:
                start_index = len(builder_locators) - 3
                secondary_world_vector = self.get_world_axis_from_node(
                    self.loc_ctrls[start_index],
                    axis=settings["secondary_axis"]
                )
            
            secondary_world_vector_01 = None
            secondary_world_vector_02 = None

            if self.use_locator_orientation and self.loc_ctrls:
                start_index = len(builder_locators) - 3

                secondary_world_vector_01 = self.get_world_axis_from_node(
                    self.loc_ctrls[start_index],
                    axis=settings["secondary_axis"]
                )

                secondary_world_vector_02 = self.get_world_axis_from_node(
                    self.loc_ctrls[start_index + 1],
                    axis=settings["secondary_axis"]
                )
            
            builder = ThreePointJointChain(
                locators=last_three_locators,
                prefix=builder_prefix,
                name=self.name,
                suffix=self.suffix,
                primary_axis=settings["primary_axis"],
                secondary_axis=settings["secondary_axis"],
                secondary_world_orient=settings["secondary_world_orient"],
                secondary_world_vector=secondary_world_vector,
                end_orient=self.end_orient,
                create_coplanar_mesh=self.create_coplanar_mesh,
                use_cross_as_secondary=self.use_cross_as_secondary,
                secondary_world_vector_01=secondary_world_vector_01,
                secondary_world_vector_02=secondary_world_vector_02,
            )

            result = builder.build()
            built_joints = result.get("joints", [])
            self.coplanar_facet = result.get("facet", None)
            self.coplanar_clusters = result.get("clusters", None)

            if len(built_joints) != 3:
                raise RuntimeError("ThreePointJointChain did not return exactly 3 joints.")

            # Prepend every earlier joint, working backwards
            # Example with 5 locators:
                # indices 0,1 are prepended
                # last 3 are indices 2,3,4
            for prepend_index in range(len(builder_locators) - 4, -1, -1):
                parent_locator = builder_locators[prepend_index]
                child_joint = built_joints[0]

                parent_pos = cmds.xform(
                    parent_locator,
                    query=True,
                    worldSpace=True,
                    translation=True
                )

                temp_joint_name = f"{builder_prefix}_{self.name}_prepend_{prepend_index}_{self.suffix}"

                cmds.select(clear=True)
                new_joint = cmds.joint(name=temp_joint_name, position=parent_pos, radius=self.joint_size)

                # Parent current root under this new joint
                cmds.parent(child_joint, new_joint)

                # Create temp helper loc aligned to child joint
                temp_loc = cmds.spaceLocator(name=f"{builder_prefix}_{self.name}_tempAimLoc_{prepend_index}")[0]
                temp_loc_offset = cmds.group(temp_loc, name=f"{temp_loc}_offsetGrp")

                cmds.matchTransform(temp_loc_offset, child_joint, position=True, rotation=True)

                child_pos = cmds.xform(
                    child_joint,
                    query=True,
                    worldSpace=True,
                    translation=True
                )

                helper_distance = self.get_helper_distance(
                    parent_pos=parent_pos,
                    child_pos=child_pos
                )

                cmds.setAttr(
                    f"{temp_loc}.translate{settings['cross_product'].upper()}",
                    helper_distance
                )

                builder.reorient_joint(
                    joint_01=new_joint,
                    joint_02=child_joint,
                    helper_loc=temp_loc,
                    primary_axis=settings["primary_axis"],
                    secondary_axis=settings["secondary_axis"],
                    secondary_world_orient=settings["secondary_world_orient"]
                )

                cmds.delete(temp_loc_offset)

                # Add new parent to the front of the chain list
                built_joints.insert(0, new_joint)

            if len(built_joints) != len(joint_positions):
                raise RuntimeError(
                    f"Expected {len(joint_positions)} joints but got {len(built_joints)}"
                )

            renamed_joints = self.rename_built_joint_chain(
                built_joints,
                prefix_names
            )

            return renamed_joints

    def create_ctrls(self, ctrl_type, name, size=1, color=13):
        mult_size = self.loc_size * 2
        
        ctrl_map = {
            "circle_01": GiancarloCurveLibrary.circle,
            "circle_02": GiancarloCurveLibrary.circle_02_ctrl,
            "circle_03": GiancarloCurveLibrary.global_ctrl,
            "sphere": GiancarloCurveLibrary.pv_ik_ctrl,
            "square": GiancarloCurveLibrary.square_ctrl,
            "cube": GiancarloCurveLibrary.cube_ctrl,
            "diamond": GiancarloCurveLibrary.hand_ik_ctrl,
            "four_way_arrow": GiancarloCurveLibrary.four_way_arrow,
        }
        
        ctrl_func = ctrl_map.get(ctrl_type)

        if ctrl_func is None:
            om.MGlobal.displayWarning(f"{ctrl_type} is not a valid control type.")
            return
        
        if color is None:
            om.MGlobal.displayWarning(f"{color} is not a valid control color.")
            return

        return ctrl_func(name=name, size=size*mult_size, color=color, override=True)
    
    def get_world_axis_from_node(self, node, axis="y"):
        matrix = cmds.xform(node, query=True, worldSpace=True, matrix=True)

        axis = axis.lower()
        sign = -1.0 if axis.startswith("-") else 1.0
        axis = axis[-1]

        if axis == "x":
            vec = [matrix[0], matrix[1], matrix[2]]
        elif axis == "y":
            vec = [matrix[4], matrix[5], matrix[6]]
        elif axis == "z":
            vec = [matrix[8], matrix[9], matrix[10]]
        else:
            vec = [0, 1, 0]

        return [
            vec[0] * sign,
            vec[1] * sign,
            vec[2] * sign
        ]
    
    def setup_ctrl_aim_chain(self):
        if not self.loc_ctrls or len(self.loc_ctrls) < 2:
            return

        settings = self.get_orientation_settings()
        aim_vector = settings["aimVector"]
        up_vector = settings["upVector"]

        for i in range(len(self.loc_ctrls) - 1):
            ctrl = self.loc_ctrls[i]
            child_ctrl = self.loc_ctrls[i + 1]

            if not cmds.objExists(ctrl):
                continue

            if not cmds.objExists(child_ctrl):
                continue

            cmds.aimConstraint(
                child_ctrl,
                ctrl,
                maintainOffset=False,
                aimVector=aim_vector,
                upVector=up_vector,
                worldUpType="object",
                worldUpObject=child_ctrl
            )
        
    def match_end_locator_to_parent_rotation(self, end_loc, end_ctrl, parent_ctrl):
        layer = self.loc_display_layer

        if layer and cmds.objExists(layer):
            cmds.setAttr("{}.displayType".format(layer), 0)

        cmds.matchTransform(end_loc, parent_ctrl, rotation=True)
        cmds.matchTransform(end_ctrl, parent_ctrl, rotation=True)

        if layer and cmds.objExists(layer):
            cmds.setAttr("{}.displayType".format(layer), 2)

    def create_locator_ctrls(self):
        if not self.locators:
            om.MGlobal.displayWarning("No locators found. Create locators first.")
            return

        self.loc_ctrls = []
        self.loc_ctrl_offsets = []

        for i, joint_name in enumerate(self.joints):
            locator = self.locators[i]

            ctrl_name = self.build_ctrl_name(joint_name)
            ctrl_offset_name = self.build_ctrl_offset_name(joint_name)

            ctrl = self.create_ctrls(
                ctrl_type=self.ctrl_type,
                name=ctrl_name,
                size=self.ctrl_size,
                color=self.ctrl_color
            )

            if not ctrl:
                om.MGlobal.displayWarning(
                    "Failed to create control for {}".format(locator)
                )
                continue

            ctrl_offset = cmds.group(ctrl, name=ctrl_offset_name)

            cmds.delete(
                cmds.parentConstraint(
                    locator,
                    ctrl_offset,
                    maintainOffset=False
                )
            )
            
            GiancarloHelpers.transfer_to_offset_parent_matrix(ctrl_offset)
            
            # Reset ctrl values under the matched offset.
            cmds.setAttr(f"{ctrl}.translateX", 0)
            cmds.setAttr(f"{ctrl}.translateY", 0)
            cmds.setAttr(f"{ctrl}.translateZ", 0)
            cmds.setAttr(f"{ctrl}.rotateX", 0)
            cmds.setAttr(f"{ctrl}.rotateY", 0)
            cmds.setAttr(f"{ctrl}.rotateZ", 0)

            # Ctrl moves locator.
            cmds.pointConstraint(
                ctrl,
                locator,
                maintainOffset=False
            )

            self.loc_ctrls.append(ctrl)
            self.loc_ctrl_offsets.append(ctrl_offset)

        # Aim the actual ctrls at their child ctrls.
        self.setup_ctrl_aim_chain()

        if self.loc_ctrl_offsets:
            cmds.parent(self.loc_ctrl_offsets, self.loc_ctrl_grp)

    def delete_locators(self):
        deleted_any = False

        loc_main_grp = getattr(self, "loc_main_grp", None)
        if loc_main_grp and cmds.objExists(loc_main_grp):
            cmds.delete(loc_main_grp)
            deleted_any = True

        loc_display_layer = getattr(self, "loc_display_layer", None)
        if loc_display_layer and cmds.objExists(loc_display_layer):
            cmds.delete(loc_display_layer)
            deleted_any = True

        # Fallback in case main group is missing but some child groups still exist
        groups_to_delete = [
            getattr(self, "global_offset", None),
            getattr(self, "root_offset", None),
            getattr(self, "loc_grp", None),
            getattr(self, "branch_grp", None),
            getattr(self, "loc_cluster_grp", None),
            getattr(self, "loc_ctrl_grp", None),
        ]

        for grp in groups_to_delete:
            if grp and cmds.objExists(grp):
                cmds.delete(grp)
                deleted_any = True

        if not deleted_any:
            om.MGlobal.displayWarning("Cannot delete: No locator rig groups or display layer found")

        return deleted_any
    
    def delete_joints(self):
        deleted_any = False

        jnt_main_grp = getattr(self, "jnt_main_grp", None)
        if jnt_main_grp and cmds.objExists(jnt_main_grp):
            cmds.delete(jnt_main_grp)
            deleted_any = True

        jnt_display_layer = getattr(self, "jnt_display_layer", None)
        if jnt_display_layer and cmds.objExists(jnt_display_layer):
            cmds.delete(jnt_display_layer)
            deleted_any = True

        groups_to_delete = [
            getattr(self, "jnt_joints_grp", None),
            getattr(self, "jnt_mesh_grp", None),
            getattr(self, "jnt_cluster_grp", None),
        ]

        for grp in groups_to_delete:
            if grp and cmds.objExists(grp):
                cmds.delete(grp)
                deleted_any = True

        existing_joints = []
        for joint in getattr(self, "built_joints", []):
            if joint and cmds.objExists(joint):
                existing_joints.append(joint)

        if existing_joints:
            try:
                cmds.delete(existing_joints)
                deleted_any = True
            except Exception as e:
                om.MGlobal.displayWarning(f"Failed to delete cached joints: {e}")

        if not deleted_any:
            om.MGlobal.displayWarning(
                "Cannot delete: No joint rig groups, joints, or display layer found."
            )
            return False

        self.clear_cached_joint_state()
        return True
    
    def clear_cached_locator_state(self):
        self.loc_main_grp = None
        self.root_ctrl = None
        self.root_offset = None
        self.global_ctrl = None
        self.global_offset = None
        self.loc_display_layer = None
        self.locators = []
        self.branches = []
        self.loc_ctrls = []
        self.loc_ctrl_offsets = []

        self.loc_grp = None
        self.branch_grp = None
        self.loc_cluster_grp = None
        self.loc_ctrl_grp = None
            
    def clear_cached_joint_state(self):
        self.built_joints = []
        self.coplanar_facet = None
        self.coplanar_clusters = []

        self.jnt_display_layer = None
        self.jnt_main_grp = None
        self.jnt_mesh_grp = None
        self.jnt_joints_grp = None
        self.jnt_cluster_grp = None
        
    def construct_joints(self):
        if self.prefix:
            layer_name = f"{self.prefix}_{self.name}_jnt_display"
        else:
            layer_name = f"{self.name}_jnt_display"
        
        group_names = self.build_main_group_names()
        
        self.jnt_main_grp = None
        self.jnt_mesh_grp = None
        self.jnt_joints_grp = None
        self.jnt_cluster_grp = None
        
        joint_positions = self.locator_positions()
        built_joints = self.create_joints(joint_positions)

        if built_joints:
            self.built_joints = built_joints
        else:
            self.built_joints = []
            om.MGlobal.displayWarning("No joints were built.")
            return self.built_joints
        
        for jnt in self.built_joints:
            if cmds.objExists(jnt) and cmds.attributeQuery("displayLocalAxis", node=jnt, exists=True):
                cmds.setAttr(f"{jnt}.displayLocalAxis", self.display_LRA)
        
        self.jnt_joints_grp = cmds.group(self.built_joints[0], name=group_names["jnt_joints_grp"])
        
        self.jnt_main_grp = cmds.group(self.jnt_joints_grp, name=group_names["jnt_main_grp"])
        
        self.built_joints = cmds.listRelatives(
            self.jnt_joints_grp,
            allDescendents=True,
            type="joint",
            fullPath=True
        ) or []

        self.built_joints.reverse()
        
        if self.coplanar_facet:
            self.jnt_mesh_grp = cmds.group(self.coplanar_facet, name=group_names["jnt_mesh_grp"])
            cmds.parent(self.jnt_mesh_grp, self.jnt_main_grp)
            clusters = [cluster["handle"] for cluster in (self.coplanar_clusters or [])]
            if clusters:
                self.jnt_cluster_grp = cmds.group(clusters, name=group_names["jnt_cluster_grp"])
                cmds.parent(self.jnt_cluster_grp, self.jnt_main_grp)
        
        if self.display_layer and cmds.objExists(self.display_layer):
            cmds.editDisplayLayerMembers(
                self.display_layer,
                self.built_joints,
                noRecurse=False
            )

            self.jnt_display_layer = self.display_layer

        elif self.create_display_layer:
            self.jnt_display_layer = GiancarloHelpers.create_display_layer(
                name=layer_name,
                members=self.built_joints,
                reference=False
            )

            cmds.setAttr(f"{self.jnt_display_layer}.color", 28)
        
        cmds.select(clear=True)
        
        return {
            "joints": self.built_joints, 
            "main_grp": self.jnt_main_grp, 
            "joint_grp": self.jnt_joints_grp, 
            "mesh_grp": self.jnt_mesh_grp, 
            "cluster_grp": self.jnt_cluster_grp
        }

if __name__ == "__main__":
    
    # cmds.file(f=True, new=True)
    
    name = "arm_01"
    prefix = "L"
    suffix = "ik"
    ctrl_type = "sphere"
    ctrl_size = 1
    ctrl_color = 13
    root_type = "diamond"
    root_size = 2
    root_color = 17
    global_type = "four_way_arrow"
    global_size = 3
    global_color = 14
    joints = ["clavicle", "shoulder", "elbow", "hand"]
    orientation = "z"
    display_LRA = True
    loc_size = 0.5
    joint_size = 1.0
    distance_between = 3
    end_orient = "parent"           # "parent" or "world"
    create_coplanar_mesh = False
    create_global_root = False
    create_display_layer = True
    display_layer = None
    use_locator_orientation=False

    arm_jnt_01 = JointChainBuilder(
        name=name,
        prefix=prefix,
        suffix=suffix,
        ctrl_type=ctrl_type,
        ctrl_size=ctrl_size,
        ctrl_color=ctrl_color,
        root_type = root_type,
        root_size = root_size,
        root_color = root_color,
        global_type = global_type,
        global_size = global_size,
        global_color = global_color,
        joints=joints,
        orientation=orientation,
        display_LRA = display_LRA,
        loc_size=loc_size,
        joint_size=joint_size,
        distance_between = distance_between,
        end_orient=end_orient,
        create_coplanar_mesh=create_coplanar_mesh,
        create_global_root=create_global_root,
        create_display_layer=create_display_layer,
        display_layer=display_layer,
        use_locator_orientation=use_locator_orientation
    )
    # arm_jnt_01 = arm_jnt_01.create_cylinder(name="null", organize=True, assign_shader=False)
    arm_01 = arm_jnt_01.create_locators()
    print(arm_01["loc_ctrls"])
    print(arm_01["loc_ctrl_offsets"])
    # built_joints = arm_jnt_01.construct_joints()
    # print(built_joints["joints"])
    # arm_jnt_01.delete_locators()
    # arm_jnt_01.delete_joints()
           
