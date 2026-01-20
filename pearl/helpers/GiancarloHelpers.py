import maya.cmds as cmds
import maya.mel as mel

import colorsys

class GiancarloHelpers(object):
    
    @classmethod
    def add_attr(cls, node, long_name, attr_type, default_value=0, keyable=False):
        cmds.addAttr(node, longName=long_name, attributeType=attr_type, defaultValue=default_value, keyable=keyable)
    
    @classmethod
    def set_attr(cls, node, attr, value, value_type=None):
        if value_type:
            # expect a list that will be unpacked for the command
            cmds.setAttr("{0}.{1}".format(node, attr), *value, type=value_type) # The "*" unpacks the list
        else:
            cmds.setAttr("{0}.{1}".format(node, attr), value)
    
    @classmethod
    def connect_attr(cls, node_a, attr_a, node_b, attr_b, force=False):
        cmds.connectAttr("{0}.{1}".format(node_a, attr_a), "{0}.{1}".format(node_b, attr_b), force=force)
    
    @classmethod
    def lock_and_hide_attrs(cls, node, attrs, lock=True, hide=True, channelBox=False):
        keyable = not hide
        
        for attr in attrs:
            full_name = "{0}.{1}".format(node, attr)
            cmds.setAttr(full_name, lock=lock, keyable=keyable, channelBox=channelBox)
            
    @classmethod
    def make_unselectable(cls, transform_node):
        shape_node = cls.get_shape_from_transform(transform_node)
        
        cls.set_attr(shape_node, "overrideEnabled", True)
        cls.set_attr(shape_node, "overrideDisplayType", 2)
    
    @classmethod
    def create_display_layer(cls, name, members, reference=False):
        display_layer = cmds.createDisplayLayer(name=name, empty=True)
        
        if reference:
            cmds.setAttr("{0}.displayType".format(display_layer), 2)
        
        if members:
            cmds.editDisplayLayerMembers(display_layer, members, noRecurse=True)
        
        return display_layer

    @classmethod
    def create_and_assign_lambert_shader(cls, name, shape_node, hsv=None):
        shader = cmds.shadingNode("lambert", name=name, asShader=True) 
        shader_sg = cmds.sets(name="{0}SG".format(shader), renderable=True, noSurfaceShader=True, empty=True)
        
        # Connect shader to shading group directly
        cmds.connectAttr(f"{shader}.outColor", f"{shader_sg}.surfaceShader", force=True)
        
        if hsv and len(hsv) == 3:
            h, s, v = hsv
            
            # Convert hue from degrees (0-360) to normalized (0.0-1.0)
            # If hue is > 1, assume it's in degrees
            if h > 1.0:
                hue = (h % 360) / 360.0
            else:
                hue = h % 1.0
            
            # Convert HSV to RGB
            r, g, b = colorsys.hsv_to_rgb(hue, s, v)
            
            # Set the color
            cmds.setAttr(f"{shader}.color", r, g, b, type="double3")
        
        # Assign to shape node
        cmds.sets([shape_node], edit=True, forceElement=shader_sg)
        
        return shader

    @classmethod
    def get_shape_from_transform(cls, transform_node):
        return cmds.listRelatives(transform_node, shapes=True, fullPath=True)[0]