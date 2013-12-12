import os
import glob

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

class BreakBlendSegOperator (bpy.types.Operator):
    bl_idname = "object.breakblendseg"
    bl_label = "Break Blendseg"

    def execute(self, context):
        print ("Breaking...")

        # Load image
        fname = "/home/andrew/workspace/imageBlowup/Atiff/axial/Aaxi0256.tif"
        img_name = image_utils.load_image(fname).name
        img = bpy.data.images[img_name]

        # Create texture
        texture = bpy.data.textures.new(name="Aaxi0256", type='IMAGE')
        texture.image=img

        # Create material
        material = bpy.data.materials.new(name="AXImat")
        slot = material.texture_slots.add()
        slot.texture = texture
        slot.texture_coords = 'UV'
        material.use_shadeless = True
        material.game_settings.use_backface_culling = False

        # Create a mesh for the plane
        verts=[]
        verts.append((1.0, -1.0, 0.0))
        verts.append((-1.0, -1.0, 0.0))
        verts.append((1.0, 1.0, 0.0))
        verts.append((-1.0, 1.0, 0.0))

        edges=[]
        edges.append((0,1))
        edges.append((2,3))
        edges.append((3,1))
        edges.append((0,2))

        faces=[]
        faces.append((2,3,1,0))
                     
        meshplane = bpy.data.meshes.new("AXIplane")
        meshplane.from_pydata(verts, edges, faces)
        meshplane.name = "AXIplane"

        plane = bpy.data.objects.new(meshplane.name, meshplane)
        bpy.context.scene.objects.link(plane)

        # Tell the plane to use the material and texture we created
        plane.data.materials.append(material)
        plane.data.uv_textures.new()
        plane.data.uv_textures[0].data[0].image = \
            material.texture_slots[0].texture.image
        
        try:
            mesh = bpy.data.objects['Mesh']
        except KeyError:
            print("Couldn't find mesh when running operator: " +
                  BlendSeg.blender_mesh_name)
        else:
            mesh.data.calc_tessface()
            mesh.data.calc_tessface()
            
        
        return {'FINISHED'}

    def invoke(self, context, event):
        # wm = context.window_manager
        # return wm.invoke_props_dialog(self)
        # try:
        #     mesh = bpy.data.objects[BlendSeg.blender_mesh_name]
        # except KeyError:
        #     print("Couldn't find mesh when running operator: " +
        #           BlendSeg.blender_mesh_name)
        #     return {'FINISHED'}
        
        # mesh.hide = False
        # mesh.select = False
       
        return self.execute(context)

    @classmethod
    def poll(cls, context):
        """ Only run if an object named 'Mesh' exists """
        # return (BlendSeg.blender_mesh_name in bpy.data.objects and
        #         context.mode == 'OBJECT')
        return context.mode == 'OBJECT'
    

class BlendSegOperator (bpy.types.Operator):
    bl_idname = "object.blendseg"
    bl_label = "Blendseg Operator"
    
    axi_dir_root = bpy.props.StringProperty(name="Axial images dir. root")
    cor_dir_root = bpy.props.StringProperty(name="Coronal images dir. root")
    sag_dir_root = bpy.props.StringProperty(name="Sagittal images dir. root")
    
    def execute(self, context):
        print("Executing...")
        # Save cursor position and move to origin
        # This will fix the position of the contours in Blender v2.68
        old_position = Vector(context.scene.cursor_location)
        context.scene.cursor_location = Vector((0., 0., 0.))
        
        start = time()
        bs = BlendSeg()

        try:
            mesh = bpy.data.objects[BlendSeg.blender_mesh_name]
        except KeyError:
            print("Couldn't find mesh when running operator: " +
                  BlendSeg.blender_mesh_name)
            return {'FINISHED'}
        
        bs.is_updating = True
        bs.update_all_intersections(mesh)
        bs.is_updating = False
        
        seconds = time() - start
        print("Took %1.5f seconds." % seconds)

        # Return cursor position to where it was before calling execute
        #context.scene.cursor_location = old_position
        return {'FINISHED'}

    def invoke(self, context, event):
        # wm = context.window_manager
        # return wm.invoke_props_dialog(self)
        try:
            mesh = bpy.data.objects[BlendSeg.blender_mesh_name]
        except KeyError:
            print("Couldn't find mesh when running operator: " +
                  BlendSeg.blender_mesh_name)
            return {'FINISHED'}
        
        mesh.hide = False
        mesh.select = False
        
        return self.execute(context)

    @classmethod
    def poll(cls, context):
        """ Only run if an object named 'Mesh' exists """
        return (BlendSeg.blender_mesh_name in bpy.data.objects and
                context.mode == 'OBJECT')

class BlendSegCleanupOperator (bpy.types.Operator):
    """ Cleanup the existing BlendSeg instance, if it exists.
    """
    bl_idname = "object.cleanblendseg"
    bl_label = "Cleanup BlendSeg"
    
    def execute(self, context):
        """ Cleanup the existing BlendSeg instance.
        """
        try:
            mesh = bpy.data.objects[BlendSeg.blender_mesh_name]
        except KeyError:
            print("Couldn't find mesh when running operator: " +
                  BlendSeg.blender_mesh_name)
            return {'FINISHED'}
        
        bpy.context.scene.objects.active = None
        mesh.select = False
        mesh.hide = False
        
        print ("Cleaning up BlendSeg!")
        BlendSeg._cleanup()
        return {'FINISHED'}
    
    @classmethod
    def poll(cls, context):
        """ Only run if BlendSeg instance has been instantiated.
        """
        return BlendSeg.has_instance()

    
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
    
    letter = "G"

    image_dir = "/home/andrew/workspace/imageBlowup/"+letter+"tiff/"
    image_ext = "*.tif"
    axi_prefix = "axial/"+letter+"axi"
    sag_prefix = "sagittal/"+letter+"sag"
    cor_prefix = "coronal/"+letter+"cor"

    axi_dir_root = image_dir + axi_prefix
    cor_dir_root = image_dir + cor_prefix
    sag_dir_root = image_dir + sag_prefix

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

    blender_mesh_name = "Mesh"

    __instance = None
    def __new__(cls):
        """ Get existing BlendSeg instance, or create a new
        one if it doesn't exist.
        """

        if BlendSeg.__instance is None:
            if BlendSeg.show_timing_msgs:
                print("Initializing BlendSeg")
            BlendSeg.__instance = super(BlendSeg, cls).__new__(cls)
            BlendSeg.__instance.load_img_stacks()
            BlendSeg.__instance.create_planes()
            # BlendSeg.__instance.mesh_qem = None
            # BlendSeg.__instance.mesh_tree = None
            # BlendSeg.__instance.is_updating = False
            
            # BlendSeg.__instance.register_callback()

        return BlendSeg.__instance

    @classmethod
    def _cleanup(cls):
        """ Delete the existing instance.
        """
        if cls.__instance is not None:
            cls.__instance.remove_and_cleanup()
            del cls.__instance
            cls.__instance = None

    @classmethod
    def has_instance(cls):
        """ Check if BlendSeg instance exists.
        Return true if __instance is not None, false otherwise.
        """
        return BlendSeg.__instance is not None
    
    def __init__(self):
        pass
        #bpy.app.handlers.scene_update_post.clear()
        # bpy.app.handlers.scene_update_pre.append(self.scene_update_callback)

    def register_callback(self):
        """ Register the contour-update callbacks in Blender.
        """
        bpy.app.handlers.scene_update_post.append(
            self.scene_update_callback)
        #if self.is_interactive:
        bpy.app.handlers.scene_update_pre.append(
            self.scene_update_contour_callback)
        
    def unregister_callback(self):
        """ Remove the contour-update callbacks in Blender.
        """
        if self.scene_update_callback in bpy.app.handlers.scene_update_post:
            bpy.app.handlers.scene_update_post.remove(
                self.scene_update_callback)
        #if self.is_interactive:
        if self.scene_update_contour_callback in bpy.app.handlers.scene_update_pre:
            bpy.app.handlers.scene_update_pre.remove(
                self.scene_update_contour_callback)

    def remove_and_cleanup(self):
        """ Delete all planes, images, and loops associated with
        this BlendSeg object in Blender.
        Unregister loop-callbacks and plane-update-callbacks
        from Blender.
        """
        self.unregister_callback()
        self.delete_planes()
        self.delete_meshes()

        try:
            mesh = bpy.context.scene.objects[
                BlendSeg.blender_mesh_name]
        except KeyError:
            print(BlendSeg.blender_mesh_name +
                  " wasn't found during remove and cleanup!")
            return
        
        bpy.context.scene.objects.active = mesh
        # mesh.select = True
        # mesh.hide = False
        if not bpy.ops.object.mode_set.poll():
            print("Failed to set mode to object.")
            return
        bpy.ops.object.mode_set(mode='OBJECT')

    def delete_planes(self):
        """ Delete sag, cor, and axi planes in Blender.

        This will unregister callbacks associated with the planes.
        Also deletes loops if they exist.
        """
        self.axi_plane.remove_and_cleanup()
        self.cor_plane.remove_and_cleanup()
        self.sag_plane.remove_and_cleanup()

    def delete_meshes(self):
        """ Delete all QEM storage (for mesh and 3 planes).
        """
        del self.mesh_qem
        del self.sp_qem
        del self.ap_qem
        del self.cp_qem

    def scene_update_callback(self, scene):
        """ Check if the mesh has been sculpted/modified.
        """
        try:
            mesh = scene.objects[self.mesh_qem.blender_name]
        except KeyError:
            #print(self.mesh_qem.blender_name + " wasn't found!")
            return

        # TODO: if mesh is visible, don't update
        if mesh.is_updated: # and mesh.hide:
            if BlendSeg.show_timing_msgs:
                print(self.mesh_qem.blender_name + " was updated!!")
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
            #print(self.mesh_qem.blender_name + " wasn't found!")
            return

        # Don't bother updating contour if mesh is visible.
        # if not mesh.hide:
        #     return
        
        self.is_updating = True

        # Save cursor position and move to origin
        # This will fix the position of the contours in Blender v2.68
        old_position = Vector(scene.cursor_location)
        scene.cursor_location = Vector((0., 0., 0.))

        bpy.context.scene.objects.active = None
        mesh.select = False
        mesh.hide = False
        
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
        # self.sag_plane = slice_plane.SlicePlane (
        #     'SAGITTAL', self.image_origin,
        #     self.sag_imgs, BlendSeg.image_spacing)
        # self.cor_plane = slice_plane.SlicePlane (
        #     'CORONAL', self.image_origin,
        #     self.cor_imgs, BlendSeg.image_spacing)
        
        # Create a new object to hold the contours
        # if (bpy.ops.object.mode_set.poll()):
        #     bpy.ops.object.mode_set(mode='OBJECT')
        # else:
        #     print("Couldn't set OBJECT mode!")
        #     return

        # bpy.ops.object.add(type='MESH')
        # loop = bpy.context.object
        # loop.name = self.axi_plane.loop_name
        
        # bpy.ops.object.add(type='MESH')
        # loop = bpy.context.object
        # loop.name = self.sag_plane.loop_name
        
        # bpy.ops.object.add(type='MESH')
        # loop = bpy.context.object
        # loop.name = self.cor_plane.loop_name

    def update_all_intersections (self, mesh):
        # Is this causing a crash??
        # mesh.select = False
        return
        # mesh.hide = True
        print ("")
        print ("mesh.hide: " + str(mesh.hide))
        print ("mesh.select: " + str(mesh.select))
        print ("active_object: " + str(bpy.context.active_object))
        """ Attempt to find our planes """
        try:
            sp = bpy.data.objects[self.sag_plane.plane_name]
            ap = bpy.data.objects[self.axi_plane.plane_name]
            cp = bpy.data.objects[self.cor_plane.plane_name]
        except KeyError:
            print("Warning! Can't find all planes by name...")
            return

        print ("A")
        # Generate CMesh objects for planes, mesh
        if self.mesh_qem is None:
            if BlendSeg.show_timing_msgs:
                print("Generating Quad-Edge Meshes")
                start = time()
            # print ("Aa")
            # self.sp_qem = BlenderQEMeshBuilder.construct_from_blender_object(sp)
            # print ("Ab")
            # self.ap_qem = BlenderQEMeshBuilder.construct_from_blender_object(ap)
            # print ("Ac")
            # self.cp_qem = BlenderQEMeshBuilder.construct_from_blender_object(cp)
            # print("Ad")
            # self.mesh_qem = BlenderQEMeshBuilder.construct_from_blender_object(mesh)
            mesh.data.calc_tessface()
            # self.mesh_qem.is_rigid = False
            if BlendSeg.show_timing_msgs:
                seconds = time() - start
                print("Took %1.5f seconds" % seconds)
        print ("B")
        
        return
    
        # Call this to update matrix_world
        if self.mesh_tree is None:
            if BlendSeg.show_timing_msgs:
                print("Generating AABB Trees")
                start = time()
            self.sp_tree = AABBTree(self.sp_qem)
            self.ap_tree = AABBTree(self.ap_qem)
            self.cp_tree = AABBTree(self.cp_qem)
            self.mesh_tree = AABBTree(self.mesh_qem)

            # First time initialization
            self.sp_qem.update_bounding_boxes()
            self.ap_qem.update_bounding_boxes()
            self.cp_qem.update_bounding_boxes()
            self.mesh_qem.update_bounding_boxes()

            self.sp_tree.update_bbs()
            self.ap_tree.update_bbs()
            self.cp_tree.update_bbs()
            self.mesh_tree.update_bbs()
            #self.mesh_tree.update_bbs_mt()
            
            if BlendSeg.show_timing_msgs:
                seconds = time() - start
                print("Took %1.5f seconds" % seconds)

        print ("C")
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
            
        print ("D")
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

        print ("E")
        if BlendSeg.show_timing_msgs:
            print("  Refreshing aabb trees to see how fast...")
            start = time()
        self.sp_tree.update_bbs()
        self.ap_tree.update_bbs()
        self.cp_tree.update_bbs()
        if self.mesh_qem.is_updated:
            self.mesh_tree.update_bbs()
            # self.mesh_tree.update_bbs_mt()
        if BlendSeg.show_timing_msgs:
            seconds = time() - start
            print("  Took %1.5f seconds" % (seconds))

        print ("F")
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

        print ("G")
        # These need to be hidden/shown after the all computations
        if not sp.hide and loop1:
            loop1.select = True
        if not ap.hide and loop2:
            loop2.select = True
        if not cp.hide and loop3:
            loop3.select = True

        # bpy.context.scene.objects.active = mesh
        # mesh.select = True
        # bpy.ops.object.mode_set(mode='SCULPT')
        
        # mesh.hide = True

        print ("H")
        
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
        ix_contours = ixer.compute_intersection_with_plane(mesh,
                                                           mesh_tree,
                                                           sl_plane)
        if BlendSeg.show_timing_msgs:
            seconds = time() - start
            print("  Took %1.5f seconds" % seconds)

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
        else:
            print("Couldn't set OBJECT mode!")
            return
        bpy.ops.object.add(type='MESH')
        loop = bpy.context.object
        loop.name = loop_name
        
        for contour in contours:
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

            for idx in range(0, num_ixps - 1):
                edge = loop.data.edges[edge_start_idx + idx]
                edge.vertices = (vert_start_idx + idx, vert_start_idx + idx + 1)

            if is_closed:
                edge = loop.data.edges[-1]
                edge.vertices = (vert_start_idx + num_ixps - 1, vert_start_idx)

        return loop

def register():
    """Register Blendseg Operator with blender"""
    bpy.utils.register_class(BlendSegOperator)
    bpy.utils.register_class(BlendSegCleanupOperator)
    bpy.utils.register_class(BreakBlendSegOperator)

# For convenience, register ths when imported
register()
