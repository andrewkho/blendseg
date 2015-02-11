import bpy
from .blendseg import BlendSeg
from .blendseg import BlendSegPrefs
from .blendseg import BlendSegOperator
from .blendseg import BlendSegCleanupOperator

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

    
