import os
import glob
import gc

from time import time

import bpy
from bpy_extras import image_utils

from mathutils import Vector
import imp

from . import slice_plane
# imp.reload(slice_plane)
# from . import object_intersection
# imp.reload(object_intersection)
# from . import aabb_tree
# imp.reload(aabb_tree)
# from . import aabb_directional_tree
# imp.reload(aabb_directional_tree)

from .intersector import Intersector
from .blender_quad_edge_mesh import BlenderQEMeshBuilder
from .quad_edge_mesh.aabb_tree import AABBTree

class BlendSegOperator (bpy.types.Operator):
    bl_idname = "object.blendseg"
    bl_label = "Blendseg Operator"
    
    def execute(self, context):
        print("Executing...")
        # Save cursor position and move to origin
        # This will fix the position of the contours in Blender v2.68
        old_position = Vector(context.scene.cursor_location)
        context.scene.cursor_location = Vector((0., 0., 0.))
        
        start = time()
        bs = BlendSeg()
        mesh = bpy.data.objects['Mesh']

        bs.is_updating = True
        bs.update_all_intersections(mesh)
        bs.is_updating = False
        
        seconds = time() - start
        print("Took %1.5f seconds." % seconds)

        # Return cursor position to where it was before calling execute
        context.scene.cursor_location = old_position
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        """ Only run if an object named 'Mesh' exists """
        return 'Mesh' in bpy.data.objects

        
    
class BlendSeg (object):
    """ Compute and render the intersections of a mesh.
    
    Intersection contours can be rendered on each plane in order to aid 
    precision. Activating the operator will search for a mesh named "Mesh"
    and then compute the intersection with 3 orthogonal planes (which will
    be created if necessary). 

    This tool is meant to aid with segmentation. Computing intersections is
    currently quite slow for the meshes I'm working on,
    otherwise it'd be nice to have it update in real time.
    
    It will read images corresponding to axial, saggital, and coronal
    slices, and store them as textures. Three planes are created
    corresponding to the 3 principal directions. DICOM is not supported.
    """
    
    letter = "A"

    image_dir = "/home/andrew/workspace/imageBlowup/"+letter+"tiff/"
    image_ext = "*.tif"
    axi_prefix = "axial/"+letter+"axi"
    sag_prefix = "sagittal/"+letter+"sag"
    cor_prefix = "coronal/"+letter+"cor"

    axi_files = sorted(glob.glob (image_dir + axi_prefix + image_ext))
    sag_files = sorted(glob.glob (image_dir + sag_prefix + image_ext))
    cor_files = sorted(glob.glob (image_dir + cor_prefix + image_ext))

    #axi_files = ['/home/andrew/workspace/imageBlowup/Atiff/axial/Aaxi0160.tif']
    #sag_files = ['/home/andrew/workspace/imageBlowup/Atiff/sagittal/Asag0256.tif']
    #cor_files = ['/home/andrew/workspace/imageBlowup/Atiff/coronal/Acor0256.tif']

    #image_origin = tuple([239.616/2,239.616/2,0.])
    image_origin = tuple([0.,21.5,-51])
    image_spacing = tuple([0.468,0.468,0.5])

    show_timing_msgs = False

    __instance = None
    def __new__(cls):

        if BlendSeg.__instance is None:
            if BlendSeg.show_timing_msgs:
                print("Initializing BlendSeg")
            BlendSeg.__instance = super(BlendSeg, cls).__new__(cls)
            BlendSeg.__instance.load_img_stacks()
            BlendSeg.__instance.create_planes()
            BlendSeg.__instance.mesh_qem = None
            BlendSeg.__instance.mesh_tree = None
            BlendSeg.__instance.is_updating = False

            bpy.app.handlers.scene_update_post.append(
                BlendSeg.__instance.scene_update_callback)
            #if self.is_interactive:
            bpy.app.handlers.scene_update_pre.append(
                BlendSeg.__instance.scene_update_contour_callback)
                
        return BlendSeg.__instance
    
    def __init__(self):
        pass
        #bpy.app.handlers.scene_update_post.clear()
        # bpy.app.handlers.scene_update_pre.append(self.scene_update_callback)

    def scene_update_callback(self, scene):
        """ Hook this into scene_update_post.
        Let's use it to deterine if we need to update meshes.
        I wonder if it can be made interactive?
        """
        try:
            mesh = scene.objects[self.mesh_qem.blender_name]
        except KeyError:
            print(self.mesh_qem.blender_name + " wasn't found!")
            return
        
        if mesh.is_updated:
            print("Mesh was updated!!")
            self.mesh_qem.is_updated = True
            
    def scene_update_contour_callback(self, scene):
        """ Update the intersection contours in a callback.
        If the mesh is small enough, it shouldn't be a big deal.
        """

        if self.is_updating:
            return

        if (not self.sag_plane.is_updated and
            not self.axi_plane.is_updated and
            not self.cor_plane.is_updated and
            not self.mesh_qem.is_updated):
            return
        
        try:
            mesh = scene.objects[self.mesh_qem.blender_name]
        except KeyError:
            print(self.mesh_qem.blender_name + " wasn't found!")
            return

        self.is_updating = True

        # Save cursor position and move to origin
        # This will fix the position of the contours in Blender v2.68
        old_position = Vector(scene.cursor_location)
        scene.cursor_location = Vector((0., 0., 0.))

        if BlendSeg.show_timing_msgs:
            print("Updating all contours...")
            start = time()
        self.update_all_intersections(mesh)
        if BlendSeg.show_timing_msgs:
            seconds = time() - start
            print("Took %1.5f seconds" % seconds)
        
        # Return cursor position to where it was before calling execute
        scene.cursor_location = old_position
        
        self.is_updating = False
        self.sag_plane.is_updated = False
        self.cor_plane.is_updated = False
        self.axi_plane.is_updated = False
        self.mesh_qem.is_updated = False

    def load_img_stacks(self):
        print ("Looking for " + BlendSeg.letter + " image sequence")
        axi_files = BlendSeg.axi_files
        sag_files = BlendSeg.sag_files
        cor_files = BlendSeg.cor_files

        try:
            self.axi_imgs = [image_utils.load_image(f).name for f in axi_files]
            self.sag_imgs = [image_utils.load_image(f).name for f in sag_files]
            self.cor_imgs = [image_utils.load_image(f).name for f in cor_files]
        except AttributeError:
            print("Couldn't find certain images!")
            return
            
        print ("Loaded " + str(len(self.axi_imgs)) + " axial images!")
        print ("Loaded " + str(len(self.sag_imgs)) + " sagittal images!")
        print ("Loaded " + str(len(self.cor_imgs)) + " coronal images!")
        
    def create_planes(self):
        self.axi_plane = slice_plane.SlicePlane (
            'AXIAL', self.image_origin,
            self.axi_imgs, BlendSeg.image_spacing)
        self.sag_plane = slice_plane.SlicePlane (
            'SAGITTAL', self.image_origin,
            self.sag_imgs, BlendSeg.image_spacing)
        self.cor_plane = slice_plane.SlicePlane (
            'CORONAL', self.image_origin,
            self.cor_imgs, BlendSeg.image_spacing)
        
        # Create a new object to hold the contours
        if (bpy.ops.object.mode_set.poll()):
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.add(type='MESH')
        loop = bpy.context.object
        loop.name = self.axi_plane.loop_name
        
        bpy.ops.object.add(type='MESH')
        loop = bpy.context.object
        loop.name = self.sag_plane.loop_name
        
        bpy.ops.object.add(type='MESH')
        loop = bpy.context.object
        loop.name = self.cor_plane.loop_name

    def update_all_intersections (self, mesh):
        mesh.hide = False
        """ Attempt to find our planes """
        try:
            sp = bpy.data.objects[self.sag_plane.plane_name]
            ap = bpy.data.objects[self.axi_plane.plane_name]
            cp = bpy.data.objects[self.cor_plane.plane_name]
        except KeyError:
            print("Warning! Can't find all planes by name...")
            return

        # Generate CMesh objects for planes, mesh
        if self.mesh_qem is None:
            if BlendSeg.show_timing_msgs:
                print("Generating Quad-Edge Meshes")
                start = time()
            self.sp_qem = BlenderQEMeshBuilder.construct_from_blender_object(sp)
            self.ap_qem = BlenderQEMeshBuilder.construct_from_blender_object(ap)
            self.cp_qem = BlenderQEMeshBuilder.construct_from_blender_object(cp)
            self.mesh_qem = BlenderQEMeshBuilder.construct_from_blender_object(mesh)
            self.mesh_qem.is_rigid = False
            if BlendSeg.show_timing_msgs:
                seconds = time() - start
                print("Took %1.5f seconds" % seconds)

        # Call this to update matrix_world
        #bpy.data.scenes[0].update()
        if self.mesh_tree is None:
            if BlendSeg.show_timing_msgs:
                print("Generating AABB Trees")
                start = time()
            self.sp_tree = AABBTree(self.sp_qem)
            self.ap_tree = AABBTree(self.ap_qem)
            self.cp_tree = AABBTree(self.cp_qem)
            self.mesh_tree = AABBTree(self.mesh_qem)

            # First time initialization
            # self.sp_qem.update_vertex_positions()
            self.sp_qem.update_bounding_boxes()
            # self.ap_qem.update_vertex_positions()
            self.ap_qem.update_bounding_boxes()
            # self.cp_qem.update_vertex_positions()
            self.cp_qem.update_bounding_boxes()
            # self.mesh_qem.update_vertex_positions()
            self.mesh_qem.update_bounding_boxes()

            self.sp_tree.update_bbs()
            self.ap_tree.update_bbs()
            self.cp_tree.update_bbs()
            self.mesh_tree.update_bbs()
            #self.mesh_tree.update_bbs_mt()
            
            if BlendSeg.show_timing_msgs:
                seconds = time() - start
                print("Took %1.5f seconds" % seconds)
            
        if BlendSeg.show_timing_msgs:
            print("  Refreshing vertex positions")
        start = time()
        self.sp_qem.update_vertex_positions()
        self.ap_qem.update_vertex_positions()
        self.cp_qem.update_vertex_positions()
        if self.mesh_qem.is_updated:
            if BlendSeg.show_timing_msgs:
                print("updating mesh_qem!")
            self.mesh_qem.update_vertex_positions()
        #self.mesh_qem.update_vertex_positions_mt()
        if BlendSeg.show_timing_msgs:
            seconds = time() - start
            print("  Took %1.5f seconds" % (seconds))

        if BlendSeg.show_timing_msgs:
            print("  Refreshing bounding box positions")
            start = time()
        self.sp_qem.update_bounding_boxes()
        self.ap_qem.update_bounding_boxes()
        self.cp_qem.update_bounding_boxes()
        if self.mesh_qem.is_updated:
            self.mesh_qem.update_bounding_boxes()
        if BlendSeg.show_timing_msgs:
            seconds = time() - start
            print("  Took %1.5f seconds" % (seconds))
        
        if BlendSeg.show_timing_msgs:
            print("  Refreshing aabb trees to see how fast...")
            start = time()
        self.sp_tree.update_bbs()
        self.ap_tree.update_bbs()
        self.cp_tree.update_bbs()
        if self.mesh_qem.is_updated:
            #self.mesh_tree.update_bbs()
            self.mesh_tree.update_bbs_mt()
        if BlendSeg.show_timing_msgs:
            seconds = time() - start
            print("  Took %1.5f seconds" % (seconds))

        gc.disable()
        if not sp.hide and (self.sag_plane.is_updated or self.mesh_qem.is_updated):
            if BlendSeg.show_timing_msgs:
                print("  Computing sagittal intersection...")
                start = time()
            loop1 = self.compute_intersection_qem(bpy.context.scene,
                                                  self.sag_plane,
                                                  self.sp_qem, self.mesh_qem,
                                                  self.sp_tree, self.mesh_tree,
                                                  self.sag_plane.loop_name)
            if BlendSeg.show_timing_msgs:
                seconds = time() - start
                print("  Took %1.5f seconds" % (seconds))
        else:
            try:
                loop1 = bpy.context.scene.objects[self.sag_plane.loop_name]
            except KeyError:
                loop1 = None

        if not ap.hide and (self.axi_plane.is_updated or self.mesh_qem.is_updated):
            if BlendSeg.show_timing_msgs:
                print("  Computing axial intersection...")
                start = time()
            loop2 = self.compute_intersection_qem(bpy.context.scene,
                                                  self.axi_plane,
                                                  self.ap_qem, self.mesh_qem,
                                                  self.ap_tree, self.mesh_tree,
                                                  self.axi_plane.loop_name)
            if BlendSeg.show_timing_msgs:
                seconds = time() - start
                print("  Took %1.5f seconds" % (seconds))
        else:
            try:
                loop2 = bpy.context.scene.objects[self.axi_plane.loop_name]
            except KeyError:
                loop2 = None

        if not cp.hide and (self.cor_plane.is_updated or self.mesh_qem.is_updated):
            if BlendSeg.show_timing_msgs:
                print("  Computing coronal intersection...")
                start = time()
            loop3 = self.compute_intersection_qem(bpy.context.scene,
                                                  self.cor_plane,
                                                  self.cp_qem, self.mesh_qem,
                                                  self.cp_tree, self.mesh_tree,
                                                  self.cor_plane.loop_name)
            if BlendSeg.show_timing_msgs:
                seconds = time() - start
                print("  Took %1.5f seconds" % (seconds))
        else:
            try:
                loop3 = bpy.context.scene.objects[self.cor_plane.loop_name]
            except KeyError:
                loop3 = None


        gc.enable()
        
        # These need to be hidden/shown after the all computations
        if not sp.hide and loop1:
            loop1.select = True
        if not ap.hide and loop2:
            loop2.select = True
        if not cp.hide and loop3:
            loop3.select = True

        if False:
            bpy.data.scenes[0].update()

        bpy.context.scene.objects.active = mesh
        mesh.select = True
        bpy.ops.object.mode_set(mode='SCULPT')
        
        mesh.hide = True
        
    def compute_intersection_qem (self, scene,
                                  sl_plane,
                                  plane, mesh,
                                  plane_tree, mesh_tree,
                                  loop_name):
        """ Compute intersection of plane and mesh and return a
        contour representing their intersection.
        """
        # Try to remove old loop before anything else
        try:
            loop = scene.objects[loop_name]
        except KeyError:
            pass
            #print("Couldn't find old loop! Continuing")
        else:
            scene.objects.unlink(loop)
            bpy.data.objects.remove(loop)

        if BlendSeg.show_timing_msgs:
            print("  Searching for ix_points")
            start = time()
        ixer = Intersector()
        # ix_contours = ixer.compute_intersection_contour(mesh, plane,
        #                                                 mesh_tree, plane_tree)
        ix_contours = ixer.compute_intersection_with_plane(mesh, mesh_tree, sl_plane)
        if BlendSeg.show_timing_msgs:
            seconds = time() - start
            print("  Took %1.5f seconds" % seconds)

        # try:
        #     loop = bpy.context.scene.objects[loop_name]
        # except KeyError:
        #     print("Couldn't find " + loop + "!")
        #     return

        # Clear all old vertices
        # bpy.context.scene.objects.active = loop
        # if not bpy.ops.mesh.delete.poll():
        #     bpy.ops.object.mode_set(mode='EDIT', toggle=True)
        #     bpy.ops.mesh.delete()
        #     bpy.ops.object.mode_set(mode='EDIT', toggle=True)
        # else:
        #     bpy.ops.mesh.delete()
        
        if BlendSeg.show_timing_msgs:
            print("  Creating blender contour")
            start = time()
        loop = self._create_blender_contour(ix_contours, loop_name)
        if BlendSeg.show_timing_msgs:
            seconds = time() - start
            print("  Took %1.5f seconds" % seconds)
        
        return loop

    def _create_blender_contour (self, contours, loop_name):
        """ Create a blender object representing one or more contours.

        loop_name - name of the new blender object
        contour - A list of IntersectionPoints representing the contour
        """
        if len(contours) == 0:
            return None
        
        # Create a new object to hold the contours
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.add(type='MESH')
        loop = bpy.context.object
        loop.name = loop_name
        # try:
        #     loop = bpy.context.scene.objects[loop_name]
        # except KeyError:
        #     print("Couldn't find " + loop + "!")
        #     return
        
        for contour in contours:
            # print ("Contour length: " + str(len(contour)))

            vert_start_idx = len(loop.data.vertices)
            edge_start_idx = len(loop.data.edges)
            if contour[0] == contour[-1]:
                # closed loop
                is_closed = True
                num_ixps = len(contour) - 1
                loop.data.edges.add(len(contour) - 1)
            else:
                # open loop
                is_closed = False
                num_ixps = len(contour)
                loop.data.edges.add(len(contour) - 1)
                
            loop.data.vertices.add(num_ixps)

            for idx in range(0, num_ixps):
                vert = loop.data.vertices[vert_start_idx + idx]
                vert.co = tuple(contour[idx].point)
                # print("vert.co: " + str(vert.co))

            for idx in range(0, num_ixps - 1):
                edge = loop.data.edges[edge_start_idx + idx]
                edge.vertices = (vert_start_idx + idx, vert_start_idx + idx + 1)

            if is_closed:
                edge = loop.data.edges[-1]
                edge.vertices = (vert_start_idx + num_ixps - 1, vert_start_idx)

        #loop.data.update()
        
        return loop

def register():
    """Register Blendseg Operator with blender"""
    bpy.utils.register_class(BlendSegOperator)

# For convenience, register ths when imported
register()
