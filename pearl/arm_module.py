import maya.cmds as cmds
import maya.OpenMaya as om

from PearlAutoRig.pearl.joint_chain_builder import JointChainBuilder
from PearlAutoRig.pearl.locator_preset_manager import LocatorPresetManager

from GiancarloHelpers import GiancarloHelpers


class ArmModule(object):

    def __init__(
        self,
        loc_type,
        fingers=True,
        finger_count=4,
        thumb=True,
        finger_segments=3,
        name="arm_01",
        prefix="L",
        suffix="jnt",
        ctrl_type="sphere",
        ctrl_size=1,
        ctrl_color=13,
        root_type="diamond",
        root_size=2,
        root_color=17,
        global_type="four_way_arrow",
        global_size=3,
        global_color=14,
        joints=None,
        orientation="x",
        display_LRA=False,
        loc_size=0.5,
        distance_between=3,
        end_orient="parent",
        create_coplanar_mesh=False,
        position_preset="A-Pose",
        finger_orientation_mode="propagated"
    ):
        default_joints = ["clavicle", "shoulder", "elbow", "wrist"]
        
        clean_joints = [j.strip() for j in (joints or []) if j and j.strip()]
        if not clean_joints:
            om.MGlobal.displayWarning(
                f"No valid arm joints were provided. Using default joints: {default_joints}"
                
            )
            joints = default_joints[:]
        else:
            joints = clean_joints

        self.loc_type = loc_type
        self.fingers = fingers
        self.finger_count = finger_count
        self.thumb = thumb
        self.finger_segments = finger_segments
        self.name = name
        self.prefix = prefix
        self.suffix = suffix
        self.ctrl_type = ctrl_type
        self.ctrl_size = ctrl_size
        self.ctrl_color = ctrl_color
        self.root_type = root_type
        self.root_size = root_size
        self.root_color = root_color
        self.global_type = global_type
        self.global_size = global_size
        self.global_color = global_color
        self.joints = joints
        self.orientation = orientation
        self.display_LRA = display_LRA
        self.loc_size = loc_size
        self.distance_between = distance_between
        self.end_orient = end_orient
        self.create_coplanar_mesh = create_coplanar_mesh
        self.position_preset = position_preset
        self.finger_orientation_mode = finger_orientation_mode
        
        # "propagated" = root uses sphere, rest follow root plane
        # "per_joint" = every joint uses sphere direction

        self.builder = None
        self.finger_builder = None
        self.finger_joints = ["thumb", "index", "middle", "ring", "pinkie"]
        self.locs = {}
        self.finger_locs = {}
        self.finger_main_grp = None
        self.hand_up_ref_grp = None
        
    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
        
    def create_locators(self):
        self.left_biped_arm(
            self.fingers,
            self.finger_count,
            self.thumb,
            self.finger_segments
            )

        return self.locs
                        
    def create_joints(self, delete_locators_after=True):
        if not self.builder:
            om.MGlobal.displayWarning("No builder found. Create locators first.")
            return

        # Build the arm joints first.
        joint_result = self.builder.construct_joints()

        if not joint_result:
            om.MGlobal.displayWarning("Failed to construct arm joints.")
            return

        arm_joints = joint_result.get("joints", [])
        
        self.apply_joint_size_to_joints(
            arm_joints,
            self.builder.joint_size
        )

        wrist_joint = None

        if self.joints:
            wrist_index = len(self.joints) - 1

            if wrist_index < len(arm_joints):
                wrist_joint = arm_joints[wrist_index]

        if not wrist_joint or not cmds.objExists(wrist_joint):
            om.MGlobal.displayWarning("Could not find wrist joint for finger parenting.")

        # Build finger joints using each finger's own JointChainBuilder.
        finger_joint_results = {}

        if self.finger_locs and wrist_joint and cmds.objExists(wrist_joint):
            finger_joint_results = self.create_finger_joints(wrist_joint)

        # Delete locators only AFTER arm and finger joints are finished.
        if delete_locators_after:
            self.builder.delete_locators()
            self.builder.clear_cached_locator_state()

            self.locs = {}
            self.finger_locs = {}
            self.finger_main_grp = None
        
        cmds.select(clear=True)
        
        return {
            "arm": joint_result,
            "fingers": finger_joint_results
        }
    
    # ---------------------------------------------------------
    # Pose data
    # ---------------------------------------------------------
    
    def get_pose_module_key(self):
        return self.loc_type
    
    def get_hardcoded_default_positions(self):
        preset = LocatorPresetManager.load_preset(
            self.get_pose_module_key(),  # Example: "Left_Biped_Arm"
            self.position_preset         # Example: "A-Pose"
        )

        if preset:
            return self.normalize_pose_for_current_finger_segments(preset)

        om.MGlobal.displayWarning(
            "Could not find position preset: {}. "
            "Using hardcoded fallback.".format(
                self.position_preset
            )
        )

        positions = {
            "clavicle": [2.927, 147.262, 2.561],
            "shoulder": [12.051, 144.032, -1.583],
            "elbow": [27.838, 128.785, -3.762],
            "wrist": [42.221, 116.034, 9.606],

            "femur": [9.972, 90.51, -0.394],
            "tibia": [9.972, 54.559, 0.992],
            "foot": [9.972, 13.716, -7.324],
            "ball": [9.972, -0.014, 5.551],
            "toe_end": [9.972, -0.011, 15.678],
            "heel": [9.972, -0.014, -16.072],
            "bank_out": [17.149, 0, 5.223],
            "bank_in": [3.01, 0, 6],

            "pelvis": [0, 95.859, -0.486],
            "spine_01": [0, 108.262, 2.431],
            "spine_02": [0, 115.631, 3.82],
            "chest": [0, 127.026, 3.731],
            "neck": [0, 150.971, -1.684],
            "head": [0, 161.882, 0.053],

            "index_01": [46.432, 111, 16.066],
            "index_02": [47.767, 108.999, 18.034],
            "index_03": [48.06, 107.089, 19.035],
            "index_04": [47.56, 104.59, 19.698],

            "middle_01": [47.723, 110.748, 14.501],
            "middle_02": [49.666, 107.837, 15.791],
            "middle_03": [49.876, 105.37, 16.524],
            "middle_04": [49.688, 103.064, 17.097],

            "ring_01": [48.56, 109.955, 12.577],
            "ring_02": [49.999, 107.164, 13.133],
            "ring_03": [50.137, 105.211, 13.338],
            "ring_04": [49.522, 103.333, 13.296],

            "pinkie_01": [48.425, 109.072, 10.771],
            "pinkie_02": [49.091, 106.726, 10.862],
            "pinkie_03": [49.032, 105.544, 10.956],
            "pinkie_04": [48.538, 103.902, 10.975],

            "thumb_01": [41.875, 113.392, 12.821],
            "thumb_02": [41.598, 111.402, 14.4],
            "thumb_03": [41.648, 109.502, 15.788],
            "thumb_04": [41.972, 107.137, 17.555],
            "thumb_up": [38.474, 111.781, 19.42],
            
            "wrist_rotation": 0,
            "index_rotation": 27.5,
            "middle_rotation": 1.7,
            "ring_rotation": 11.3,
            "pinkie_rotation": 2.2,
            "thumb_rotation": 26.2
        }

        return positions
            
    def save_default_a_pose_to_json(self):
        positions = self.get_hardcoded_default_positions()

        LocatorPresetManager.save_preset(
            self.loc_type,
            "A-Pose",
            positions
        )

        om.MGlobal.displayInfo("Saved default A-Pose to JSON.")
    
    def get_pose_translation(self, pose_data, key):
        value = pose_data.get(key)

        if isinstance(value, dict):
            # New JSON format:
            # key: {
            #     "offset": {"translate": [...], "rotate": [...]},
            #     "ctrl": {"translate": [...], "rotate": [...]}
            # }
            if "offset" in value:
                offset_data = value.get("offset") or {}
                return offset_data.get("translate")

            # Older dict format:
            # key: {"translation": [...]}
            return value.get("translation")

        # Very old format:
        # key: [...]
        return value
        
    def get_saved_finger_up_ref_pos(
        self,
        pose_data,
        finger
    ):
        metadata = pose_data.get("metadata") or {}
        
        finger_ref = metadata.get(
            "finger_up_references"
        ) or {}
        
        finger_data = finger_ref.get(finger) or {}
        
        return finger_data.get("world_translate")
    
    def lerp_position(self, a, b, t):
        if not a or not b:
            return None

        return [
            a[0] + ((b[0] - a[0]) * t),
            a[1] + ((b[1] - a[1]) * t),
            a[2] + ((b[2] - a[2]) * t),
        ]
    
    def normalize_pose_for_current_finger_segments(self, pose_data):
        if not pose_data:
            return pose_data

        normalized = dict(pose_data)

        finger_names = self.get_finger_order()[:int(self.finger_count)]

        if self.thumb:
            finger_names.append("thumb")

        for finger in finger_names:
            p01 = self.get_pose_translation(normalized, "{}_01".format(finger))
            p02 = self.get_pose_translation(normalized, "{}_02".format(finger))
            p03 = self.get_pose_translation(normalized, "{}_03".format(finger))
            p04 = self.get_pose_translation(normalized, "{}_04".format(finger))

            if not p02:
                p02 = self.lerp_position(p01, p04, 0.33)
                if p02:
                    normalized["{}_02".format(finger)] = p02

            if not p03:
                p03 = self.lerp_position(p02 or p01, p04, 0.5)
                if p03:
                    normalized["{}_03".format(finger)] = p03

        return normalized
        
    # ---------------------------------------------------------
    # Builder creation
    # ---------------------------------------------------------
    
    def build_joint_chain_builder(self):
        self.builder = JointChainBuilder(
            name=self.name,
            prefix=self.prefix,
            suffix=self.suffix,
            ctrl_type=self.ctrl_type,
            ctrl_size=self.ctrl_size,
            ctrl_color=self.ctrl_color,
            root_type=self.root_type,
            root_size=self.root_size,
            root_color=self.root_color,
            global_type=self.global_type,
            global_size=self.global_size,
            global_color=self.global_color,
            joints=self.joints,
            orientation=self.orientation,
            display_LRA=self.display_LRA,
            loc_size=self.loc_size,
            distance_between=self.distance_between,
            end_orient=self.end_orient,
            create_coplanar_mesh=self.create_coplanar_mesh,
            create_global_root=True,
            create_display_layer=True,
            display_layer=None,
            use_locator_orientation=False
        )
        return self.builder
        
    def finger_chain_builder(self, finger_joints):
        finger_name = finger_joints[0].split("_")[0]

        clean_finger_joints = []

        for joint in finger_joints:
            clean_name = joint.replace(finger_name + "_", "")
            clean_finger_joints.append(clean_name)

        self.finger_builder = JointChainBuilder(
            name="{}_{}".format(self.name, finger_name),
            prefix=self.prefix,
            suffix=self.suffix,
            ctrl_type=self.ctrl_type,
            ctrl_size=self.ctrl_size,
            ctrl_color=self.ctrl_color,
            root_type=self.root_type,
            root_size=self.root_size/1.5,
            root_color=self.root_color,
            global_type=self.global_type,
            global_size=self.global_size/1.5,
            global_color=self.global_color,
            joints=clean_finger_joints,
            orientation=self.orientation,
            display_LRA=self.display_LRA,
            loc_size=self.loc_size/2.5,
            distance_between=self.distance_between,
            end_orient=self.end_orient,
            create_coplanar_mesh=False,
            create_global_root=False,
            create_display_layer=False,
            display_layer=self.builder.loc_display_layer,
            use_locator_orientation=True if finger_name != "thumb" else False,
            use_cross_as_secondary=True if finger_name == "thumb" else False
        )

        return self.finger_builder
    
    def build_fingers(self, finger, segments=1):
        if finger not in self.finger_joints:
            om.MGlobal.displayWarning(
                "{} is not a valid finger. Valid fingers are: {}".format(
                    finger, self.finger_joints
                )
            )
            return

        segments = int(segments)

        if segments < 1:
            segments = 1
        elif segments > 3:
            segments = 3

        max_joints = 4

        if segments == 1:
            finger_joints = [
                "{}_01".format(finger),
                "{}_0{}".format(finger, max_joints)
            ]

        elif segments == 2:
            finger_joints = [
                "{}_01".format(finger),
                "{}_02".format(finger),
                "{}_0{}".format(finger, max_joints)
            ]

        else:
            finger_joints = [
                "{}_01".format(finger),
                "{}_02".format(finger),
                "{}_03".format(finger),
                "{}_04".format(finger)
            ]

        return self.finger_chain_builder(finger_joints)
    
    def get_finger_order(self):
        return ["index", "middle", "ring", "pinkie"]
    
    def build_finger_joint_names_for_position_lookup(self, finger, joints):
        return ["{}_{}".format(finger, joint) for joint in joints]
    
    # ---------------------------------------------------------
    # Arm locator creation
    # ---------------------------------------------------------
    
    def left_biped_arm(self, fingers=False, finger_count=1, thumb=False, finger_segments=3):
        self.locs = {}

        pos = self.get_hardcoded_default_positions()

        builder = self.build_joint_chain_builder()
        self.locs = builder.create_locators()

        if not self.locs:
            om.MGlobal.displayWarning("Failed to create locators.")
            return

        loc_ctrl_offsets = self.locs.get("loc_ctrl_offsets", [])
        loc_ctrls = self.locs.get("loc_ctrls", [])
        locators = self.locs.get("locators", [])

        if len(loc_ctrl_offsets) < 2 or len(loc_ctrls) < 2:
            om.MGlobal.displayWarning("Expected global/root controls in locator result.")
            return

        global_offset = loc_ctrl_offsets[0]
        root_offset = loc_ctrl_offsets[1]
        joint_ctrls = loc_ctrls[2:]
        joint_offsets = loc_ctrl_offsets[2:]

        if len(joint_ctrls) == 4:
            joint_keys = [
                "clavicle",
                "shoulder",
                "elbow",
                "wrist"
            ]

        elif len(joint_ctrls) == 3:
            joint_keys = [
                "shoulder",
                "elbow",
                "wrist"
            ]

        else:
            om.MGlobal.displayWarning(
                "Left_Biped_Arm expects either 3 or 4 joints."
            )
            return
        
        joint_positions = []

        for index, key in enumerate(joint_keys):
            position = self.get_pose_translation(
                pos,
                key
            )

            # Legacy custom-pose support.
            if (
                position is None
                and index < len(self.joints)
            ):
                legacy_key = self.joints[index]

                position = self.get_pose_translation(
                    pos,
                    legacy_key
                )

            joint_positions.append(position)

        for key, position in zip(joint_keys, joint_positions):
            if position is None:
                om.MGlobal.displayWarning(
                    "Pose '{}' is missing usable "
                    "offset.translate for key: {}".format(
                        self.position_preset,
                        key
                    )
                )
                return

        root_global_position = joint_positions[0]

        if cmds.objExists(global_offset):
            cmds.xform(global_offset, worldSpace=True, translation=root_global_position)
        else:
            om.MGlobal.displayWarning("Global offset does not exist: {}".format(global_offset))
            return

        if cmds.objExists(root_offset):
            cmds.xform(root_offset, worldSpace=True, translation=root_global_position)
        else:
            om.MGlobal.displayWarning("Root offset does not exist: {}".format(root_offset))
            return

        for ctrl, position in zip(joint_ctrls, joint_positions):
            if cmds.objExists(ctrl):
                cmds.xform(ctrl, worldSpace=True, translation=position)
            else:
                om.MGlobal.displayWarning("Control does not exist: {}".format(ctrl))
        
        for offset, ctrl, locator in zip(joint_offsets, joint_ctrls, locators):
            cmds.parent(ctrl, world=True)
            cmds.matchTransform(offset, locator, position=True, rotation=True)
            cmds.parent(ctrl, offset)
          
        if len(locators) >= 2 and len(loc_ctrls) >= 2:
            builder.match_end_locator_to_parent_rotation(
                end_loc=locators[-1],
                end_ctrl=joint_offsets[-1],
                parent_ctrl=joint_ctrls[-2]
            )
        else:
            om.MGlobal.displayWarning(
                "Could not match end locator rotation for {}. "
                "Expected at least 2 locators and 2 ctrls. "
                "Got {} locators and {} ctrls.".format(
                    self.name,
                    len(locators),
                    len(loc_ctrls)
                )
            )
        
        if fingers:
            finger_output = self.create_finger_locators(
                pos=pos,
                finger_count=finger_count,
                thumb=thumb,
                finger_segments=finger_segments
            )
    
    # ---------------------------------------------------------
    # Finger locator creation
    # ---------------------------------------------------------
    
    def create_finger_locators(self, pos, finger_count=1, thumb=False, finger_segments=3):
        finger_count = int(finger_count)

        if finger_count < 0:
            finger_count = 0
        elif finger_count > 4:
            finger_count = 4

        fingers_to_build = self.get_finger_order()[:finger_count]

        if thumb:
            fingers_to_build.append("thumb")

        self.finger_locs = {}
        
        if self.prefix:
            hand_up_ref_grp_name = "{}_{}_hand_up_refGrp".format(self.prefix, self.name)
        else:
            hand_up_ref_grp_name = "{}_hand_up_refGrp".format(self.name)

        if cmds.objExists(hand_up_ref_grp_name):
            cmds.delete(hand_up_ref_grp_name)

        self.hand_up_ref_grp = cmds.group(
            empty=True,
            name=hand_up_ref_grp_name
        )

        if len(fingers_to_build) > 1:
            if self.prefix:
                finger_main_grp_name = "{}_{}_finger_locRigGrp".format(self.prefix, self.name)
            else:
                finger_main_grp_name = "{}_finger_locRigGrp".format(self.name)

            if cmds.objExists(finger_main_grp_name):
                om.MGlobal.displayWarning(
                    "{} found in scene already.".format(finger_main_grp_name)
                )
                return

            self.finger_main_grp = cmds.group(empty=True, name=finger_main_grp_name)
        
        finger_loc_grp = {}
        finger_ctrl_grp = {}
        finger_offset_grp = {}
        
        for finger in fingers_to_build:
            finger_builder = self.build_fingers(finger, segments=finger_segments)

            if not finger_builder:
                continue

            finger_joints = self.build_finger_joint_names_for_position_lookup(
                finger,
                finger_builder.joints
            )

            finger_positions = [
                self.get_pose_translation(pos, jnt)
                for jnt in finger_joints
            ]
                        
            locs = finger_builder.create_locators()

            if not locs:
                om.MGlobal.displayWarning(
                    "Failed to create locators for finger: {}".format(finger)
                )
                continue

            self.finger_locs[finger] = {
                "builder": finger_builder,
                "locs": locs
            }
            

            finger_ctrls = locs.get("loc_ctrls", [])
            finger_locs = locs.get("locators", [])
            finger_offsets = locs.get("loc_ctrl_offsets", [])
            
            finger_loc_grp[finger] = finger_locs
            finger_ctrl_grp[finger] = finger_ctrls
            finger_offset_grp[finger] = finger_offsets

            if len(finger_ctrls) != len(finger_positions):
                om.MGlobal.displayWarning(
                    "Finger ctrl count does not match position count for: {}".format(finger)
                )
                continue

            for ctrl, position in zip(finger_ctrls, finger_positions):
                if cmds.objExists(ctrl):
                    cmds.xform(ctrl, worldSpace=True, translation=position)
                else:
                    om.MGlobal.displayWarning(
                        "Finger control does not exist: {}".format(ctrl)
                    )
            
            for offset, ctrl, locator in zip(
                finger_offsets,
                finger_ctrls,
                finger_locs
            ):
                cmds.parent(ctrl, world=True)

                cmds.matchTransform(
                    offset,
                    locator,
                    position=True,
                    rotation=True
                )

                cmds.parent(ctrl, offset)

            finger_up_ref_data = self.create_finger_up_reference(
                finger,
                finger_builder,
                finger_positions,
                pos
            )

            for ctrl in finger_ctrls:
                GiancarloHelpers.lock_and_hide_attrs(
                    node=ctrl,
                    attrs=["rx", "ry", "rz"]
                )

            if finger_up_ref_data:
                self.finger_locs[finger]["up_ref"] = finger_up_ref_data.get("up_ref")
                self.finger_locs[finger]["up_ref_grp"] = finger_up_ref_data.get("up_ref_grp")

                up_ref_grp = finger_up_ref_data.get("up_ref_grp")

                # if (
                #     up_ref_grp
                #     and self.hand_up_ref_grp
                #     and cmds.objExists(up_ref_grp)
                #     and cmds.objExists(self.hand_up_ref_grp)
                # ):
                #     cmds.parent(up_ref_grp, self.hand_up_ref_grp)
            
            if len(finger_locs) >= 2 and len(finger_ctrls) >= 2:
                finger_builder.match_end_locator_to_parent_rotation(
                end_loc=finger_locs[-1],
                end_ctrl=finger_offsets[-1],
                parent_ctrl=finger_ctrls[-2]
            )
            else:
                om.MGlobal.displayWarning(
                    "Could not match end locator rotation for {}. Not enough locators/ctrls.".format(finger)
                )
               
                            
            self.create_wrist_to_finger_branch(finger, locs)

            finger_loc_main_grp = locs.get("loc_main_grp")
                        
            if self.finger_main_grp and finger_loc_main_grp and cmds.objExists(finger_loc_main_grp):
                cmds.parent(finger_loc_main_grp, self.finger_main_grp)

        arm_ctrls = self.locs.get("loc_ctrls", [])

        if not arm_ctrls:
            om.MGlobal.displayWarning(
                "Could not find arm locator controls."
            )
            return
        wrist_ctrl = arm_ctrls[-1]
        
        if not wrist_ctrl or not cmds.objExists(wrist_ctrl):
            om.MGlobal.displayWarning(
                "Wrist locator ctrl does not exist: {}".format(wrist_ctrl)
            )
            return
                        
        if (
            self.hand_up_ref_grp
            and wrist_ctrl
            and cmds.objExists(self.hand_up_ref_grp)
            and cmds.objExists(wrist_ctrl)
        ):
            cmds.parent(self.hand_up_ref_grp, wrist_ctrl)
        
        if self.finger_main_grp and cmds.objExists(self.finger_main_grp):
            cmds.parent(self.finger_main_grp, wrist_ctrl)

        else:
            for finger_data in self.finger_locs.values():
                locs = finger_data.get("locs", {})
                finger_loc_main_grp = locs.get("loc_main_grp")

                if finger_loc_main_grp and cmds.objExists(finger_loc_main_grp):
                    cmds.parent(finger_loc_main_grp, wrist_ctrl)
        
        cmds.select(clear=True)
        
        return {
            "finger_locs": finger_loc_grp, 
            "finger_ctrls": finger_ctrl_grp, 
            "finger_offsets": finger_offset_grp,
            "finger_names": fingers_to_build
            }
    
    def create_wrist_to_finger_branch(self, finger, finger_locs):
        arm_locators = self.locs.get("locators", [])
        finger_locators = finger_locs.get("locators", [])

        if not self.joints:
            om.MGlobal.displayWarning("Cannot create finger branch because no arm joints were found.")
            return

        wrist_index = len(self.joints) - 1

        if wrist_index >= len(arm_locators):
            om.MGlobal.displayWarning("Could not find wrist locator.")
            return

        if not finger_locators:
            om.MGlobal.displayWarning("Could not find first locator for finger: {}".format(finger))
            return

        wrist_locator = arm_locators[wrist_index]
        finger_start_locator = finger_locators[0]

        branch_name = "{}_{}_wristBranch".format(self.name, finger)

        if self.prefix:
            branch_name = "{}_{}".format(self.prefix, branch_name)

        branch_data = self.builder.create_cylinder(
            name=branch_name,
            organize=True,
            assign_shader=True
        )

        branch_main_grp = branch_data.get("main_grp")
        front_cluster_handle = branch_data.get("front_cluster_handle")
        end_cluster_handle = branch_data.get("end_cluster_handle")

        if not front_cluster_handle or not end_cluster_handle:
            om.MGlobal.displayWarning("Failed to create branch clusters for: {}".format(finger))
            return

        # front = finger
        # end = wrist
        cmds.matchTransform(front_cluster_handle, finger_start_locator, position=True)
        cmds.matchTransform(end_cluster_handle, wrist_locator, position=True)

        cmds.parentConstraint(finger_start_locator, front_cluster_handle, maintainOffset=True)
        cmds.parentConstraint(wrist_locator, end_cluster_handle, maintainOffset=True)

        finger_branch_grp = finger_locs.get("branch_grp")

        if (
            branch_main_grp
            and finger_branch_grp
            and cmds.objExists(branch_main_grp)
            and cmds.objExists(finger_branch_grp)
        ):
            cmds.parent(branch_main_grp, finger_branch_grp)
        else:
            om.MGlobal.displayWarning(
                "Could not parent wrist branch under finger branch group for: {}".format(finger)
            )
    
    # ---------------------------------------------------------
    # Finger up-reference and coplanar orientation
    # ---------------------------------------------------------
    
    def create_finger_up_reference(self, finger, finger_builder, finger_positions, pose_data):
        if self.prefix:
            up_ref_name = "{}_{}_{}_up_ref".format(self.prefix, self.name, finger)
            up_ref_grp_name = "{}_{}_{}_up_ref_offsetGrp".format(self.prefix, self.name, finger)
        else:
            up_ref_name = "{}_{}_up_ref".format(self.name, finger)
            up_ref_grp_name = "{}_{}_up_ref_offsetGrp".format(self.name, finger)

        for obj in [up_ref_name, up_ref_grp_name]:
            if cmds.objExists(obj):
                cmds.delete(obj)

        finger_ctrls = getattr(finger_builder, "loc_ctrls", []) or []
        finger_locs = getattr(
            finger_builder,
            "locators",
            []
        ) or []

        # segment 1 -> root ctrl
        # segment 2 -> second ctrl
        # segment 3 -> third ctrl
        
        driver_index = self.get_finger_up_driver_index(finger_builder)
        

        if len(finger_ctrls) <= driver_index:
            om.MGlobal.displayWarning(
                "Could not find up-ref driver ctrl for {}.".format(finger)
            )
            return None

        driver_ctrl = finger_ctrls[driver_index]
        child_index = driver_index + 1

        if len(finger_locs) <= child_index:
            om.MGlobal.displayWarning(
                "Could not find driver/child locators for: {}".format(
                    finger
                )
            )
            return None

        driver_loc = finger_locs[driver_index]
        child_loc = finger_locs[child_index]

        child_ctrl = finger_ctrls[child_index]

        saved_helper_position = self.get_saved_finger_up_ref_pos(
            pose_data,
            finger
        )
        
        if saved_helper_position is None:
            raise RuntimeError(
                "No saved helper position found for: {}".format(
                    finger
                )
            )

        coplanar_result = self.make_finger_driver_coplanar(
            finger_builder=finger_builder,
            driver_ctrl=driver_ctrl,
            driver_loc=driver_loc,
            child_ctrl=child_ctrl,
            child_loc=child_loc,
            saved_helper_position=saved_helper_position
        )

        if not coplanar_result:
            cmds.error(
                "Coplanar solver returned False for: {}".format(
                    finger
                )
            )

        ctrl_aim = coplanar_result.get("ctrl_aim")
        loc_aim = coplanar_result.get("loc_aim")

        GiancarloHelpers.add_attr(
            node=driver_ctrl,
            long_name="customRotation",
            attr_type="double",
            default_value=0,
            keyable=True
        )

        offset_attr = "offset{}".format(
            self.orientation.upper()
        )
        
        source_attr = "{}.customRotation".format(driver_ctrl)
        
        if self.position_preset in ["A-Pose", "T-Pose"]:
            saved_custom_rotation = 0.0
        else:
            saved_custom_rotation = pose_data.get(
                "{}_rotation".format(finger),
                0.0
            )
                   
        for aim_constraint in [ctrl_aim, loc_aim]:
            cmds.connectAttr(
                source_attr,
                "{}.{}".format(
                    aim_constraint,
                    offset_attr
                    ),
                force=True
            )
        
        cmds.delete(ctrl_aim)

        up_distance = self.builder.get_helper_distance(
            parent_pos=finger_positions[0],
            child_pos=finger_positions[-1]
        )

        up_ref_grp = cmds.group(empty=True, name=up_ref_grp_name)

        cmds.matchTransform(
            up_ref_grp,
            driver_ctrl,
            position=True,
            rotation=False
        )

        up_ref = cmds.polySphere(
            name=up_ref_name,
            radius=self.loc_size * 0.5,
            constructionHistory=False
        )[0]

        cmds.parent(up_ref, up_ref_grp)

        settings = finger_builder.get_joint_orientation_settings()

        if finger == "thumb":
            up_axis = settings["cross_product"]
        else:
            up_axis = settings["secondary_axis"]

        local_translate = self.axis_to_local_translate(
            up_axis,
            up_distance
        )

        cmds.setAttr(
            "{}.translate".format(up_ref),
            local_translate[0],
            local_translate[1],
            local_translate[2]
        )
        
        driver_position = cmds.xform(
            driver_ctrl,
            query=True,
            worldSpace=True,
            translation=True
        )
        
        cmds.xform(
            up_ref,
            worldSpace=True,
            rotatePivot=driver_position,
        )
        
        primary_axis = settings["primary_axis"]
        
        helper_rotate_attr = "{}.rotate{}".format(
            up_ref,
            primary_axis[-1].upper()
        )
        
        cmds.connectAttr(
            source_attr,
            helper_rotate_attr,
            force=True
        )
        
        up_ref_shape = GiancarloHelpers.get_shape_from_transform(up_ref)

        shader_name = "{}_{}_rootColor_lambert".format(
            self.prefix,
            self.name
        ) if self.prefix else "{}_rootColor_lambert".format(self.name)

        GiancarloHelpers.create_and_assign_lambert_shader_from_color_index(
            name=shader_name,
            shape_node=up_ref_shape,
            color_index=self.root_color
        )
        
        cmds.delete(cmds.parentConstraint(
            driver_ctrl,
            up_ref_grp,
            maintainOffset=False
        ))
        
        cmds.setAttr(
            source_attr,
            saved_custom_rotation
        )
        
        cmds.parent(up_ref_grp, driver_ctrl)
                
        return {
            "up_ref": up_ref,
            "up_ref_grp": up_ref_grp
        }
    
    def make_finger_driver_coplanar(
        self,
        finger_builder,
        driver_ctrl,
        driver_loc,
        child_ctrl,
        child_loc,
        saved_helper_position
    ):
        required_nodes = {
            "driver_ctrl": driver_ctrl,
            "driver_loc": driver_loc,
            "child_ctrl": child_ctrl,
            "child_loc": child_loc
        }

        for label, node in required_nodes.items():
            if not node or not cmds.objExists(node):
                om.MGlobal.displayWarning(
                    "{} does not exist: {}".format(
                        label,
                        node
                    )
                )
                return False

        if saved_helper_position is None:
            om.MGlobal.displayWarning(
                "Saved helper position was not provided."
            )
            return False

        # The constraint must be allowed to write rotation.
        for node in [driver_ctrl, driver_loc]:
            for axis in "XYZ":
                cmds.setAttr(
                    "{}.rotate{}".format(node, axis),
                    lock=False
                )

        driver_position = cmds.xform(
            driver_ctrl,
            query=True,
            worldSpace=True,
            translation=True
        )

        child_position = cmds.xform(
            child_ctrl,
            query=True,
            worldSpace=True,
            translation=True
        )

        aim = om.MVector(
            child_position[0] - driver_position[0],
            child_position[1] - driver_position[1],
            child_position[2] - driver_position[2]
        )

        saved_direction = om.MVector(
            saved_helper_position[0] - driver_position[0],
            saved_helper_position[1] - driver_position[1],
            saved_helper_position[2] - driver_position[2]
        )

        aim.normalize()

        saved_direction = saved_direction - (
            aim * (saved_direction * aim)
        )

        if saved_direction.length() < 1e-8:
            om.MGlobal.displayWarning(
                "Saved helper direction is parallel to the finger aim: {}".format(
                    driver_ctrl
                )
            )
            return False

        saved_direction.normalize()


        if finger_builder.use_cross_as_secondary:
            # The helper defines the other in-plane direction.
            # Build the cross-product secondary axis from aim and helper.
            coplanar_up_vector = saved_direction ^ aim

            if coplanar_up_vector.length() < 1e-8:
                om.MGlobal.displayWarning(
                    "Could not calculate thumb cross-product axis: {}".format(
                        driver_ctrl
                    )
                )
                return False

            coplanar_up_vector.normalize()

        else:
            # Standard fingers use the saved helper direction directly.
            coplanar_up_vector = saved_direction


        coplanar_up = [
            coplanar_up_vector.x,
            coplanar_up_vector.y,
            coplanar_up_vector.z
        ]

        constraint_settings = (
            finger_builder.get_orientation_settings()
        )

        aim_constraint_vector = (
            constraint_settings["aimVector"]
        )

        local_up_vector = (
            constraint_settings["upVector"]
        )
        
        ctrl_aim = cmds.aimConstraint(
            child_ctrl,
            driver_ctrl,
            maintainOffset=False,
            aimVector=aim_constraint_vector,
            upVector=local_up_vector,
            worldUpType="vector",
            worldUpVector=coplanar_up
        )[0]

        loc_aim = cmds.aimConstraint(
            child_loc,
            driver_loc,
            maintainOffset=False,
            aimVector=aim_constraint_vector,
            upVector=local_up_vector,
            worldUpType="vector",
            worldUpVector=coplanar_up
        )[0]

        cmds.dgdirty(
            driver_ctrl,
            driver_loc
        )

        cmds.refresh(
            force=True
        )

        return {
            "ctrl_aim": ctrl_aim,
            "loc_aim": loc_aim
        }
    
    def get_finger_up_driver_index(self, finger_builder):
        joint_count = len(finger_builder.joints)

        if joint_count == 2:
            return 0
        elif joint_count == 3:
            return 1

        return 2
    
    def axis_to_local_translate(self, axis_name, distance):
        sign = -1.0 if axis_name.startswith("-") else 1.0
        axis = axis_name[-1]

        value = distance * sign
        translate = [0, 0, 0]

        if axis == "x":
            translate[0] = value
        elif axis == "y":
            translate[1] = value
        else:
            translate[2] = value

        return translate
    
    # ---------------------------------------------------------
    # Finger joint construction
    # ---------------------------------------------------------
    
    def create_finger_joints(self, wrist_joint):
        finger_joint_results = {}

        if not self.finger_locs:
            return finger_joint_results

        if not wrist_joint or not cmds.objExists(wrist_joint):
            om.MGlobal.displayWarning(
                "Cannot parent finger joints because wrist joint was not found."
            )
            return finger_joint_results

        for finger, finger_data in self.finger_locs.items():
            finger_builder = finger_data.get("builder")

            if not finger_builder:
                om.MGlobal.displayWarning(
                    "{} finger builder was not found.".format(finger)
                )
                continue
            
            finger_builder.display_LRA = self.display_LRA
            finger_builder.joint_size = self.builder.joint_size
            finger_builder.end_orient = "parent"
            finger_builder.create_display_layer = False
            finger_builder.display_layer = self.builder.jnt_display_layer
            # finger_builder.display_layer = getattr(self.builder, "jnt_display_layer", None)
            
            up_ref = finger_data.get("up_ref")
            
            finger_result = self.build_finger_joints_with_up_ref(
                finger,
                finger_builder,
                up_ref
            )
            
            if not finger_result:
                om.MGlobal.displayWarning(
                    "Failed to construct joints for finger: {}".format(finger)
                )
                continue

            finger_joints = finger_result.get("joints", [])
            
            finger_main_grp = finger_result.get("main_grp")
            finger_joint_grp = finger_result.get("joint_grp")
            
            self.apply_display_lra_to_joints(
                finger_joints,
                finger_builder.display_LRA
            )
            self.apply_joint_size_to_joints(
                finger_joints,
                finger_builder.joint_size
            )
                        
            if not finger_joints:
                om.MGlobal.displayWarning(
                    "No finger joints were created for: {}".format(finger)
                )
                continue

            finger_root_joint = finger_joints[0]

            if cmds.objExists(finger_root_joint):
                current_parent = cmds.listRelatives(
                    finger_root_joint,
                    parent=True,
                    fullPath=True
                ) or []

                wrist_joint_long = cmds.ls(wrist_joint, long=True)[0]

                if not current_parent or current_parent[0] != wrist_joint_long:
                    cmds.parent(finger_root_joint, wrist_joint_long)
            else:
                om.MGlobal.displayWarning(
                    "Finger root joint does not exist: {}".format(finger_root_joint)
                )
                continue
            
            # Remove unnecessary finger grouping hierarchy.
            if finger_joint_grp and cmds.objExists(finger_joint_grp):
                joint_grp_children = cmds.listRelatives(
                    finger_joint_grp,
                    children=True,
                    fullPath=True
                ) or []

                if joint_grp_children:
                    cmds.parent(joint_grp_children, world=True)

                cmds.delete(finger_joint_grp)

            if finger_main_grp and cmds.objExists(finger_main_grp):
                cmds.delete(finger_main_grp)

            finger_joint_results[finger] = finger_result

        return finger_joint_results
    
    def build_finger_joints_with_up_ref(self, finger, finger_builder, up_ref):
        locators = finger_builder.locators
        
        if not locators or len(locators) < 2:
            om.MGlobal.displayWarning("Need at least 2 finger locators for: {}".format(finger))
            return None
        
        if not up_ref or not cmds.objExists(up_ref):
            om.MGlobal.displayWarning("Missing up reference for finger: {}".format(finger))
            return None
        
        settings = finger_builder.get_joint_orientation_settings()
        
        primary_axis = settings["primary_axis"]
        
        secondary_axis = settings["secondary_axis"]
            
        positions = [
            cmds.xform(loc, query=True, worldSpace=True, translation=True)
            for loc in locators
        ]
        
        joints = []

        up_ref_matrix = cmds.xform(
            up_ref,
            query=True,
            worldSpace=True,
            matrix=True
        )

        up_ref_pos = om.MVector(
            up_ref_matrix[12],
            up_ref_matrix[13],
            up_ref_matrix[14]
        )

        driver_index = self.get_finger_up_driver_index(finger_builder)

        driver_loc = locators[driver_index]

        driver_pos = om.MVector(
            *cmds.xform(driver_loc, query=True, worldSpace=True, translation=True)
        )

        up_direction = up_ref_pos - driver_pos
        
        if up_direction.length() < 1e-8:
            up_direction = om.MVector(0, 1, 0)

        up_direction.normalize()
                
        for i, pos in enumerate(positions):
            joint_name = "{}_{}_{}".format(
                finger_builder.name,
                finger_builder.joints[i],
                finger_builder.suffix
            )
            
            if finger_builder.prefix:
                joint_name = "{}_{}".format(finger_builder.prefix, joint_name)
            
            jnt = cmds.joint(name=joint_name, position=pos)
            joints.append(jnt)
            
            cmds.select(clear=True)
        
        chain_up_pos = None

        for i in range(len(joints) - 1):
            parent_joint = joints[i]
            child_joint = joints[i + 1]

            parent_pos = om.MVector(*positions[i])
            child_pos = om.MVector(*positions[i + 1])

            if self.finger_orientation_mode == "per_joint":
                current_up_pos = parent_pos + up_direction
            else:
                if i == 0 or chain_up_pos is None:
                    current_up_pos = parent_pos + up_direction
                else:
                    current_up_pos = chain_up_pos

            self.apply_matrix_orientation_to_joint(
                joint=parent_joint,
                position=parent_pos,
                child_position=child_pos,
                up_position=current_up_pos,
                primary_axis=primary_axis,
                secondary_axis=secondary_axis
            )

            rot_matrix = cmds.xform(
                parent_joint,
                query=True,
                worldSpace=True,
                matrix=True
            )

            if secondary_axis.endswith("x"):
                axis_vec = om.MVector(rot_matrix[0], rot_matrix[1], rot_matrix[2])
            elif secondary_axis.endswith("y"):
                axis_vec = om.MVector(rot_matrix[4], rot_matrix[5], rot_matrix[6])
            else:
                axis_vec = om.MVector(rot_matrix[8], rot_matrix[9], rot_matrix[10])

            if secondary_axis.startswith("-"):
                axis_vec *= -1.0

            axis_vec.normalize()

            chain_up_pos = child_pos + axis_vec
            
        # End joint matches parent while still unparented.
        if len(joints) >= 2:
            parent_rot = cmds.xform(
                joints[-2],
                query=True,
                worldSpace=True,
                rotation=True
            )

            cmds.xform(
                joints[-1],
                worldSpace=True,
                rotation=parent_rot
            )
            
        # Parent joints after world orientations are solved.
        for jnt in joints:
            cmds.makeIdentity(
                jnt,
                apply=True,
                translate=False,
                rotate=True,
                scale=False,
                normal=False
            )
            
        for i in range(1, len(joints)):
            cmds.parent(joints[i], joints[i - 1])
        
        return {
            "joints": joints,
            "main_grp": None,
            "joint_grp": None
        }
    
    def apply_matrix_orientation_to_joint(
        self,
        joint,
        position,
        child_position,
        up_position,
        primary_axis="x",
        secondary_axis="y"
    ):
        aim_vec = child_position - position
        
        if aim_vec.length() < 1e-8:
            om.MGlobal.displayWarning("Joint and child are too close: {}".format(joint))
            return
        
        aim_vec.normalize()
        
        up_vec = up_position - position
        
        if up_vec.length() < 1e-8:
            up_vec = om.MVector(0, 1, 0)
        
        up_vec.normalize()
        
        # Remove any part of up_vec that points down the aim_axis.
        up_vec = up_vec - (aim_vec * (up_vec * aim_vec))
        
        up_vec.normalize()
        
        if up_vec.length() < 1e-8:
            up_vec = om.MVector(0, 1, 0)
            
            if abs(aim_vec * up_vec) > 0.98:
                up_vec = om.MVector(0, 0, 1)
            
            up_vec = up_vec - (aim_vec * (up_vec * aim_vec))
        
        axes = {}

        primary_sign = -1.0 if primary_axis.startswith("-") else 1.0
        primary_axis_clean = primary_axis[-1]

        secondary_sign = -1.0 if secondary_axis.startswith("-") else 1.0
        secondary_axis_clean = secondary_axis[-1]

        aim_axis = aim_vec * primary_sign
        up_axis = up_vec * secondary_sign

        aim_axis.normalize()
        up_axis.normalize()

        axes[primary_axis_clean] = aim_axis
        axes[secondary_axis_clean] = up_axis

        missing_axis = list(set(["x", "y", "z"]) - set(axes.keys()))[0]

        # Build the missing axis using stable right-handed rules.
        if primary_axis_clean == "x" and secondary_axis_clean == "y":
            axes[missing_axis] = axes["x"] ^ axes["y"]

        elif primary_axis_clean == "x" and secondary_axis_clean == "z":
            axes[missing_axis] = axes["z"] ^ axes["x"]

        elif primary_axis_clean == "y" and secondary_axis_clean == "x":
            axes[missing_axis] = axes["y"] ^ axes["x"]

        elif primary_axis_clean == "y" and secondary_axis_clean == "z":
            axes[missing_axis] = axes["y"] ^ axes["z"]

        elif primary_axis_clean == "z" and secondary_axis_clean == "x":
            axes[missing_axis] = axes["z"] ^ axes["x"]

        elif primary_axis_clean == "z" and secondary_axis_clean == "y":
            axes[missing_axis] = axes["y"] ^ axes["z"]

        axes[missing_axis].normalize()

        # Rebuild secondary to make it perfectly perpendicular.
        if secondary_axis_clean == "x":
            if primary_axis_clean == "y":
                axes["x"] = axes["z"] ^ axes["y"]
            else:
                axes["x"] = axes["y"] ^ axes["z"]

        elif secondary_axis_clean == "y":
            if primary_axis_clean == "x":
                axes["y"] = axes["z"] ^ axes["x"]
            else:
                axes["y"] = axes["z"] ^ axes["x"]

        elif secondary_axis_clean == "z":
            if primary_axis_clean == "x":
                axes["z"] = axes["x"] ^ axes["y"]
            else:
                axes["z"] = axes["x"] ^ axes["y"]

        axes["x"].normalize()
        axes["y"].normalize()
        axes["z"].normalize()
        
        x_axis = axes["x"]
        y_axis = axes["y"]
        z_axis = axes["z"]
        
        matrix = [
            x_axis.x, x_axis.y, x_axis.z, 0,
            y_axis.x, y_axis.y, y_axis.z, 0,
            z_axis.x, z_axis.y, z_axis.z, 0,
            position.x, position.y, position.z, 1
        ]
                
        cmds.xform(
            joint,
            worldSpace=True,
            matrix=matrix
        )
        cmds.setAttr("{}.scale".format(joint), 1, 1, 1)
    
    # ---------------------------------------------------------
    # Joint display utilities
    # ---------------------------------------------------------
    
    def apply_display_lra_to_joints(self, joints, state):
        for jnt in joints:
            if cmds.objExists(jnt) and cmds.attributeQuery("displayLocalAxis", node=jnt, exists=True):
                cmds.setAttr("{}.displayLocalAxis".format(jnt), state)
    
    def apply_joint_size_to_joints(self, joints, size):
        for jnt in joints:
            if cmds.objExists(jnt) and cmds.attributeQuery("radius", node=jnt, exists=True):
                cmds.setAttr("{}.radius".format(jnt), size)
                                
    @classmethod
    def from_settings(cls, settings):
        return cls(
            loc_type=settings["loc_type"],
            fingers=settings["fingers"],
            finger_count=settings["finger_count"],
            thumb=settings["thumb"],
            finger_segments=settings["finger_segments"],
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
            distance_between=settings["distance_between"],
            end_orient=settings["end_orient"],
            create_coplanar_mesh=settings["create_coplanar_mesh"],
            position_preset=settings.get("position_preset", "A-Pose"),
            finger_orientation_mode=settings.get(
                "finger_orientation_mode",
                "propagated"
            )
        )
        
if __name__ == "__main__":

    arm = ArmModule(
        loc_type="Left_Biped_Arm",
        fingers=True,
        finger_count=4,
        thumb=True,
        finger_segments=1,
        name="arm_01",
        prefix="L",
        suffix="jnt",
        ctrl_type="sphere",
        ctrl_size=.6,
        ctrl_color=13,
        root_type="diamond",
        root_size=2,
        root_color=17,
        global_type="four_way_arrow",
        global_size=3,
        global_color=14,
        joints=[],
        orientation="z",
        display_LRA=True,
        loc_size=2,
        distance_between=3,
        end_orient="parent",
        create_coplanar_mesh=True,
        finger_orientation_mode="propagated",
    )
    
    arm.create_locators()

    # built = arm.create_joints(delete_locators_after=True)
    
    # if finger_builder:
    #     print(finger_builder.joints)
    
    # if built:
    #     print(built["joints"])