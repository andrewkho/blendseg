import bpy

from .blendseg import BlendSegOperator
from .blendseg import BlendSegCleanupOperator
from .blendseg_panel import BlendSegPanel

bl_info = {
    "name": "Blendseg Addon",
    "category": "Operator",
}


def register_operators():
    """Register Blendseg Operator with blender"""
    bpy.utils.register_class(BlendSegOperator)
    bpy.utils.register_class(BlendSegCleanupOperator)

def unregister_operators():
    bpy.utils.unregister_class(BlendSegOperator)
    bpy.utils.unregister_class(BlendSegCleanupOperator)

def register_panel():
    bpy.utils.register_class(BlendSegPanel)

def unregister_panel():
    bpy.utils.unregister_class(BlendSegPanel)

def register():
    register_operators()
    register_panel()

def unregister():
    unregister_operators()
    unregister_panel()
    

if __name__ == "__main__":
    register()
