bl_info = {
    "name": "Mesh Tools",
    "author": "Rainer Wahnsinn",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "View3D > UI > Mesh Tools",
    "description": "Multiple useful Mesh Options",
    "category": "3D View"
}

import bpy
from . import operators
from . import ui_panel

classes = operators.classes + [ui_panel.MeshToolsPanel]

def register():
    operators.register_scene_props()
    for cls in classes:
        bpy.utils.register_class(cls)
    operators.start_queue_timer()

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    operators.unregister_scene_props()
