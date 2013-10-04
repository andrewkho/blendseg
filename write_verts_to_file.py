import os
import glob
#import imp
#import material_loader
#imp.reload (material_loader)
#import slice_plane
#imp.reload (slice_plane)
#import object_intersection 
#imp.reload (object_intersection)

import bpy
from bpy_extras import image_utils

def print_selected_vertices ():
   return [i.index for i in bpy.context.active_object.data.vertices if i.select]

def write_selected_vertices ():
   selected_verts = [i.index for i in bpy.context.active_object.data.vertices if i.select]
   f = open ("points.txt", "w")
   print ("writing to points.txt...")
   for idx in selected_verts:
      f.write (str(idx) + "\n")
   print ("done!")
   f.close()
