import os
import glob

from time import time

import bpy
from bpy_extras import image_utils
import imp

from . import slice_plane
imp.reload(slice_plane)
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
        start = time()
        bs = BlendSeg()
        mesh = bpy.data.objects['Mesh']
        
        bs.update_all_intersections(mesh)
        seconds = time() - start
        print("Took %1.5f seconds." % seconds)

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

    __instance = None
    def __new__(cls):

        if BlendSeg.__instance is None:
            print("Initializing BlendSeg")
            BlendSeg.__instance = super(BlendSeg, cls).__new__(cls)
            BlendSeg.__instance.load_img_stacks()
            BlendSeg.__instance.create_planes()
            
        return BlendSeg.__instance
    
    def __init__(self): pass


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
        try:
            self.mesh_qem
        except AttributeError:
            print("Generating Quad-Edge Meshes")
            start = time()
            self.sp_qem = BlenderQEMeshBuilder.construct_from_blender_object(sp)
            self.ap_qem = BlenderQEMeshBuilder.construct_from_blender_object(ap)
            self.cp_qem = BlenderQEMeshBuilder.construct_from_blender_object(cp)
            self.mesh_qem = BlenderQEMeshBuilder.construct_from_blender_object(mesh)
            seconds = time() - start
            print("Took %1.5f seconds" % seconds)

        # Call this to update matrix_world
        bpy.data.scenes[0].update()
        try:
            self.mesh_tree
        except AttributeError:
            print("Generating AABB Trees")
            start = time()
            self.sp_tree = AABBTree(self.sp_qem)
            self.ap_tree = AABBTree(self.ap_qem)
            self.cp_tree = AABBTree(self.cp_qem)
            self.mesh_tree = AABBTree(self.mesh_qem)

            # First time initialization
            self.sp_qem.update_vertex_positions()
            self.sp_qem.update_bounding_boxes()
            self.ap_qem.update_vertex_positions()
            self.ap_qem.update_bounding_boxes()
            self.cp_qem.update_vertex_positions()
            self.cp_qem.update_bounding_boxes()
            self.mesh_qem.update_vertex_positions()
            self.mesh_qem.update_bounding_boxes()

            self.sp_tree.update_bbs()
            self.ap_tree.update_bbs()
            self.cp_tree.update_bbs()
            self.mesh_tree.update_bbs()
            
            seconds = time() - start
            print("Took %1.5f seconds" % seconds)
            
        # try:
        #     self.mesh_cmesh
        # except AttributeError:
        #     print("Generating collision-mesh objects")
        #     start = time()
        #     self.sp_cmesh = object_intersection.CMesh(sp, False, False)
        #     self.ap_cmesh = object_intersection.CMesh(ap, False, False)
        #     self.cp_cmesh = object_intersection.CMesh(cp, False, False)
        #     self.mesh_cmesh = object_intersection.CMesh(mesh, False, False)
        #     seconds = time() - start
        #     print("Took %1.5f seconds" % (seconds))

        # try:
        #     self.mesh_tree
        # except AttributeError:
        #     print("Generating mesh aabb tree...")
        #     start = time()
        #     self.sp_tree = aabb_tree.AABBTree(self.sp_cmesh)
        #     self.ap_tree = aabb_tree.AABBTree(self.ap_cmesh)
        #     self.cp_tree = aabb_tree.AABBTree(self.cp_cmesh)
        #     self.mesh_tree = aabb_tree.AABBTree(self.mesh_cmesh)
        #     seconds = time() - start
        #     print("Took %1.5f seconds" % (seconds))
        #     self.mesh_stree = self.mesh_tree
        #     self.mesh_atree = self.mesh_tree
        #     self.mesh_ctree = self.mesh_tree

        # print("Generating Directional AABB Trees...")
        # start = time()
        # self.sp_tree = aabb_tree.AABBTree(self.sp_cmesh)
        # self.ap_tree = aabb_tree.AABBTree(self.ap_cmesh)
        # self.cp_tree = aabb_tree.AABBTree(self.cp_cmesh)
        # mesh_stree = aabb_directional_tree.AABBDirectionalTree(
        #     self.mesh_cmesh, slice_plane.Orientation('SAGITTAL').__index__())
        # mesh_atree = aabb_directional_tree.AABBDirectionalTree(
        #     self.mesh_cmesh, slice_plane.Orientation('AXIAL').__index__())
        # mesh_ctree = aabb_directional_tree.AABBDirectionalTree(
        #     self.mesh_cmesh, slice_plane.Orientation('CORONAL').__index__())
        # seconds = time() - start
        # print("Took %1.5f seconds" % (seconds))

        print("  Refreshing vertex positions")
        start = time()
        self.sp_qem.update_vertex_positions()
        self.ap_qem.update_vertex_positions()
        self.cp_qem.update_vertex_positions()
        if mesh.is_updated:
            self.mesh_qem.update_vertex_positions()
        seconds = time() - start
        print("  Took %1.5f seconds" % (seconds))

        print("  Refreshing bounding box positions")
        start = time()
        self.sp_qem.update_bounding_boxes()
        self.ap_qem.update_bounding_boxes()
        self.cp_qem.update_bounding_boxes()
        if mesh.is_updated:
            self.mesh_qem.update_bounding_boxes()
        seconds = time() - start
        print("  Took %1.5f seconds" % (seconds))
        
        print("  DEBUG: refreshing aabb trees to see how fast...")
        start = time()
        self.sp_tree.update_bbs()
        self.ap_tree.update_bbs()
        self.cp_tree.update_bbs()
        if mesh.is_updated:
            self.mesh_tree.update_bbs()
        seconds = time() - start
        print("  Took %1.5f seconds" % (seconds))

        if (not sp.hide):
            print("Computing sagittal intersection...")
            start = time()
            #self.mesh_cmesh.reset_edges_found_lists()
            # loop1 = self.compute_intersection(
            #     bpy.context.scene, self.sp_cmesh, self.mesh_cmesh,
            #     self.sp_tree, self.mesh_stree,
            #     self.sag_plane.orientation, sp.location[self.sag_plane.orientation],
            #     self.sag_plane.loop_name)
            loop1 = self.compute_intersection_qem(bpy.context.scene, self.sp_qem, self.mesh_qem,
                                                  self.sp_tree, self.mesh_tree,
                                                  self.sag_plane.loop_name)
            seconds = time() - start
            print("Took %1.5f seconds" % (seconds))
        if (not ap.hide):
            print("Computing axial intersection...")
            start = time()
            #self.mesh_cmesh.reset_edges_found_lists()
            # loop2 = self.compute_intersection(
            #     bpy.context.scene, self.ap_cmesh, self.mesh_cmesh,
            #     self.ap_tree, self.mesh_atree,
            #     self.axi_plane.orientation, ap.location[self.axi_plane.orientation],
            #     self.axi_plane.loop_name)
            loop2 = self.compute_intersection_qem(bpy.context.scene, self.ap_qem, self.mesh_qem,
                                                  self.ap_tree, self.mesh_tree,
                                                  self.axi_plane.loop_name)
            seconds = time() - start
            print("Took %1.5f seconds" % (seconds))
        if (not cp.hide):
            print("Computing coronal intersection...")
            start = time()
            #self.mesh_cmesh.reset_edges_found_lists()
            # loop3 = self.compute_intersection(
            #     bpy.context.scene, self.cp_cmesh, self.mesh_cmesh,
            #     self.cp_tree, self.mesh_ctree,
            #     self.cor_plane.orientation, cp.location[self.cor_plane.orientation],
            #     self.cor_plane.loop_name)
            loop3 = self.compute_intersection_qem(bpy.context.scene, self.cp_qem, self.mesh_qem,
                                                  self.cp_tree, self.mesh_tree,
                                                  self.cor_plane.loop_name)
            seconds = time() - start
            print("  Took %1.5f seconds" % (seconds))
        # These need to be hidden/shown after the all computations
        if (not sp.hide and loop1):
            loop1.select = True
        if (not ap.hide and loop2):
            loop2.select = True
        if (not cp.hide and loop3):
            loop3.select = True

        bpy.data.scenes[0].update()

        bpy.context.scene.objects.active = mesh
        #bpy.ops.object.mode_set(mode='SCULPT')
        
        mesh.hide = True

    def compute_intersection_qem (self, scene, plane, mesh, plane_tree, mesh_tree, loop_name):
        """ Compute intersection of plane and mesh and return a contour representing
        their intersection.
        """
        # Try to remove old loop before anything else
        try:
            loop = scene.objects[loop_name]
        except KeyError:
            print("Couldn't find old loop! Continuing")
        else:
            scene.objects.unlink(loop)
            bpy.data.objects.remove(loop)
            
        ixer = Intersector()
        ix_contours = ixer.compute_intersection_contour(plane, mesh, plane_tree, mesh_tree)
        loop = self._create_blender_contour(ix_contours, loop_name)

        return loop

    def _create_blender_contour (self, contours, loop_name):
        """ Create a blender object representing one or more contours.

        loop_name - name of the new blender object
        contour - A list of IntersectionPoints representing the contour
        """
        if len(contours) == 0:
            return None
        
        # Create a new object to hold the contours
        if (bpy.ops.object.mode_set.poll()):
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.add(type='MESH')
        loop = bpy.context.object
        loop.name = loop_name

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

        loop.data.update()
        
        return loop
        
    def compute_intersection (self, scene, plane, mesh,
                              plane_tree, mesh_tree, dirn, divide, loop_name):
        """ Computes intersection of two CMesh's
        
        Returns an object representing the intersection contour.
        """
        if (mesh == None or plane == None):
            raise ValueError('mesh or plane is None!')

        # print("Computing crs points...")
        # start = time()
        """ Original Brute force method """
        # crs_pnts = object_intersection.intersect(plane, mesh)
        """ Intersect two trees """ 
        crs_pnts = object_intersection.intersect_aabb(plane, mesh, plane_tree, mesh_tree)
        """ Brute force method with single division line """
        # crs_pnts = object_intersection.intersect_split(plane, mesh, dirn, divide)
        # seconds = time() - start
        # print("Took %1.5f seconds" % (seconds))


        """ attempt to find our old loop and delete if exists """
        try:
            loop = scene.objects[loop_name]
        except KeyError:
            print("Couldn't find old loop! Continuing")
        else:
            scene.objects.unlink(loop)
            bpy.data.objects.remove(loop)

        """ create a new loop object """
        if (bpy.ops.object.mode_set.poll()):
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.add(type='MESH')
        loop = bpy.context.object
        loop.name = loop_name

        # print("Computing loop...")
        # start = time()
        # add vertices to self plane?
        print("  Found " + str(len(crs_pnts)) + " loops")
        for l in crs_pnts:
            object_intersection.create(l, loop, allEdges=True)
                
        # we must set the mode to edit before points can be selected
        # if crs_pnts: #any other method of unselecting did not work here: 
        #     oldactive = scene.objects.active
        #     scene.objects.active = bpy.data.objects[loop_name]
        #     #bpy.ops.object.mode_set(mode='EDIT')#bpy.ops.object.editmode_toggle()
        #     #bpy.ops.mesh.select_all(action='DESELECT')
        #     bpy.ops.object.mode_set(mode='OBJECT')#bpy.ops.object.editmode_toggle()
        #     #bpy.context.scene.objects.active = oldactive

        # seconds = time()-start
        # print("Took %1.5f seconds" % seconds)
        
        #select the newly created vertices:
        # found = 0
        # for v in loop.data.vertices: 
        #      found += 1
        #      v.select = True
        # print ("found " + str(found) + " vertices to select")
                
        #enter edit mode (to let the user to evaluate the results):
        #bpy.ops.object.mode_set(mode='EDIT')#bpy.ops.object.editmode_toggle()
            
        if not crs_pnts:
            print ("No intersection found between this and the other selected object.")

        return loop

def register():
    """Register Blendseg Operator with blender"""
    bpy.utils.register_class(BlendSegOperator)

# For convenience, register ths when imported
register()
