import maya.cmds as cmds
import maya.OpenMaya as om

from custom_locator import CustomLocator
from GiancarloHelpers import GiancarloHelpers

class JointChainBuilder(object):
    
    def __init__(self, name, joints, side=None, orientation="x", size=1):
        self.name = name
        self.side = side
        self.orientation = orientation
        self.size = size
        
        self.locators = []
        self.branches = []
        
        if len(set(joints)) != len(joints):
            om.MGlobal.displayWarning("Duplicate names found.")
            return
        else:
            self.joints = joints                    
        
    def create_locators(self):
        joints = self.joints
        side = self.side
        orientation = self.orientation
        size = self.size
        
        existing_objects = cmds.ls(type="transform")
        
        for joint in joints:            
            if side:
                locator_name = f"{side}_{joint}_loc"
            else:
                locator_name = f"{joint}_loc"
            
            if locator_name in existing_objects:
                om.MGlobal.displayWarning(f"{locator_name} found in scene already.")
                return
        
        
        positions = [(0, 0, 0), (2, 0, -1), (5, 0, -3), (9, 0, -1)]
        self.cluster_grp = cmds.group(name=f"{self.name}_cluster_grp", empty=True)
        self.branch_grp = cmds.group(name=f"{self.name}_branch_grp", empty=True)
        
        
        if len(joints) == 3 or len(joints) == 4:
            for i, name in enumerate(joints):
                if len(joints) == 3:
                    position_index = i + 1
                else:
                    position_index = i
                
                position = positions[position_index]
                
                loc = CustomLocator(name=name, side=side, orientation=orientation)
                loc = loc.get_locator_name()
                
                cmds.xform(loc, worldSpace=True, translation=position)
                cmds.setAttr(f"{loc}.scale", size, size, size, type="double3")
                cmds.makeIdentity(loc, apply=True, scale=True)
                
                self.locators.append(loc)
                
            if len(joints) == 3:
                branch_01 = self.create_cylinder(name=f"{self.name}_branch_01")
                branch_02 = self.create_cylinder(name=f"{self.name}_branch_02")
                self.branches.append(branch_01[0])
                self.branches.append(branch_02[0])
                
                # match transforms & parent constraints
                cmds.matchTransform(branch_01[2], self.locators[1], position=True)
                cmds.matchTransform(branch_01[4], self.locators[0], position=True)
                cmds.matchTransform(branch_02[2], self.locators[2], position=True)
                cmds.matchTransform(branch_02[4], self.locators[1], position=True)
                
                cmds.parentConstraint(self.locators[1], branch_01[2], maintainOffset=True)
                cmds.parentConstraint(self.locators[0], branch_01[4], maintainOffset=True)
                cmds.parentConstraint(self.locators[2], branch_02[2], maintainOffset=True)
                cmds.parentConstraint(self.locators[1], branch_02[4], maintainOffset=True)
                
                cmds.parent(branch_01[2], branch_01[4], branch_02[2], branch_02[4], self.cluster_grp)
                cmds.setAttr(f"{self.cluster_grp}.visibility", False)
                GiancarloHelpers.lock_and_hide_attrs(self.cluster_grp, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"], lock=True, hide=True, channelBox=False)
                cmds.parent(self.branches, self.branch_grp)
                GiancarloHelpers.lock_and_hide_attrs(self.branch_grp, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"], lock=True, hide=True, channelBox=False)
                cmds.setAttr(f"{self.branch_grp}.overrideEnabled", True)
                cmds.setAttr(f"{self.branch_grp}.overrideDisplayType", 2)
                
                branch_shader = GiancarloHelpers.create_and_assign_lambert_shader(name="branch_lambert", shape_node=self.branches[0], hsv=(175.384, 0, 0.032))
                cmds.sets(self.branches[1], edit=True, forceElement=branch_shader + "SG")
                
                if self.orientation == "x":
                    loc_01_aim = cmds.aimConstraint(self.locators[1], self.locators[0], maintainOffset=False, aimVector=(1,0,0), upVector=(0,1,0), worldUpType="object", worldUpObject=self.locators[1])
                    loc_02_aim = cmds.aimConstraint(self.locators[2], self.locators[1], maintainOffset=False, aimVector=(1,0,0), upVector=(0,1,0), worldUpType="object", worldUpObject=self.locators[2])
                    loc_03 = cmds.spaceLocator(name="null")[0]
                    null_grp = cmds.group(empty=True, name="null_grp")
                    cmds.matchTransform(null_grp, self.locators[1], position=True, rotation=True)
                    cmds.parent(loc_03, null_grp)
                    cmds.setAttr(f"{loc_03}.translate", 6, 0, 0, type="double3")
                    cmds.setAttr(f"{loc_03}.rotate", 0, 0, 0, type="double3")
                    cmds.delete(cmds.aimConstraint(loc_03, self.locators[2], maintainOffset=False, aimVector=(1,0,0), upVector=(0,1,0), worldUpType="object", worldUpObject=loc_03))
                    cmds.delete(null_grp)
                    
                elif self.orientation == "y":
                    loc_01_aim = cmds.aimConstraint(self.locators[1], self.locators[0], maintainOffset=False, aimVector=(0,1,0), upVector=(-1,0,0), worldUpType="object", worldUpObject=self.locators[1])
                    loc_02_aim = cmds.aimConstraint(self.locators[2], self.locators[1], maintainOffset=False, aimVector=(0,1,0), upVector=(-1,0,0), worldUpType="object", worldUpObject=self.locators[2])
                    loc_03 = cmds.spaceLocator(name="null")[0]
                    null_grp = cmds.group(empty=True, name="null_grp")
                    cmds.matchTransform(null_grp, self.locators[1], position=True, rotation=True)
                    cmds.parent(loc_03, null_grp)
                    cmds.setAttr(f"{loc_03}.translate", 0, 6, 0, type="double3")
                    cmds.setAttr(f"{loc_03}.rotate", 0, 0, 0, type="double3")
                    cmds.delete(cmds.aimConstraint(loc_03, self.locators[2], maintainOffset=False, aimVector=(0,1,0), upVector=(-1,0,0), worldUpType="object", worldUpObject=loc_03))
                    cmds.delete(null_grp)
                    
                elif self.orientation == "z":
                    loc_01_aim = cmds.aimConstraint(self.locators[1], self.locators[0], maintainOffset=False, aimVector=(0,0,1), upVector=(1,0,0), worldUpType="object", worldUpObject=self.locators[1])
                    loc_02_aim = cmds.aimConstraint(self.locators[2], self.locators[1], maintainOffset=False, aimVector=(0,0,1), upVector=(1,0,0), worldUpType="object", worldUpObject=self.locators[2])
                    loc_03 = cmds.spaceLocator(name="null")[0]
                    null_grp = cmds.group(empty=True, name="null_grp")
                    cmds.matchTransform(null_grp, self.locators[1], position=True, rotation=True)
                    cmds.parent(loc_03, null_grp)
                    cmds.setAttr(f"{loc_03}.translate", 0, 0, 6, type="double3")
                    cmds.setAttr(f"{loc_03}.rotate", 0, 0, 0, type="double3")
                    cmds.delete(cmds.aimConstraint(loc_03, self.locators[2], maintainOffset=False, aimVector=(0,0,1), upVector=(1,0,0), worldUpType="object", worldUpObject=loc_03))
                    cmds.delete(null_grp)
                                    
            if len(joints) == 4:    
                branch_01 = self.create_cylinder(name=f"{self.name}_branch_01")
                branch_02 = self.create_cylinder(name=f"{self.name}_branch_02")
                branch_03 = self.create_cylinder(name=f"{self.name}_branch_03")
                self.branches.append(branch_01[0])
                self.branches.append(branch_02[0])
                self.branches.append(branch_03[0])
                
                # match transforms & parent constraints
                cmds.matchTransform(branch_01[2], self.locators[1], position=True)
                cmds.matchTransform(branch_01[4], self.locators[0], position=True)
                cmds.matchTransform(branch_02[2], self.locators[2], position=True)
                cmds.matchTransform(branch_02[4], self.locators[1], position=True)
                cmds.matchTransform(branch_03[2], self.locators[3], position=True)
                cmds.matchTransform(branch_03[4], self.locators[2], position=True)
                
                cmds.parentConstraint(self.locators[1], branch_01[2], maintainOffset=True)
                cmds.parentConstraint(self.locators[0], branch_01[4], maintainOffset=True)
                cmds.parentConstraint(self.locators[2], branch_02[2], maintainOffset=True)
                cmds.parentConstraint(self.locators[1], branch_02[4], maintainOffset=True)
                cmds.parentConstraint(self.locators[3], branch_03[2], maintainOffset=True)
                cmds.parentConstraint(self.locators[2], branch_03[4], maintainOffset=True)
                
                cmds.parent(branch_01[2], branch_01[4], branch_02[2], branch_02[4], branch_03[2], branch_03[4], self.cluster_grp)
                cmds.setAttr(f"{self.cluster_grp}.visibility", False)
                GiancarloHelpers.lock_and_hide_attrs(self.cluster_grp, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"], lock=True, hide=True, channelBox=False)
                cmds.parent(self.branches, self.branch_grp)
                GiancarloHelpers.lock_and_hide_attrs(self.branch_grp, ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"], lock=True, hide=True, channelBox=False)
                cmds.setAttr(f"{self.branch_grp}.overrideEnabled", True)
                cmds.setAttr(f"{self.branch_grp}.overrideDisplayType", 2)
                
                branch_shader = GiancarloHelpers.create_and_assign_lambert_shader(name="branch_lambert", shape_node=self.branches[0], hsv=(175.384, 0, 0.032))
                cmds.sets(self.branches[1], edit=True, forceElement=branch_shader + "SG")
                cmds.sets(self.branches[2], edit=True, forceElement=branch_shader + "SG")
                
                if self.orientation == "x":
                    loc_01_aim = cmds.aimConstraint(self.locators[1], self.locators[0], maintainOffset=False, aimVector=(1,0,0), upVector=(0,1,0), worldUpType="object", worldUpObject=self.locators[1])
                    loc_02_aim = cmds.aimConstraint(self.locators[2], self.locators[1], maintainOffset=False, aimVector=(1,0,0), upVector=(0,1,0), worldUpType="object", worldUpObject=self.locators[2])
                    loc_03_aim = cmds.aimConstraint(self.locators[3], self.locators[2], maintainOffset=False, aimVector=(1,0,0), upVector=(0,1,0), worldUpType="object", worldUpObject=self.locators[3])
                    loc_04 = cmds.spaceLocator(name="null")[0]
                    null_grp = cmds.group(empty=True, name="null_grp")
                    cmds.matchTransform(null_grp, self.locators[2], position=True, rotation=True)
                    cmds.parent(loc_04, null_grp)
                    cmds.setAttr(f"{loc_04}.translate", 6, 0, 0, type="double3")
                    cmds.setAttr(f"{loc_04}.rotate", 0, 0, 0, type="double3")
                    cmds.delete(cmds.aimConstraint(loc_04, self.locators[3], maintainOffset=False, aimVector=(1,0,0), upVector=(0,1,0), worldUpType="object", worldUpObject=loc_04))
                    cmds.delete(null_grp)
                    
                elif self.orientation == "y":
                    loc_01_aim = cmds.aimConstraint(self.locators[1], self.locators[0], maintainOffset=False, aimVector=(0,1,0), upVector=(-1,0,0), worldUpType="object", worldUpObject=self.locators[1])
                    loc_02_aim = cmds.aimConstraint(self.locators[2], self.locators[1], maintainOffset=False, aimVector=(0,1,0), upVector=(-1,0,0), worldUpType="object", worldUpObject=self.locators[2])
                    loc_03_aim = cmds.aimConstraint(self.locators[3], self.locators[2], maintainOffset=False, aimVector=(0,1,0), upVector=(-1,0,0), worldUpType="object", worldUpObject=self.locators[3])
                    loc_04 = cmds.spaceLocator(name="null")[0]
                    null_grp = cmds.group(empty=True, name="null_grp")
                    cmds.matchTransform(null_grp, self.locators[2], position=True, rotation=True)
                    cmds.parent(loc_04, null_grp)
                    cmds.setAttr(f"{loc_04}.translate", 0, 6, 0, type="double3")
                    cmds.setAttr(f"{loc_04}.rotate", 0, 0, 0, type="double3")
                    cmds.delete(cmds.aimConstraint(loc_04, self.locators[3], maintainOffset=False, aimVector=(0,1,0), upVector=(-1,0,0), worldUpType="object", worldUpObject=loc_04))
                    cmds.delete(null_grp)
                    
                elif self.orientation == "z":
                    loc_01_aim = cmds.aimConstraint(self.locators[1], self.locators[0], maintainOffset=False, aimVector=(0,0,1), upVector=(1,0,0), worldUpType="object", worldUpObject=self.locators[1])
                    loc_02_aim = cmds.aimConstraint(self.locators[2], self.locators[1], maintainOffset=False, aimVector=(0,0,1), upVector=(1,0,0), worldUpType="object", worldUpObject=self.locators[2])
                    loc_03_aim = cmds.aimConstraint(self.locators[3], self.locators[2], maintainOffset=False, aimVector=(0,0,1), upVector=(1,0,0), worldUpType="object", worldUpObject=self.locators[3])
                    loc_04 = cmds.spaceLocator(name="null")[0]
                    null_grp = cmds.group(empty=True, name="null_grp")
                    cmds.matchTransform(null_grp, self.locators[2], position=True, rotation=True)
                    cmds.parent(loc_04, null_grp)
                    cmds.setAttr(f"{loc_04}.translate", 0, 0, 6, type="double3")
                    cmds.setAttr(f"{loc_04}.rotate", 0, 0, 0, type="double3")
                    cmds.delete(cmds.aimConstraint(loc_04, self.locators[3], maintainOffset=False, aimVector=(0,0,1), upVector=(1,0,0), worldUpType="object", worldUpObject=loc_04))
                    cmds.delete(null_grp)
                   
        else:
            om.MGlobal.displayWarning("Expected 3 or 4 joint names but got {}".format(len(joints)))
            return
        
        return self.locators
    
    def create_cylinder(self, name):
        cylinder = cmds.polyCylinder(name=name, radius=self.size/5, constructionHistory=False)[0]
        
        cmds.setAttr(f"{cylinder}.rotateZ", 90)
        cmds.makeIdentity(cylinder, apply=True, rotate=True)
        
        front_cluster = cmds.cluster(f"{cylinder}.vtx[0:19]", name=name + "_frontCluster")
        front_cluster_handle = front_cluster[1]
        front_cluster = front_cluster[0]
        end_cluster = cmds.cluster(f"{cylinder}.vtx[20:39]", name=name + "_endCluster")
        end_cluster_handle = end_cluster[1]
        end_cluster = end_cluster[0]
        
        cmds.select(clear=True)
        
        return [cylinder, front_cluster, front_cluster_handle, end_cluster, end_cluster_handle]
    
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
        
    def create_joints(self, joint_positions):
        joint_list = []
        
        existing_objects = cmds.ls(type="transform")
        
        for joint in self.joints:            
            if self.side:
                joint_name = f"{self.side}_{joint}_jnt"
            else:
                joint_name = f"{joint}_jnt"
            
            if joint_name in existing_objects:
                om.MGlobal.displayWarning(f"{joint_name} found in scene already.")
                return
        
        if self.side:
            prefix = []
            for joint in self.joints:
                prefix.append(f"{self.side}_{joint}")
        else:
            prefix = self.joints
        
        if joint_positions:    
            if len(joint_positions) == 3:
                cmds.select(clear=True)
                
                for i, position in enumerate(joint_positions):
                    if i < len(prefix):
                        joint_name = f"{prefix[i]}_jnt"
                    else:
                        joint_name = f"joint_{i}_jnt"
                    
                    joint = cmds.joint(position=position, name=joint_name)
                    joint_list.append(joint)
                
                if self.orientation == "x":
                    cmds.joint(joint_list[0], edit=True, orientJoint="xyz", zeroScaleOrient=True, secondaryAxisOrient="yup")
                    cmds.joint(joint_list[1], edit=True, orientJoint="xyz", zeroScaleOrient=True, secondaryAxisOrient="yup")
                    cmds.joint(joint_list[2], edit=True, orientJoint="none", zeroScaleOrient=True, secondaryAxisOrient="yup")
                
                elif self.orientation == "y":
                    cmds.joint(joint_list[0], edit=True, orientJoint="yzx", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    cmds.joint(joint_list[1], edit=True, orientJoint="yzx", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    cmds.joint(joint_list[2], edit=True, orientJoint="none", zeroScaleOrient=True, secondaryAxisOrient="zup")
                
                else:
                    cmds.joint(joint_list[0], edit=True, orientJoint="zyx", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    cmds.joint(joint_list[1], edit=True, orientJoint="zyx", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    cmds.joint(joint_list[2], edit=True, orientJoint="none", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    
                
            
            elif len(joint_positions) == 4:
                cmds.select(clear=True)
                
                for i, position in enumerate(joint_positions):
                    if i < len(prefix):
                        joint_name = f"{prefix[i]}_jnt"
                    else:
                        joint_name = f"joint_{i}_jnt"
                    
                    joint = cmds.joint(position=position, name=joint_name)
                    joint_list.append(joint)
                
                if self.orientation == "x":
                    cmds.joint(joint_list[0], edit=True, orientJoint="xyz", zeroScaleOrient=True, secondaryAxisOrient="yup")
                    cmds.joint(joint_list[1], edit=True, orientJoint="xyz", zeroScaleOrient=True, secondaryAxisOrient="yup")
                    cmds.joint(joint_list[2], edit=True, orientJoint="xyz", zeroScaleOrient=True, secondaryAxisOrient="yup")
                    cmds.joint(joint_list[3], edit=True, orientJoint="none", zeroScaleOrient=True, secondaryAxisOrient="yup")
                
                elif self.orientation == "y":
                    cmds.joint(joint_list[0], edit=True, orientJoint="yzx", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    cmds.joint(joint_list[1], edit=True, orientJoint="yzx", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    cmds.joint(joint_list[2], edit=True, orientJoint="yzx", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    cmds.joint(joint_list[3], edit=True, orientJoint="none", zeroScaleOrient=True, secondaryAxisOrient="zup")
                
                else:
                    cmds.joint(joint_list[0], edit=True, orientJoint="zyx", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    cmds.joint(joint_list[1], edit=True, orientJoint="zyx", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    cmds.joint(joint_list[2], edit=True, orientJoint="zyx", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    cmds.joint(joint_list[3], edit=True, orientJoint="none", zeroScaleOrient=True, secondaryAxisOrient="zup")
                    
                
            else:
                raise RuntimeError("Expected 3 or 4 joint positions")
        else:
            return
    
    def delete_locators(self):
        if self.locators:
            cmds.delete(self.locators)
            cmds.delete(self.branches)
            cmds.delete(self.branch_grp)
        else:
            om.MGlobal.displayWarning("Cannot delete: No locators found")
    
    def construct_joints(self):
        joint_positions = self.locator_positions()
        self.create_joints(joint_positions)
        
        cmds.select(clear=True)


if __name__ == "__main__":
    
    # cmds.file(f=True, new=True)
    
    name = "arm_jnt_01"
    joints = ["clavicle", "shoulder", "elbow", "hand"]
    arm_jnt_01 = JointChainBuilder(name=name, joints=joints, side="L", orientation="x", size=0.5)
    arm_jnt_01.create_locators()
    arm_jnt_01.construct_joints()
    arm_jnt_01.delete_locators()
    
    name = "leg_jnt_01"
    joints = ["femur", "tibia", "ankle"]
    leg_jnt_01 = JointChainBuilder(name=name, joints=joints, side=None, orientation="y", size=0.8)
    leg_jnt_01.create_locators()
    leg_jnt_01.construct_joints()
    leg_jnt_01.delete_locators()
    
