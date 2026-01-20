# CustomLocator
# Originally developed in the CustomLocator repository
# https://github.com/FrameDarkZero/CustomLocator
#
# Integrated into P.E.A.R.L. (Procedural Engine for Automated Rigging Layouts)

import maya.cmds as cmds
import maya.OpenMaya as om

from GiancarloHelpers import GiancarloHelpers

class CustomLocator(object):
    
    # Class-level shader cache
    shader_cache = {}
    
    def __init__(self, name, side=None, orientation="x"):
        self.name = name
        self.side = side
        self.orientation = orientation
        
        if name == None:
            om.MGlobal.displayWarning("Please input a name")
            return
        else:
            self.locator = self.create_locator(name, side, orientation)
    
    def get_or_create_shader(self, shader_name, shape_node, hsv):
        """Get existing shader from cache or create a new one if it doesn't exist."""
        if shader_name in self.shader_cache:
            # Get existing shader and assign it to the shape
            shader_sg = self.shader_cache[shader_name]
            shader = cmds.listConnections(f"{shader_sg}.surfaceShader", source=True, destination=False)[0]
            
            # Assign the shader to the shape
            cmds.sets([shape_node], edit=True, forceElement=shader_sg)
            return shader
        else:
            # Create new shader and cache it
            shader = GiancarloHelpers.create_and_assign_lambert_shader(
                name=shader_name, 
                shape_node=shape_node, 
                hsv=hsv
            )
            # Store the shading group in cache
            shader_sg = f"{shader_name}SG"
            self.shader_cache[shader_name] = shader_sg
            return shader
    
    def create_locator(self, name, side, orientation):
        sphere = cmds.polySphere(name="sphere", radius=0.7, sa=20, sh=20, constructionHistory=False)[0]
        
        x_torus = cmds.polyTorus(name="x_torus", radius=0.7, sectionRadius="0.1", sa=40, sh=40, constructionHistory=False)[0]
        x_torus_shape = GiancarloHelpers.get_shape_from_transform(x_torus)
        y_torus = cmds.polyTorus(name="y_torus", radius=0.7, sectionRadius="0.1", sa=40, sh=40, constructionHistory=False)[0]
        y_torus_shape = GiancarloHelpers.get_shape_from_transform(y_torus)
        z_torus = cmds.polyTorus(name="z_torus", radius=0.7, sectionRadius="0.1", sa=40, sh=40, constructionHistory=False)[0]
        z_torus_shape = GiancarloHelpers.get_shape_from_transform(z_torus)
        
        x_cone = cmds.polyCone(name="x_cone", radius=0.4, height=0.8, sa=20, sh=1, constructionHistory=False)[0]
        x_cone_shape = GiancarloHelpers.get_shape_from_transform(x_cone)
        y_cone = cmds.polyCone(name="y_cone", radius=0.4, height=0.8, sa=20, sh=1, constructionHistory=False)[0]
        y_cone_shape = GiancarloHelpers.get_shape_from_transform(y_cone)
        z_cone = cmds.polyCone(name="z_cone", radius=0.4, height=0.8, sa=20, sh=1, constructionHistory=False)[0]
        z_cone_shape = GiancarloHelpers.get_shape_from_transform(z_cone)
        
        cmds.setAttr(f"{x_torus}.rotateZ", 90)
        cmds.setAttr(f"{z_torus}.rotateX", 90)
        cmds.setAttr(f"{x_cone}.rotateZ", -90)
        cmds.setAttr(f"{z_cone}.rotateX", 90)
        cmds.setAttr(f"{x_cone}.translateX", 2)
        cmds.setAttr(f"{y_cone}.translateY", 2)
        cmds.setAttr(f"{z_cone}.translateZ", 2)
        
        # Use cached shaders or create new ones
        orange = self.get_or_create_shader("orange_lambert", sphere, hsv=(21.246, 1, 1))
        red = self.get_or_create_shader("red_lambert", x_cone, hsv=(3.900, 1, 1))
        green = self.get_or_create_shader("green_lambert", y_cone, hsv=(103.302, 1, 1))
        blue = self.get_or_create_shader("blue_lambert", z_cone, hsv=(217.074, 1, 1))
        
        # Assign the same shaders to torus shapes
        red_sg = self.shader_cache.get("red_lambert", "red_lambertSG")
        green_sg = self.shader_cache.get("green_lambert", "green_lambertSG")
        blue_sg = self.shader_cache.get("blue_lambert", "blue_lambertSG")
        
        cmds.sets([x_torus_shape], edit=True, forceElement=red_sg)
        cmds.sets([y_torus_shape], edit=True, forceElement=green_sg)
        cmds.sets([z_torus_shape], edit=True, forceElement=blue_sg)
        
        cmds.makeIdentity([sphere, x_torus, y_torus, z_torus, x_cone, y_cone, z_cone], apply=True)
        cmds.parent([x_torus_shape, y_torus_shape, z_torus_shape, x_cone_shape, y_cone_shape, z_cone_shape], sphere, relative=True, shape=True)
        cmds.delete([x_torus, y_torus, z_torus, x_cone, y_cone, z_cone])
        
        if side:
            locator = cmds.rename(sphere, f"{side}_{name}_loc")
        else:
            locator = cmds.rename(sphere, f"{name}_loc")
            
        if orientation == "y":
            cmds.setAttr(f"{locator}.rotateZ", -90)
            self.transfer_to_offset_parent_matrix(locator)
        
        if orientation == "z":
            cmds.setAttr(f"{locator}.rotateX", 90)
            cmds.setAttr(f"{locator}.rotateZ", 90)
            self.transfer_to_offset_parent_matrix(locator)
        
        cmds.select(clear=True)
        
        return locator
    
    def transfer_to_offset_parent_matrix(self, obj):    
        translate = cmds.getAttr(f"{obj}.translate")[0]
        rotate = cmds.getAttr(f"{obj}.rotate")[0]
        scale = cmds.getAttr(f"{obj}.scale")[0]
        
        local_matrix = cmds.xform(obj, query=True, matrix=True, objectSpace=True)
        
        cmds.setAttr(f"{obj}.offsetParentMatrix", local_matrix, type="matrix")
        
        cmds.setAttr(f"{obj}.translate", 0, 0, 0, type="double3")
        cmds.setAttr(f"{obj}.rotate", 0, 0, 0, type="double3")
        cmds.setAttr(f"{obj}.scale", 1, 1, 1, type="double3")
        
        print(f"Transferred {obj}'s local transform to offsetParentMatrix and reset transforms.")
    
    def get_locator_name(self):
        return self.locator
    
    @classmethod
    def clear_shader_cache(cls):
        """Clear the shader cache if needed."""
        cls.shader_cache.clear()

if __name__ == "__main__":
    
    # Clear any existing shader cache (optional)
    # CustomLocator.clear_shader_cache()
    
    spine_01 = CustomLocator(name="spine_01", side="L", orientation="x")
    spine_01 = spine_01.get_locator_name()
    
    spine_02 = CustomLocator(name="spine_02", side=None, orientation="y")
    spine_02 = spine_02.get_locator_name()
    
    spine_03 = CustomLocator(name="spine_03", side="R", orientation="z")
    spine_03 = spine_03.get_locator_name()

    
