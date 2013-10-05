import os
import glob

from time import time

import bpy
from bpy_extras import image_utils
import imp

import slice_plane
imp.reload(slice_plane)
import object_intersection
imp.reload(object_intersection)
import aabb_tree
imp.reload(aabb_tree)

class BlendSeg (bpy.types.Operator):
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
    bl_idname = "object.blendseg"
    bl_label = "Blendseg Operator"
    
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

    def execute(self, context):
        print("\nBlendseg is executing!")

        mesh = bpy.data.objects['Mesh']
        self.update_all_intersections(mesh)
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        """ Only run if an object named 'Mesh' exists """
        return 'Mesh' in bpy.data.objects
        
    def __init__(self):
        print("Initializing BlendSeg...")
        start = time()
        self.load_img_stacks()
        self.create_planes()
        end = time()
        print("took " + str(end-start) + " seconds")

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
            self.mesh_cmesh
        except AttributeError:
            print("Generating collision-mesh objects")
            start = time()
            self.sp_cmesh = object_intersection.CMesh(sp, False, False)
            self.ap_cmesh = object_intersection.CMesh(ap, False, False)
            self.cp_cmesh = object_intersection.CMesh(cp, False, False)
            self.mesh_cmesh = object_intersection.CMesh(mesh, False, False)
            seconds = time() - start
            print("Took %1.5f seconds" % (seconds))

        print("Generating mesh aabb tree...")
        start = time()
        sp_tree = aabb_tree.AABBTree(self.sp_cmesh)
        ap_tree = aabb_tree.AABBTree(self.ap_cmesh)
        cp_tree = aabb_tree.AABBTree(self.cp_cmesh)
        mesh_tree = aabb_tree.AABBTree(self.mesh_cmesh)
        seconds = time() - start
        print("Took %1.5f seconds" % (seconds))

        print("DEBUG: refreshing aabb trees to see how fast...")
        start = time()
        sp_tree.update_bbs()
        ap_tree.update_bbs()
        cp_tree.update_bbs()
        seconds = time() - start
        print("Took %1.5f seconds" % (seconds))

        if (not sp.hide):
            print("Computing sagittal intersection...")
            start = time()
            loop1 = self.compute_intersection(
                bpy.context.scene, self.sp_cmesh, self.mesh_cmesh, sp_tree, mesh_tree,
                self.sag_plane.orientation, sp.location[self.sag_plane.orientation],
                self.sag_plane.loop_name)
            seconds = time() - start
            print("Took %1.5f seconds" % (seconds))
        if (not ap.hide):
            print("Computing axial intersection...")
            start = time()
            loop2 = self.compute_intersection(
                bpy.context.scene, self.ap_cmesh, self.mesh_cmesh, ap_tree, mesh_tree,
                self.axi_plane.orientation, ap.location[self.axi_plane.orientation],
                self.axi_plane.loop_name)
            seconds = time() - start
            print("Took %1.5f seconds" % (seconds))
        if (not cp.hide):
            print("Computing coronal intersection...")
            start = time()
            loop3 = self.compute_intersection(
                bpy.context.scene, self.cp_cmesh, self.mesh_cmesh, cp_tree, mesh_tree,
                self.cor_plane.orientation, cp.location[self.cor_plane.orientation],
                self.cor_plane.loop_name)
            seconds = time() - start
            print("  Took %1.5f seconds" % (seconds))
            
        """ These need to be hidden/shown after the all computations """
        if (not sp.hide):
            loop1.select = True
        if (not ap.hide):
            loop2.select = True
        if (not cp.hide):
            loop3.select = True

        bpy.context.scene.objects.active = mesh
        #bpy.ops.object.mode_set(mode='SCULPT')
        
        mesh.hide = True

    def update_axi_intersections (self):
        bpy.context.scene.objects.active = self.mesh
        self.mesh.hide = False
        self.axi_plane.update_intersection()
        self.axi_plane.loop.select = True
        self.sag_plane.loop.select = False
        self.cor_plane.loop.select = False

        bpy.context.scene.objects.active = self.mesh
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='SCULPT')
        self.axi_plane.plane.hide = False
        self.sag_plane.plane.hide = True
        self.cor_plane.plane.hide = True
        self.mesh.hide = True

    def update_sag_intersections (self):
        bpy.context.scene.objects.active = self.mesh
        self.mesh.hide = False
        self.sag_plane.update_intersection()
        self.axi_plane.loop.select = False
        self.sag_plane.loop.select = True
        self.cor_plane.loop.select = False

        bpy.context.scene.objects.active = self.mesh
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='SCULPT')
        self.axi_plane.plane.hide = True
        self.sag_plane.plane.hide = False
        self.cor_plane.plane.hide = True
        self.mesh.hide = True
        
    def update_cor_intersections (self):
        bpy.context.scene.objects.active = self.mesh
        self.mesh.hide = False
        self.cor_plane.update_intersection()
        self.axi_plane.loop.select = False
        self.sag_plane.loop.select = False
        self.cor_plane.loop.select = True

        bpy.context.scene.objects.active = self.mesh
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='SCULPT')
        self.axi_plane.plane.hide = True
        self.sag_plane.plane.hide = True
        self.cor_plane.plane.hide = False
        self.mesh.hide = True
        
    #def compute_intersection (self, scene, plane, mesh, dirn, divide, loop_name):
    def compute_intersection (self, scene, plane, mesh, plane_tree, mesh_tree, dirn, divide, loop_name):
        """ Computes intersection of two CMesh's
        
        Returns an object representing the intersection contour.
        """
        if (mesh == None or plane == None):
            raise ValueError('mesh or plane is None!')

        # print("Computing crs points...")
        # start = time()
        # crs_pnts = object_intersection.intersect(plane, mesh)
        crs_pnts = object_intersection.intersect_aabb(plane, mesh, plane_tree, mesh_tree)
        # crs_pnts = object_intersection.intersect_aabb(plane, mesh, plane_tree)
        # crs_pnts = object_intersection.intersect_aabb(mesh, plane, mesh_tree)
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
        # add vertices to self plane
        self.use_diagonals = False
        for l in crs_pnts:
            object_intersection.create(l, loop, self.use_diagonals)
                
        # we must set the mode to edit before points can be selected
        if crs_pnts: #any other method of unselecting did not work here: 
            oldactive = scene.objects.active
            scene.objects.active = bpy.data.objects[loop_name]
            #bpy.ops.object.mode_set(mode='EDIT')#bpy.ops.object.editmode_toggle()
            #bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')#bpy.ops.object.editmode_toggle()
            #bpy.context.scene.objects.active = oldactive

        # seconds = time()-start
        # print("Took %1.5f seconds" % seconds)
        
        #select the newly created vertices:
        found = 0
        for v in loop.data.vertices: 
             found += 1
             v.select = True
        print ("found " + str(found) + " vertices to select")
                
        #enter edit mode (to let the user to evaluate the results):
        #bpy.ops.object.mode_set(mode='EDIT')#bpy.ops.object.editmode_toggle()
            
        if not crs_pnts:
            print ("No intersection found between this and the other selected object.")

        return loop

# callback for updating plane images
# We need to try-except each call so that if one is deleted,
# we can continue to run
"""        
def update_plane_images (scene):
    if (BlendSeg == None):
        return
    bs = BlendSeg.get_instance()
    if (not bs):
        return
    try:
        if scene.objects[bs.axi_plane.plane_name].is_updated:
            #print ("AxiPlane updated")
            if (bs.axi_plane.plane != scene.objects[bs.axi_plane.plane_name]):
                bs.axi_plane.plane = scene.objects[bs.axi_plane.plane_name]
            bs.axi_plane.enforce_location()
            bs.axi_plane.update_image()
    except (KeyError, AttributeError):
        #print ("exception caught!")
        pass
    try:
        if scene.objects[bs.sag_plane.plane_name].is_updated:
            #print ("SagPlane updated")
            if (bs.sag_plane.plane != scene.objects[bs.sag_plane.plane_name]):
                bs.sag_plane.plane = scene.objects[bs.sag_plane.plane_name]
            bs.sag_plane.enforce_location()
            bs.sag_plane.update_image()
    except (KeyError, AttributeError):
        #print ("exception caught!")
        pass
    try:
        if scene.objects[bs.cor_plane.plane_name].is_updated:
            #print ("CorPlane updated")
            if (bs.cor_plane.plane != scene.objects[bs.cor_plane.plane_name]):
                bs.cor_plane.plane = scene.objects[bs.cor_plane.plane_name]
            bs.cor_plane.enforce_location()
            bs.cor_plane.update_image()
    except (KeyError, AttributeError):
        #print ("exception caught!")
        pass
"""  

# Some convenience methods for changing visibility and modes
def show_planes ():
    bs = BlendSeg.get_instance()
    bs.axi_plane.plane.hide = False
    bs.sag_plane.plane.hide = False
    bs.cor_plane.plane.hide = False
    bs.mesh.hide = True
    bs.axi_plane.loop.hide = False
    bs.sag_plane.loop.hide = False
    bs.cor_plane.loop.hide = False
    bs.axi_plane.loop.select = True
    bs.sag_plane.loop.select = True
    bs.cor_plane.loop.select = True
    
def iso_axi ():
    """Hide everything except the mesh and the axial plane.
    """
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    bs = BlendSeg.get_instance()
    bs.axi_plane.plane.hide = False
    bs.sag_plane.plane.hide = True
    bs.cor_plane.plane.hide = True
    bs.mesh.hide = False

    bpy.context.scene.objects.active = bs.mesh
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='SCULPT')

def iso_sag ():
    """Hide everything except the mesh and the sagittal plane.
    """
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    bs = BlendSeg.get_instance()
    bs.axi_plane.plane.hide = True
    bs.sag_plane.plane.hide = False
    bs.cor_plane.plane.hide = True
    bs.mesh.hide = False

    bpy.context.scene.objects.active = bs.mesh
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='SCULPT')

def iso_cor ():
    """Hide everything except the mesh and the coronal plane.
    """
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    bs = BlendSeg.get_instance()
    bs.axi_plane.plane.hide = True
    bs.sag_plane.plane.hide = True
    bs.cor_plane.plane.hide = False
    bs.mesh.hide = False

    bpy.context.scene.objects.active = bs.mesh
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='SCULPT')

def register():
    """Register Blendseg Operator with blender"""
    bpy.utils.register_class(BlendSeg)

# For convenience, register ths when imported
register()
