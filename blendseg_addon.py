from time import time

import bpy
from mathutils import Vector

from blendseg.blendseg import BlendSeg

bl_info = {
    "name": "Blendseg Addon",
    "description": "Tools for visualizing an objects 'fit' with 3D volumetric image data",
    "blender": (2, 72, 0),
    "author": "Andrew Kenneth Ho",
    "location": "Panel",
    "category": "Operator",
}

# class BlendSegPrefs (bpy.types.AddonPref):
#     """ This class holds the preferences for BlendSeg.

#     Includes required vars for operation eg image directories.
#     """
#     bl_idname = __name__
    
#     mesh_name = "Mesh"
#     # mesh_name = bpy.props.StringProperty(name="Mesh Name", default="Mesh")
    
#     # ugly, but temporary
#     letter = "A"
#     image_dir = "/home/andrew/workspace/imageBlowup/"+letter+"tiff/"
#     image_ext = "*.tif"
#     axi_prefix = "axial/"+letter+"axi"
#     sag_prefix = "sagittal/"+letter+"sag"
#     cor_prefix = "coronal/"+letter+"cor"

#     image_origin = tuple([0.,21.5,-51])
#     image_spacing = tuple([0.468,0.468,0.5])
#     show_timing_msgs = False

#     # def draw(self,context):
#     #     layout = self.layout
#     #     layout.label(text="This is a preferences view for Blendseg")
#     #     layout.prop(self,"mesh_name")

class BlendSegPanel (bpy.types.Panel):
    # bl_space_type = "VIEW_3D"
    # bl_region_type = "UI"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"
    bl_label = "BlendSeg"

    def draw(self, context):
        layout = self.layout
        layout.operator(BlendSegOperator.bl_idname,
                             "Start BlendSeg")
        layout.operator(BlendSegCleanupOperator.bl_idname,
                             "Stop BlendSeg")
        if BlendSegOperator.blendseg_instance is not None:
            return
        try:
            layout.prop(context.object, 'name')
            layout.prop(context.object, 'blendseg_matrix_not_identity')
            layout.prop(context.object, 'blendseg_image_origin')
            layout.prop(context.object, 'blendseg_path')
            layout.prop(context.object, 'blendseg_axi_prefix')
            layout.prop(context.object, 'blendseg_sag_prefix')
            layout.prop(context.object, 'blendseg_cor_prefix')
            layout.prop(context.object, 'blendseg_image_ext')
            layout.prop(context.object, 'blendseg_image_spacing')
            layout.prop(context.object, 'blendseg_show_timing_msgs')
        except TypeError:
            pass

class BlendSegOperator (bpy.types.Operator):
    bl_idname = "object.blendseg"
    bl_label = "Blendseg Operator"

    blendseg_instance = None
    number2 = bpy.props.IntProperty(name="number2", default=10)
    def execute(self, context):
        print("Executing...")
        addon_prefs = context.user_preferences.addons[__name__].preferences
        
        # Save cursor position and move to origin
        # This will fix the position of the contours in Blender v2.68
        old_position = Vector(context.scene.cursor_location)
        context.scene.cursor_location = Vector((0., 0., 0.))
        start = time()

        # blendseg_instance needs to qualified *explicitly* 
        # the first time, otherwise a member variable is
        # created instead, masking the static class var
        ob = context.object
        BlendSegOperator.blendseg_instance = BlendSeg(
            ob.name,
            ob.blendseg_matrix_not_identity,
            ob.blendseg_path,
            ob.blendseg_image_ext,
            ob.blendseg_axi_prefix,
            ob.blendseg_sag_prefix,
            ob.blendseg_cor_prefix,
            ob.blendseg_image_origin,
            ob.blendseg_image_spacing,
            ob.blendseg_show_timing_msgs)
        mesh = bpy.data.objects[ob.name]

        self.blendseg_instance.is_updating = True
        self.blendseg_instance.update_all_intersections(mesh)
        self.blendseg_instance.is_updating = False
        
        seconds = time() - start
        print("Took %1.5f seconds." % seconds)

        # Return cursor position to where it was before calling execute
        context.scene.cursor_location = old_position
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        # print (BlendSegPrefs.mesh_name)
        """ Only run if an object named 'Mesh' exists """
        # return (BlendSegPanel.mesh_name[1]['default'] in bpy.data.objects and
        #         context.mode == 'OBJECT' and
        #         cls.blendseg_instance == None)
        return (cls.blendseg_instance == None and context.object != None)

class BlendSegCleanupOperator (bpy.types.Operator):
    """ Cleanup the existing BlendSeg instance, if it exists.
    """
    bl_idname = "object.cleanblendseg"
    bl_label = "Cleanup BlendSeg"
    
    def execute(self, context):
        """ Cleanup the existing BlendSeg instance.
        """
        try:
            mesh = bpy.data.objects[
                BlendSegOperator.blendseg_instance.blender_mesh_name]
        except KeyError:
            print("Couldn't find mesh when running operator: " +
                  BlendSegOperator.blendseg_instance.blender_mesh_name)
            return {'FINISHED'}
        
        bpy.context.scene.objects.active = None
        mesh.select = False
        mesh.hide = False
        
        print ("Cleaning up BlendSeg!")
        BlendSegOperator.blendseg_instance.remove_and_cleanup()
        BlendSegOperator.blendseg_instance = None
        return {'FINISHED'}
    
    @classmethod
    def poll(cls, context):
        """ Only run if BlendSeg instance has been instantiated.
        """
        return BlendSegOperator.blendseg_instance != None


def create_rna_data():
    """ Create some RNA data so blendseg can
    use a GUI. This is really fucking stupid but I don't know
    a better way to do it yet.
    """
    bpy.types.Object.blendseg_matrix_not_identity = bpy.props.BoolProperty(
        name="Use World Coordinates (slow)",
        default=False)
    bpy.types.Object.blendseg_path = bpy.props.StringProperty(
        name="Path",
        default="/home/andrew/workspace/SequenceB/imageBlowup/frame00/",
        subtype="DIR_PATH")
    bpy.types.Object.blendseg_image_ext = bpy.props.StringProperty(
        name="Image Extension",
        default="*.tif")
    bpy.types.Object.blendseg_axi_prefix = bpy.props.StringProperty(
        name="axial prefix",
        default="axial/")
    bpy.types.Object.blendseg_sag_prefix = bpy.props.StringProperty(
        name="sagittal prefix",
        default="sagittal/")
    bpy.types.Object.blendseg_cor_prefix = bpy.props.StringProperty(
        name="coronal prefix",
        default="coronal/")
    bpy.types.Object.blendseg_image_origin = bpy.props.FloatVectorProperty(
        name="Image origin",
        size=3,
        subtype="XYZ",
        default=tuple([0.,21.5,-51]))
    bpy.types.Object.blendseg_image_spacing = bpy.props.FloatVectorProperty(
        name="Image spacing",
        size=3,
        subtype="XYZ",
        default=tuple([0.468,0.468,0.5]))
    bpy.types.Object.blendseg_show_timing_msgs = bpy.props.BoolProperty(
        name="print timing (debug)",
        default=False)

def register_operators():
    """Register Blendseg Operator with blender"""
    bpy.utils.register_class(BlendSegOperator)
    bpy.utils.register_class(BlendSegCleanupOperator)
    # bpy.utils.register_class(BlendSegPrefs)

def unregister_operators():
    bpy.utils.unregister_class(BlendSegOperator)
    bpy.utils.unregister_class(BlendSegCleanupOperator)
    # bpy.utils.unregister_class(BlendSegPrefs)

def register_panel():
    create_rna_data()
    bpy.utils.register_class(BlendSegPanel)

def unregister_panel():
    bpy.utils.unregister_class(BlendSegPanel)

def register():
    register_operators()
    register_panel()
    # bpy.utils.register_module(__name__)
    
def unregister():
    unregister_operators()
    unregister_panel()
    # bpy.utils.unregister_module(__name__)
    

if __name__ == "__main__":
    register()
