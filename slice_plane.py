import os
import imp
import bpy
from math import pi
from mathutils import Vector
import object_intersection
from time import time

class Orientation (object):
    """ An orientation which may be 'AXIAL', 'SAGITTAL', or 'CORONAL'.

    Set an orientation by eg) orientation = Orientation('AXIAL').
    Orientation can be printed with str(), and can be used to index an array.
    
    This class is an immutable singleton. Singleton-ness is enforced
    by overriding __new__. Immutability of the orientation property
    is enforced by property()."""

    _instances = dict()
    def __new__ (cls, dirn):
        if (dirn is not 'AXIAL' and
            dirn is not 'SAGITTAL' and
            dirn is not 'CORONAL'):
            raise NameException("dirn must be AXIAL, SAGITThAL, or CORONAL")

        if dirn in Orientation._instances:
            return Orientation._instances[dirn]
        else:
            return super(Orientation, cls).__new__(cls)

    def __init__ (self, dirn):
        if dirn not in Orientation._instances:
            print('Instantiating ' + dirn)
            self._orientation = dirn
            Orientation._instances[dirn] = self
        
    def __str__ (self):
        return self._orientation

    def __index__(self):
        if self._orientation == 'SAGITTAL':
            return 0
        elif self._orientation == 'CORONAL':
            return 1
        elif self._orientation == 'AXIAL':
            return 2

    def _get_orientation (self):
        return self.__orientation

    def _set_orientation (self, value):
        try:
            self.__orientation
        except AttributeError:
            self.__orientation = value
        else:
            raise ValueError('Cant do this')

    _orientation = property (_get_orientation, _set_orientation)



class SlicePlane (object):
    """ A plane with orthogonal direction Orientation.(AXIAL|SAGITTAL|CORONAL)

    This plane is constrained to translate along it's principle direction.
    It will update the image which it displays in real time according to
    the origin, spacing, and will update using the given image_names.

    Also can computes the intersection of itself with another mesh. 

    A word of warning: This relies on object/image/mesh/texture/material NAME
    lookups in order to work properly. This is because Blender invalidates
    memory objects on Undo/Redo.
    """

    def __init__ (self, orientation, origin, image_names, spacing):
        """ Constructor for the SlicePlane.
        
        orientation - string that must be one of 'AXIAL', 'SAGITTAL', 'CORONAL'
        origin - 3-tuple of floats indicating the origin of the 3D image
        image_names - list of image names (strings) associated with this plane.
        spacing - 3-tuple of floats indicating the pixel spacing x, y, z
        """

        self.x_vtx_offset = -1
        self.use_transparency=False
        self.orientation = orientation
        self.origin = origin
        self.img_names = image_names
        self.spacing = spacing
        
        if (self.orientation == Orientation('AXIAL')):
            #self.plane_name = 'PlaneAxi'
            self.loop_name = 'loopAxi'
        elif (self.orientation == Orientation('SAGITTAL')):
            #self.plane_name = 'PlaneSag'
            self.loop_name = 'loopSag'
        elif (self.orientation == Orientation('CORONAL')):
            #self.plane_name = 'PlaneCor'
            self.loop_name = 'loopCor'
        else:
            raise ValueError("WHy isn't it OrientatioN?")


        self.plane_name = str(self.orientation)
            
        plane = self.create_plane()
        self.update_image(plane)

    # def set_mesh (self, a_mesh):
    #     self.mesh = a_mesh

    def update_intersection (self, scene, mesh):
        """ Computes intersection of this plane with the given mesh.
        Returns an object representing the intersection contour.
        """
        if (mesh == None):
            raise ValueError('mesh is None!')

        """ attempt to find our plane """
        try:
            plane = scene.objects[self.plane_name]
        except KeyError:
            print("Couldn't find " + self.plane_name + "! Abort intersection")
            return

        print("Generating collision-mesh objects")
        start = time()
        A = object_intersection.CMesh(plane,False,False)
        B = object_intersection.CMesh(mesh,False,False)
        seconds = time() - start
        print("Took %1.5f seconds" % (seconds))

        print ("Updating intersection for " + self.plane_name + "...")
        start = time()
        crs_pnts = object_intersection.intersect (A,B)
        seconds = time() - start
        print("In %1.5f seconds created: %d edges, found: %d raw cross points" %
              (seconds, len(A._CMesh__edges), len(crs_pnts)))

        """ attempt to find our old loop and delete if exists """
        try:
            loop = scene.objects[self.loop_name]
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
        loop.name = self.loop_name

        # add vertices to self plane
        self.use_diagonals = False
        for l in crs_pnts:
            object_intersection.create(l, loop, self.use_diagonals)
                
        # we must set the mode to edit before points can be selected
        if crs_pnts: #any other method of unselecting did not work here: 
            oldactive = scene.objects.active
            scene.objects.active = bpy.data.objects[self.loop_name]
            #bpy.ops.object.mode_set(mode='EDIT')#bpy.ops.object.editmode_toggle()
            #bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')#bpy.ops.object.editmode_toggle()
            #bpy.context.scene.objects.active = oldactive
                
        #select the newly created vertices:
        found = 0
        for v in loop.data.vertices: 
             found += 1
             v.select = True
        print ("found " + str(found) + " vertices to select\n")
                
        #enter edit mode (to let the user to evaluate the results):
        #bpy.ops.object.mode_set(mode='EDIT')#bpy.ops.object.editmode_toggle()
            
        if not crs_pnts:
            print ("No intersection found between this and the other selected object.")

        return loop

    def enforce_location (self, plane):
        """ This method modifies the position of the given plane object
        in order to constrain it to move only along it's normal axis.
        """
        newloc = Vector(self.origin)
        newloc[self.orientation] = plane.location[self.orientation]

        plane.location = newloc

    def update_image (self, plane):
        """ Update the image that the given plane object displays.

        The new image is based on the location.
        """
        img = self.get_image_from_location (plane.location)
        if (img != None):
            plane.data.uv_textures[0].data[0].image = img
        else:
            raise ValueException("Couldn't find image!")
        plane.data.update()

    def get_image_from_location (self, loc):
        """ Given a location, return the image object that this
        plane should be showing.
        """
        if (len(self.img_names) == 0):
            return None

        left = self.origin[self.orientation] - (len(self.img_names) *
                                                self.spacing[self.orientation])/2

        pos = loc[self.orientation] - left
        idx = int(pos / self.spacing[self.orientation])

        if (idx < 0): 
            idx = 0
        if (idx >= len(self.img_names)):
            idx = len(self.img_names) - 1

        idx = -idx
        if (self.orientation == Orientation('SAGITTAL')):
            idx = -idx

        try:
            img = bpy.data.images[self.img_names[idx]]
        except KeyError:
            print("Couldn't find image " + self.img_names[idx] + "!")
            return None
            
        return img

    def move_callback(self, scene):
        """ Callback method which checks if my plane has moved,
        and if so, updates the image.

        Also constrains movement along primary axis dir'n.
        """
        
        try:
            plane = scene.objects[self.plane_name]
        except KeyError:
            print(self.plane_name + " wasn't found!")
        
        if plane.is_updated:
            self.enforce_location(plane)
            self.update_image(plane)

    def register_callback(self):
        """ Register callback with blender handler. """
        bpy.app.handlers.scene_update_pre.append (self.move_callback)

    @classmethod
    def add_obj(cls, mesh, context):
        """ Create a new blender object based on mesh.

        Adds to scene and links.
        """
        scene = context.scene
        obj_new = bpy.data.objects.new(mesh.name, mesh)
        base = scene.objects.link(obj_new)
        return obj_new, base
    
    @classmethod
    def bl_make_plane(cls, name):
        """ Return a new blender plane object.

        Centered on 0,0,0 and size 2x2 normal +z direction.
        """
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
                     
        meshplane = bpy.data.meshes.new(name)
        meshplane.from_pydata(verts, edges, faces)
        obj, base = SlicePlane.add_obj(meshplane, bpy.context)

        obj.location = Vector((0.,0.,0.))

        return obj # or is base the correct one?

    def create_plane (self):
        """ Return a blender plane.
        
        Checks if one already exists since we probably don't want more than
        one plane for each direction at a time.
        If not, create a new plane, orient it based on self.orientation,
        create textures and materials and bind to plane before returning.
        """

        if self.plane_name in bpy.data.objects:
            return bpy.data.objects[self.plane_name]
        
        """Create a mesh and add it to Blender"""
        if (len(self.img_names) == 0):
            raise ValueError("No images! Something is wrong")
        
        idx = len(self.img_names) - 1
        img_name = self.img_names[idx//2]
        try:
            img = bpy.data.images[img_name]
        except KeyError:
            print("Couldn't find image " + img_name + "!")
            return
        
        self.widthp,self.heightp = img.size
        
        """ Make a plane mesh and add to blender """
        plane = SlicePlane.bl_make_plane(str(self.orientation))

        bpy.ops.object.transform_apply(rotation=True,scale=True)
        if (self.orientation == Orientation('AXIAL')):
            self.widthf = self.widthp*self.spacing[0]
            self.heightf = self.heightp*self.spacing[1]
            plane.dimensions = self.widthf, self.heightf, 0.0

            plane.rotation_mode = 'XYZ'
            plane.rotation_euler = [0.,0.,pi]
        elif (self.orientation == Orientation('SAGITTAL')):
            self.widthf = self.widthp*self.spacing[1]
            self.heightf = self.heightp*self.spacing[2]
            plane.dimensions = self.widthf, self.heightf, 0.0

            plane.rotation_mode = 'ZYX'
            plane.rotation_euler = [0.,-pi/2,pi/2]
        elif (self.orientation == Orientation('CORONAL')):
            self.widthf = self.widthp*self.spacing[0]
            self.heightf = self.heightp*self.spacing[2]
            plane.dimensions = self.widthf, self.heightf, 0.0

            plane.rotation_mode = 'XYZ'
            plane.rotation_euler = [-pi/2,0.,pi]
        else:
            raise ValueError('orientation must be in Orientation')

        img = self.get_image_from_location (plane.location)
        tex = SlicePlane.create_image_texture (img)
        mat = self.create_material_for_texture (tex)

        plane.data.materials.append(mat)
        plane.data.uv_textures.new()
        plane.data.uv_textures[0].data[0].image = \
            mat.texture_slots[0].texture.image

        plane.location = Vector (self.origin)

        self.register_callback()

        return plane


    @classmethod
    def create_image_texture(cls, image):
        fn_full = os.path.normpath(bpy.path.abspath(image.filepath))

        # look for texture with importsettings
        # we shouldn't find one!
        for texture in bpy.data.textures:
            if texture.type == 'IMAGE':
                tex_img = texture.image
                if (tex_img is not None) and (tex_img.library is None):
                    fn_tex_full = os.path.normpath(bpy.path.abspath(tex_img.filepath))
                    #assert (fn_full != fn_tex_full)
                    if (fn_full == fn_tex_full): 
                       return texture

        # if no texture is found: create one
        name_compat = bpy.path.display_name_from_filepath(image.filepath)
        texture = bpy.data.textures.new(name=name_compat, type='IMAGE')
        texture.image = image
        return texture

    def create_material_for_texture(self, texture):
        # look for material with the needed texture
        # for material in bpy.data.materials:
        #     slot = material.texture_slots[0]
        #     if slot.texture == texture:
        #         return material

        mat_name = str(self.orientation) + "mat"
        try:
            material = bpy.data.materials[mat_name]
        except KeyError:
            # create a material
            material = bpy.data.materials.new(name=mat_name)
            slot = material.texture_slots.add()
            slot.texture = texture
            slot.texture_coords = 'UV'
        
            material.use_shadeless = True
            material.game_settings.use_backface_culling = False
        
        return material

    # ---------------------------------------
    # self.orientation property must be an instance of class Orientation
    # and may not be changed once it is set
    
    def _get_orientation (self):
        return self.__orientation
    def _set_orientation (self, value):
        try:
            self.__orientation
        except AttributeError:
            self.__orientation = Orientation(value)
        else:
            raise ValueError('Cant do this')

    orientation = property (_get_orientation, _set_orientation)

