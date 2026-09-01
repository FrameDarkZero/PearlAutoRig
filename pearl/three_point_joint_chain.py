# ThreePointJointChain
# Originally developed in the ThreePointJointChain repository
# https://github.com/FrameDarkZero/ThreePointJointChain
#
# Integrated into P.E.A.R.L. (Procedural Engine for Automated Rigging Layouts)


# Maya Python (OO): 3-point joint chain from 3 locators
# - Builds a stable plane from the 3 points (A-pose safe)
# - Orients joints with "orient joint" style options:
#     primary_axis (x/-x/y/-y/z/-z)
#     secondary_axis (x/-x/y/-y/z/-z)
#     secondary_world_orient (x/-x/y/-y/z/-z)
# - Bakes rotations into jointOrient so rotate == 0
# - Optional coplanar triangle facet mesh
# - End joint orient policy: "parent" or "world"

import maya.cmds as cmds
import math


class ThreePointJointChain(object):
    def __init__(self,
                 locators=None,
                 prefix="L",
                 name="jointChain",
                 suffix="jnt",
                 primary_axis="x",
                 secondary_axis="y",
                 secondary_world_orient="y",
                 end_orient="parent",          # "parent" or "world"
                 create_coplanar_mesh=False,
                 secondary_world_vector=None,
                 use_cross_as_secondary=False,
                 secondary_world_vector_01=None,
                 secondary_world_vector_02=None,
                 ):
        """
        If locators is None, expects the user to have selected 3 transforms in order:
        root, mid, end.
        
        """
        self.locators = locators
        self.prefix = prefix
        self.name = name
        self.suffix = suffix
        self.primary_axis = primary_axis
        self.secondary_axis = secondary_axis
        self.secondary_world_orient = secondary_world_orient
        self.end_orient = end_orient
        self.create_coplanar_mesh = create_coplanar_mesh
        self.secondary_world_vector = secondary_world_vector
        self.use_cross_as_secondary = use_cross_as_secondary
        self.secondary_world_vector_01 = secondary_world_vector_01
        self.secondary_world_vector_02 = secondary_world_vector_02

        # outputs
        self.joints = []
        self.facet = None
        self.clusters = []

    # -----------------------------
    # Vector helpers
    # -----------------------------
    def vector_sub(self, a, b): 
        return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]
    def vector_dot(self, a, b): 
        return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
    def vector_cross(self, a, b):
        return [
            a[1]*b[2] - a[2]*b[1],  # X
            a[2]*b[0] - a[0]*b[2],  # Y
            a[0]*b[1] - a[1]*b[0]   # Z
        ]
    def vector_len(self, v): 
        return math.sqrt(self.vector_dot(v, v))

    def vector_norm(self, v):
        l = self.vector_len(v)
        if l < 1e-10:
            return [0.0, 0.0, 0.0]
        return [v[0]/l, v[1]/l, v[2]/l]

    # -----------------------------
    # Scene helpers
    # -----------------------------
    def get_ws_pos(self, node):
        return cmds.xform(node, query=True, worldSpace=True, translation=True)

    def axis_to_vec(self, axis_str):
        """
        axis_str examples: 'x', '-x', 'y', '-y', 'z', '-z'
        Returns (axisLetter, sign, baseVec)
        """
        sign = axis_str.strip().lower()
        num_sign = -1.0 if sign.startswith('-') else 1.0
        letter = sign[-1]
        if letter == 'x':
            base = [1.0, 0.0, 0.0]
        elif letter == 'y':
            base = [0.0, 1.0, 0.0]
        elif letter == 'z':
            base = [0.0, 0.0, 1.0]
        else:
            raise RuntimeError("Axis must be one of: x, -x, y, -y, z, -z")
        return letter.upper(), num_sign, base

    def safe_plane_normal(self, pos_01, pos_02, pos_03, world_up=(0.0, 1.0, 0.0)):
        a = self.vector_sub(pos_02, pos_01)
        b = self.vector_sub(pos_03, pos_01)
        normal = self.vector_cross(a, b)
        if self.vector_len(normal) < 1e-8:
            normal = list(world_up)
        normal = self.vector_norm(normal)

        # Make normal consistent w/ world_up so it doesn't randomly flip
        wu = self.vector_norm(list(world_up))
        if self.vector_dot(normal, wu) < 0.0:
            normal = [-normal[0], -normal[1], -normal[2]]
        return normal

    def orthonormal_from_aim_and_up(self, aim_vec, up_vec):
        """
        Build a right-handed orthonormal basis:
        X = aim
        Y = up (made orthogonal to aim)
        Z = X x Y
        """
        x = self.vector_norm(aim_vec)
        if self.vector_len(x) < 1e-8:
            x = [1.0, 0.0, 0.0]

        up_in = self.vector_norm(up_vec)
        if self.vector_len(up_in) < 1e-8:
            up_in = [0.0, 1.0, 0.0]

        # make Y orthogonal to X (Gram-Schmidt)
        proj = self.vector_dot(up_in, x)
        y = [up_in[0] - x[0]*proj, up_in[1] - x[1]*proj, up_in[2] - x[2]*proj]
        if self.vector_len(y) < 1e-8:
            # if parallel, pick a fallback
            y = [0.0, 1.0, 0.0] if abs(x[1]) < 0.9 else [1.0, 0.0, 0.0]
            proj = self.vector_dot(y, x)
            y = [y[0] - x[0]*proj, y[1] - x[1]*proj, y[2] - x[2]*proj]
        y = self.vector_norm(y)

        z = self.vector_norm(self.vector_cross(x, y))
        # re-orthonormalize y (ensures perfect right-handed frame)
        y = self.vector_norm(self.vector_cross(z, x))
        return x, y, z

    def basis_with_primary_secondary(self, primary_world_dir, secondary_world_dir,
                                    primary_axis="x", secondary_axis="y"):
        """
        Build world-space basis (Xw,Yw,Zw) that maps:
        - local primary_axis   -> primary_world_dir
        - local secondary_axis -> as close as possible to secondary_world_dir, orthogonalized
        """
        # Canonical frame uses X=primary, Y=secondary
        Xc, Yc, Zc = self.orthonormal_from_aim_and_up(primary_world_dir, secondary_world_dir)

        pa, psign, _ = self.axis_to_vec(primary_axis)
        sa, ssign, _ = self.axis_to_vec(secondary_axis)

        if pa == sa:
            raise RuntimeError("primary_axis and secondary_axis must be different axes (x/y/z).")

        axes = {'X': None, 'Y': None, 'Z': None}

        primary_vec = [Xc[0]*psign, Xc[1]*psign, Xc[2]*psign]
        secondary_vec = [Yc[0]*ssign, Yc[1]*ssign, Yc[2]*ssign]

        axes[pa] = primary_vec
        axes[sa] = secondary_vec

        remainder = ({'X', 'Y', 'Z'} - {pa, sa}).pop()

        # right-handed: X x Y = Z
        if remainder == 'Z':
            axes['Z'] = self.vector_norm(self.vector_cross(axes['X'], axes['Y']))
        elif remainder == 'Y':
            axes['Y'] = self.vector_norm(self.vector_cross(axes['Z'], axes['X']))
        elif remainder == 'X':
            axes['X'] = self.vector_norm(self.vector_cross(axes['Y'], axes['Z']))

        # final cleanup
        X = self.vector_norm(axes['X'])
        Y = self.vector_norm(axes['Y'])
        Z = self.vector_norm(self.vector_cross(X, Y))
        Y = self.vector_norm(self.vector_cross(Z, X))
        return X, Y, Z

    def matrix_from_axes_and_pos(self, x, y, z, pos):
        return [
            x[0], x[1], x[2], 0.0,
            y[0], y[1], y[2], 0.0,
            z[0], z[1], z[2], 0.0,
            pos[0], pos[1], pos[2], 1.0
        ]

    def freeze_joint_rotation_to_orient(self, joint):
        cmds.makeIdentity(joint, apply=True, translate=False, rotate=True, scale=False, normal=False, preserveNormals=True)

    def create_coplanar_facet(self, pos_01, pos_02, pos_03, desired_normal=None, name="coplanarFacet"):
        a = self.vector_sub(pos_02, pos_01)
        b = self.vector_sub(pos_03, pos_01)
        facet_normal = self.vector_norm(self.vector_cross(a, b))

        points = [pos_01, pos_02, pos_03]
        flipped = False

        if desired_normal is not None:
            desired_normal = self.vector_norm(desired_normal)
            if self.vector_dot(facet_normal, desired_normal) < 0.0:
                points = [pos_01, pos_03, pos_02]
                flipped = True

        facet = cmds.polyCreateFacet(point=points, name=name)[0]
        
        return facet, flipped
            
    def constraint_plane_to_joints(self, joints, plane, flipped=False):
        self.clusters = []
        
        plane_vtx = cmds.ls(plane + ".vtx[*]", flatten=True)
        
        if flipped:
            joints = [joints[0], joints[2], joints[1]]
        
        for i, vtx in enumerate(plane_vtx):
            
            cluster_deformer, cluster_handle = cmds.cluster(vtx, name=f"{plane}_vtx{i}_cluster")
            
            cmds.pointConstraint(joints[i], cluster_handle, maintainOffset=False)
            cmds.setAttr(cluster_handle + ".visibility", False)
            
            self.clusters.append({"deformer": cluster_deformer,
                                  "handle": cluster_handle})
            
        return self.clusters     
        
    def resolve_locators(self):
        if self.locators:
            if len(self.locators) != 3:
                raise RuntimeError("locators must be a list of exactly 3 transforms.")
            return self.locators

        selection = cmds.ls(selection=True, type="transform") or []
        if len(selection) != 3:
            raise RuntimeError("Select exactly 3 locator transforms in order: root, mid, end.")
        return selection
    
    def get_cross_secondary(self, aim_vec, secondary_vec):
        result = self.vector_cross(aim_vec, secondary_vec)

        # For Y and Z orientation, flip the cross order so the handedness stays consistent.
        if self.primary_axis in ["y", "z"]:
            result = self.vector_cross(secondary_vec, aim_vec)

        return self.vector_norm(result)
    
    def make_secondary_coplanar(self, aim_vec, plane_normal, preferred_secondary):
        """
        Keeps preferred_secondary's direction, but forces it to live inside
        the coplanar plane.

        This means:
        - aim axis still points down the chain
        - secondary/up axis follows ctrl orientation as closely as possible
        - cross axis stays perpendicular to the coplanar mesh
        """
        aim_vec = self.vector_norm(aim_vec)
        plane_normal = self.vector_norm(plane_normal)
        preferred_secondary = self.vector_norm(preferred_secondary)

        # First remove any component that points out of the coplanar plane.
        dot_to_normal = self.vector_dot(preferred_secondary, plane_normal)

        secondary = [
            preferred_secondary[0] - plane_normal[0] * dot_to_normal,
            preferred_secondary[1] - plane_normal[1] * dot_to_normal,
            preferred_secondary[2] - plane_normal[2] * dot_to_normal
        ]

        # Then remove any component that points down the aim axis.
        dot_to_aim = self.vector_dot(secondary, aim_vec)

        secondary = [
            secondary[0] - aim_vec[0] * dot_to_aim,
            secondary[1] - aim_vec[1] * dot_to_aim,
            secondary[2] - aim_vec[2] * dot_to_aim
        ]

        if self.vector_len(secondary) < 1e-8:
            secondary = plane_normal

        return self.vector_norm(secondary)
    
    def build(self):
        locs = self.resolve_locators()

        pos_01 = self.get_ws_pos(locs[0])
        pos_02 = self.get_ws_pos(locs[1])
        pos_03 = self.get_ws_pos(locs[2])

        # Secondary world orientation fallback.
        if self.secondary_world_vector:
            world_up = self.secondary_world_vector
        else:
            _, wsign, wbase = self.axis_to_vec(self.secondary_world_orient)
            world_up = [
                wbase[0] * wsign,
                wbase[1] * wsign,
                wbase[2] * wsign
            ]

        # Stable plane normal.
        plane_normal = self.safe_plane_normal(
            pos_01,
            pos_02,
            pos_03,
            world_up=world_up
        )

        # Segment aims.
        aim_01 = self.vector_sub(pos_02, pos_01)
        aim_02 = self.vector_sub(pos_03, pos_02)

        # Default secondary vectors use the coplanar plane.
        secondary_01 = plane_normal
        secondary_02 = plane_normal

        # Optional segment-specific control/local up references.
        if self.secondary_world_vector_01:
            secondary_01 = self.make_secondary_coplanar(
                aim_01,
                plane_normal,
                self.secondary_world_vector_01
            )

        if self.secondary_world_vector_02:
            secondary_02 = self.make_secondary_coplanar(
                aim_02,
                plane_normal,
                self.secondary_world_vector_02
            )

        # Optional thumb behavior:
        # use cross direction as the secondary axis.
        if self.use_cross_as_secondary:
            secondary_01 = self.get_cross_secondary(
                aim_01,
                secondary_01
            )

            secondary_02 = self.get_cross_secondary(
                aim_02,
                secondary_02
            )
        
        # facet_world_up = list(wbase)
        # facet_normal = self.safe_plane_normal(
        #     pos_01,
        #     pos_02,
        #     pos_03,
        #     world_up=facet_world_up
        # )

        # Use facet_normal instead of plane_normal if you want polygon
        # to face up even with negative secondary_world_orient.
        
        # Optional visual coplanar facet.
        facet_flipped = False

        if self.create_coplanar_mesh:
            self.facet, facet_flipped = self.create_coplanar_facet(
                pos_01,
                pos_02,
                pos_03,
                desired_normal=plane_normal,
                name=f"{self.prefix}_{self.name}_coplanarFacet"
            )

        # Build bases.
        X1, Y1, Z1 = self.basis_with_primary_secondary(
            aim_01,
            secondary_01,
            self.primary_axis,
            self.secondary_axis
        )

        X2, Y2, Z2 = self.basis_with_primary_secondary(
            aim_02,
            secondary_02,
            self.primary_axis,
            self.secondary_axis
        )

        # End joint orientation policy.
        if self.end_orient.lower() == "parent":
            X3, Y3, Z3 = X2, Y2, Z2
        elif self.end_orient.lower() == "world":
            X3, Y3, Z3 = [
                1.0,
                0.0,
                0.0
            ], [
                0.0,
                1.0,
                0.0
            ], [
                0.0,
                0.0,
                1.0
            ]
        else:
            raise RuntimeError('end_orient must be "parent" or "world".')

        # Create joints.
        cmds.select(clear=True)

        joint_01 = cmds.createNode(
            "joint",
            name=f"{self.prefix}_{self.name}_01_{self.suffix}"
        )

        joint_02 = cmds.createNode(
            "joint",
            name=f"{self.prefix}_{self.name}_02_{self.suffix}"
        )

        joint_03 = cmds.createNode(
            "joint",
            name=f"{self.prefix}_{self.name}_03_{self.suffix}"
        )

        cmds.parent(joint_02, joint_01)
        cmds.parent(joint_03, joint_02)

        # Apply world matrices.
        cmds.xform(
            joint_01,
            ws=True,
            m=self.matrix_from_axes_and_pos(X1, Y1, Z1, pos_01)
        )

        cmds.xform(
            joint_02,
            ws=True,
            m=self.matrix_from_axes_and_pos(X2, Y2, Z2, pos_02)
        )

        cmds.xform(
            joint_03,
            ws=True,
            m=self.matrix_from_axes_and_pos(X3, Y3, Z3, pos_03)
        )

        # Bake rotate into jointOrient.
        self.freeze_joint_rotation_to_orient(joint_01)
        self.freeze_joint_rotation_to_orient(joint_02)
        self.freeze_joint_rotation_to_orient(joint_03)

        self.joints = [
            joint_01,
            joint_02,
            joint_03
        ]

        if self.facet:
            self.constraint_plane_to_joints(
                [
                    joint_01,
                    joint_02,
                    joint_03
                ],
                self.facet,
                flipped=facet_flipped
            )

        cmds.select(clear=True)

        return {
            "joints": self.joints,
            "facet": self.facet,
            "clusters": self.clusters
        }
    
    @staticmethod
    def get_remaining_axis(primary_axis, secondary_axis):
        primary = primary_axis.replace("-", "").lower()
        secondary = secondary_axis.replace("-", "").lower()
        
        if primary == secondary:
            raise ValueError(
                "Primary Axis: {}, cannot be the same as Secondary Axis: {}".format(
                    primary, 
                    secondary
                )
                )
        
        # remaining = ({"x", "y", "z"} - {primary, secondary}).pop()
        # return remaining
        
        all_axes = ["x", "y", "z"]
        
        for axis in all_axes:
            if axis != primary and axis != secondary:
                return axis
    
    @classmethod
    def reorient_joint(cls,
                       joint_01=None,
                       joint_02=None,
                       helper_loc=None,
                       primary_axis="x",
                       secondary_axis="y",
                       secondary_world_orient="y",
                       freeze_to_joint_orient=True
                       ):
       
        # ---------------------------------
        # Resolve inputs from selection
        # ---------------------------------
        if not all([joint_01, joint_02, helper_loc]):
            selection = cmds.ls(selection=True, type="transform") or []
            if len(selection) != 3:
                raise RuntimeError(
                    "Provide joint_01, joint_02, helper_loc or select exactly 3 transforms in order."
                )
            joint_01, joint_02, helper_loc = selection

        # ---------------------------------
        # Validate nodes
        # ---------------------------------
        for node in [joint_01, joint_02, helper_loc]:
            if not cmds.objExists(node):
                raise RuntimeError("Node does not exist: {}".format(node))

        if cmds.nodeType(joint_01) != "joint":
            raise RuntimeError("{} must be a joint.".format(joint_01))

        if cmds.nodeType(joint_02) != "joint":
            raise RuntimeError("{} must be a joint.".format(joint_02))

        # ---------------------------------
        # Temporary helper instance
        # lets us reuse all the math helpers
        # ---------------------------------
        helper = cls(
            locators=None,
            prefix="tmp",
            name="tmp",
            suffix="jnt",
            primary_axis=primary_axis,
            secondary_axis=secondary_axis,
            secondary_world_orient=secondary_world_orient,
            end_orient="parent",
            create_coplanar_mesh=False
        )

        # ---------------------------------
        # Save child data before changing parent
        # ---------------------------------

        child_world_matrix = cmds.xform(joint_02, query=True, worldSpace=True, matrix=True)

        # ---------------------------------
        # Unparent child temporarily if it is parented under joint_01
        # ---------------------------------
        was_direct_child = False
        direct_parent = cmds.listRelatives(joint_02, parent=True)
        if direct_parent and direct_parent[0] == joint_01:
            was_direct_child = True
            cmds.parent(joint_02, world=True)

        # ---------------------------------
        # Get world positions
        # ---------------------------------
        pos_01 = helper.get_ws_pos(joint_01)
        pos_02 = helper.get_ws_pos(joint_02)
        pos_03 = helper.get_ws_pos(helper_loc)

        # ---------------------------------
        # Build world up hint
        # ---------------------------------
        _, wsign, wbase = helper.axis_to_vec(secondary_world_orient)

        world_up = [
            wbase[0] * wsign,
            wbase[1] * wsign,
            wbase[2] * wsign
        ]

        # ---------------------------------
        # Build aim and plane normal
        # ---------------------------------
        aim_vec = helper.vector_sub(pos_02, pos_01)
        if helper.vector_len(aim_vec) < 1e-8:
            raise RuntimeError("joint_01 and joint_02 are in the same position. Cannot build aim vector.")
        
        # If aim_vec is too close to world_up, use a safer fallback world axis.
        aim_norm = helper.vector_norm(aim_vec)
        world_up_norm = helper.vector_norm(world_up)

        dot_to_world_up = abs(helper.vector_dot(aim_norm, world_up_norm))

        if dot_to_world_up > 0.95:
            fallback_world_orients = ["x", "y", "z"]

            for fallback_orient in fallback_world_orients:
                _, fsign, fbase = helper.axis_to_vec(fallback_orient)

                fallback_world_up = [
                    fbase[0] * fsign,
                    fbase[1] * fsign,
                    fbase[2] * fsign
                ]

                fallback_dot = abs(
                    helper.vector_dot(
                        aim_norm,
                        helper.vector_norm(fallback_world_up)
                    )
                )

                if fallback_dot < 0.95:
                    world_up = fallback_world_up
                    break
        
        plane_normal = helper.safe_plane_normal(pos_01, pos_02, pos_03, world_up=world_up)

        # ---------------------------------
        # Build basis
        # ---------------------------------
        
        X, Y, Z = helper.basis_with_primary_secondary(
            primary_world_dir=aim_vec,
            secondary_world_dir=plane_normal,
            primary_axis=primary_axis,
            secondary_axis=secondary_axis
        )
        
        # ---------------------------------
        # Apply matrix to joint_01
        # ---------------------------------
        joint_01_matrix = helper.matrix_from_axes_and_pos(X, Y, Z, pos_01)
        cmds.xform(joint_01, worldSpace=True, matrix=joint_01_matrix)

        # ---------------------------------
        # Bake rotate -> jointOrient
        # ---------------------------------
        if freeze_to_joint_orient:
            helper.freeze_joint_rotation_to_orient(joint_01)

        # ---------------------------------
        # Reparent child back if needed
        # ---------------------------------
        if was_direct_child:
            cmds.parent(joint_02, joint_01)

        cmds.xform(joint_02, worldSpace=True, matrix=child_world_matrix)

        cmds.select(clear=True)

        return {
            "joint": joint_01,
            "child": joint_02,
            "helper": helper_loc
        }


if __name__ == "__main__":
    # builder = ThreePointJointChain(
    #     locators=[],                 # or ["L_arm_root_loc","L_arm_mid_loc","L_arm_end_loc"]
    #     prefix="r",
    #     name="arm",
    #     suffix="fk",
    #     primary_axis="z",              # like orient joint "Primary Axis"
    #     secondary_axis="x",            # like orient joint "Secondary Axis"
    #     secondary_world_orient="y",   # like "World Orientation" (+Y); use "-y" for -Y, etc.
    #     end_orient="parent",           # "parent" or "world"
    #     create_coplanar_mesh=True      # creates a triangle facet through the points
    # )

    # chain = builder.build()
    # print("Result:", chain)
    
    ThreePointJointChain.reorient_joint(
    joint_02="L_arm_01_thumb_02_jnt",
    joint_01="L_arm_01_thumb_01_jnt",
    helper_loc="arm_01_thumb_reorient_helper_loc",
    primary_axis="y",
    secondary_axis="z",
    secondary_world_orient="-z"
)

    # remaining = ThreePointJointChain.get_remaining_axis("x", "y")
    # print(remaining)
    
