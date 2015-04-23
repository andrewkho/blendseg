from time import time

import bpy
from mathutils import Vector
from mathutils import Matrix

bl_info = {
    "name": "Affine Transform Addon",
    "description": "Tools for visualizing an objects 'fit' with 3D volumetric image data",
    "blender": (2, 72, 0),
    "author": "Andrew Kenneth Ho",
    "location": "Panel",
    "category": "Operator",
}

class AffineTxPanel (bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"
    bl_label = "AffineTransform"

    def draw(self, context):
        layout = self.layout
        layout.operator(AffineTxPreOperator.bl_idname,
                             "Pre-Transform")
        layout.operator(AffineTxPostOperator.bl_idname,
                             "Post-Transform")
        try:
            layout.prop(context.object, 'name')
            row = layout.row()
            row.prop(context.object, 'affine_tx_00')
            row.prop(context.object, 'affine_tx_01')
            row.prop(context.object, 'affine_tx_02')
            row.prop(context.object, 'affine_tx_03')
            row = layout.row()
            row.prop(context.object, 'affine_tx_10')
            row.prop(context.object, 'affine_tx_11')
            row.prop(context.object, 'affine_tx_12')
            row.prop(context.object, 'affine_tx_13')
            row = layout.row()
            row.prop(context.object, 'affine_tx_20')
            row.prop(context.object, 'affine_tx_21')
            row.prop(context.object, 'affine_tx_22')
            row.prop(context.object, 'affine_tx_23')
            row = layout.row()
            row.prop(context.object, 'affine_tx_30')
            row.prop(context.object, 'affine_tx_31')
            row.prop(context.object, 'affine_tx_32')
            row.prop(context.object, 'affine_tx_33')

            layout.label("Voxel spacing")
            layout.prop(context.object, 'affine_after_voxel_spacing')
            layout.label("Image origin")
            layout.prop(context.object, 'affine_after_origin')
            
        except TypeError:
            pass

class AffineTxPreOperator (bpy.types.Operator):
    bl_idname = "object.affine_tx_pre"
    bl_label = "Pre-Transform"

    def execute(self, context):
        print("Executing...")

        # blendseg_instance needs to qualified *explicitly* 
        # the first time, otherwise a member variable is
        # created instead, masking the static class var
        ob = context.object
        image_orientation=[]

        # Apply affine transform specified by this dude's matrix
        transform = Matrix([[ob.affine_tx_00, ob.affine_tx_01, ob.affine_tx_02, ob.affine_tx_03],
                           [ob.affine_tx_10, ob.affine_tx_11, ob.affine_tx_12, ob.affine_tx_13],
                           [ob.affine_tx_20, ob.affine_tx_21, ob.affine_tx_22, ob.affine_tx_23],
                            [ob.affine_tx_30, ob.affine_tx_31, ob.affine_tx_32, ob.affine_tx_33]])
        # print ('Affine')
        # print (transform)
        transform.transpose()
        transform.invert()
        # print ('Inverse')
        # print (transform)
        print ("Applying pre-transform!")

        print (ob.affine_after_voxel_spacing)
        print (ob.affine_after_origin)
        
        for vert in ob.data.vertices:
            txd = vert.co*transform

            txd[0] = txd[0]*ob.affine_after_voxel_spacing[0] + ob.affine_after_origin[0]
            txd[1] = txd[1]*ob.affine_after_voxel_spacing[1] + ob.affine_after_origin[1]
            txd[2] = txd[2]*ob.affine_after_voxel_spacing[2] + ob.affine_after_origin[2]

            vert.co = txd

        
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        """ Only run if an object named 'Mesh' exists """
        return context.object != None

class AffineTxPostOperator (bpy.types.Operator):
    """ Cleanup the existing BlendSeg instance, if it exists.
    """
    bl_idname = "object.affine_tx_post"
    bl_label = "Post-Transform"
    
    def execute(self, context):
        ob = context.object
        transform = Matrix([[ob.affine_tx_00, ob.affine_tx_01, ob.affine_tx_02, ob.affine_tx_03],
                           [ob.affine_tx_10, ob.affine_tx_11, ob.affine_tx_12, ob.affine_tx_13],
                           [ob.affine_tx_20, ob.affine_tx_21, ob.affine_tx_22, ob.affine_tx_23],
                            [ob.affine_tx_30, ob.affine_tx_31, ob.affine_tx_32, ob.affine_tx_33]])
        transform.transpose()
        print ("Applying post-transform!")

        for vert in ob.data.vertices:
            txd = vert.co
            txd[0] = (txd[0] - ob.affine_after_origin[0])/ob.affine_after_voxel_spacing[0]
            txd[1] = (txd[1] - ob.affine_after_origin[1])/ob.affine_after_voxel_spacing[1]
            txd[2] = (txd[2] - ob.affine_after_origin[2])/ob.affine_after_voxel_spacing[2]

            txd = vert.co*transform

            vert.co = txd
        
        return {'FINISHED'}
    
    @classmethod
    def poll(cls, context):
        """ Only run if BlendSeg instance has been instantiated.
        """
        return context.object != None


def create_rna_data():
    """ Create some RNA data so blendseg can
    use a GUI. This is really fucking stupid but I don't know
    a better way to do it yet.
    """
    bpy.types.Object.affine_tx_00 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=1.)
    bpy.types.Object.affine_tx_01 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_02 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_03 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_10 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_11 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=1.)
    bpy.types.Object.affine_tx_12 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_13 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_20 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_21 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_22 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=1.)
    bpy.types.Object.affine_tx_23 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_30 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_31 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_32 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=0.)
    bpy.types.Object.affine_tx_33 = bpy.props.FloatProperty(
        name="",
        precision=6,
        default=1.)
    
    bpy.types.Object.affine_after_voxel_spacing = bpy.props.FloatVectorProperty(
        name="",
        size=3,
        subtype="XYZ",
        precision=6,
        default=tuple([1.,1.,1.]))
    bpy.types.Object.affine_after_origin = bpy.props.FloatVectorProperty(
        name="",
        size=3,
        subtype="XYZ",
        precision=6,
        default=tuple([0.,0.,0.]))

def register_operators():
    """Register Blendseg Operator with blender"""
    bpy.utils.register_class(AffineTxPreOperator)
    bpy.utils.register_class(AffineTxPostOperator)

def unregister_operators():
    bpy.utils.unregister_class(AffineTxPreOperator)
    bpy.utils.unregister_class(AffineTxPostOperator)

def register_panel():
    create_rna_data()
    bpy.utils.register_class(AffineTxPanel)

def unregister_panel():
    bpy.utils.unregister_class(AffineTxPanel)

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
