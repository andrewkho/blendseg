import bpy
# from .blendseg import BlendSeg

# def fget(self):
#     """Distance from origin"""
#     loc = self.location    
#     distance = loc.length
#     return distance 
 
# def fset(self, value):
#     if self.location.length < 1E-6:
#         self.location = [1, 0, 0]
#     self.location.length = value
 
# bpy.types.Object.distance = property(fget, fset)
 
# ob = bpy.context.active_object
# if (ob is not None):
#     print(ob.distance)
#     ob.distance = 2
 
class BlendSegPanel (bpy.types.Panel):
    # bl_space_type = "VIEW_3D"
    # bl_region_type = "UI"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"
    bl_label = "BlendSeg"
 
    def draw(self, context):
        self.layout.operator("object.blendseg",
                             "Execute BlendSeg")
        self.layout.operator("object.cleanblendseg",
                             "Cleanup BlendSeg")
        # display "distance" of the active object
        # self.layout.label(text=str(bpy.context.active_object.distance))

        
 

