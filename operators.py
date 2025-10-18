import bpy
import math
import threading
import json
import requests
import os
import time
import queue
from bpy_extras.io_utils import ImportHelper

_status_queue = queue.Queue()
_model_info_queue = queue.Queue()
_log_queue = queue.Queue()

# ------------------------------
# Scene property update functions
# ------------------------------
def update_material(self, context):
    obj = context.active_object
    if not obj or obj.type != 'MESH':
        return

    # Create default material if none exists
    if not obj.data.materials:
        mat = bpy.data.materials.new(name="Material")
        obj.data.materials.append(mat)

    for mat in obj.data.materials:
        if not mat:
            continue

        if not mat.use_nodes:
            mat.use_nodes = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Get or create Principled BSDF
        principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not principled:
            principled = nodes.new('ShaderNodeBsdfPrincipled')
            output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
            if output:
                links.new(principled.outputs['BSDF'], output.inputs['Surface'])

        # Ensure links to Metallic are removed
        metallic_input = principled.inputs.get('Metallic')
        if metallic_input and metallic_input.is_linked:
            links.remove(metallic_input.links[0])
        metallic_input.default_value = 1.0 if context.scene.material_metallic else 0.0

        # Ensure links to Roughness are removed
        roughness_input = principled.inputs.get('Roughness')
        if roughness_input and roughness_input.is_linked:
            links.remove(roughness_input.links[0])
        roughness_input.default_value = context.scene.material_roughness

# ------------------------------
# Scene properties registration
# ------------------------------
def register_scene_props():
    bpy.types.Scene.meshtools_exp_mesh_tools = bpy.props.BoolProperty(name="Expand Mesh Tools", default=True)
    bpy.types.Scene.meshtools_exp_warning = bpy.props.BoolProperty(name="Expand Warning", default=True)
    bpy.types.Scene.meshtools_exp_log = bpy.props.BoolProperty(name="Expand Log", default=True)
    bpy.types.Scene.meshtools_status = bpy.props.StringProperty(default="Ready")
    bpy.types.Scene.meshtools_progress = bpy.props.StringProperty(default="")
    bpy.types.Scene.meshtools_model_info = bpy.props.StringProperty(default="")
    bpy.types.Scene.meshtools_log = bpy.props.StringProperty(default="")
    bpy.types.Scene.merge_distance = bpy.props.FloatProperty(name="Merge Distance", default=0.0001, min=0.0)
    bpy.types.Scene.quads_angle_limit = bpy.props.FloatProperty(name="Max Face Angle", default=40.0, min=0.0, max=180.0)
    bpy.types.Scene.quads_shape_threshold = bpy.props.FloatProperty(name="Max Shape Angle", default=40.0, min=0.0, max=180.0)
    bpy.types.Scene.smooth_angle = bpy.props.FloatProperty(name="Smooth Angle", default=30.0, min=0.0, max=180.0)
    bpy.types.Scene.material_metallic = bpy.props.BoolProperty(name="Metallic", default=False, update=update_material)
    bpy.types.Scene.material_roughness = bpy.props.FloatProperty(name="Smoothness", default=0.5, min=0.0, max=1.0, update=update_material)
    bpy.types.Scene.use_mesh_symmetry = bpy.props.BoolProperty(name="Mesh Symmetry", default=True)
    bpy.types.Scene.use_preserve_sharp = bpy.props.BoolProperty(name="Preserve Sharp", default=False)
    bpy.types.Scene.use_preserve_boundary = bpy.props.BoolProperty(name="Preserve Boundary", default=False)
    bpy.types.Scene.smooth_normals = bpy.props.BoolProperty(name="Smooth Normals", default=True)
    bpy.types.Scene.target_faces = bpy.props.IntProperty(name="Target Faces", default=10000, min=1)
    bpy.types.Scene.meshtools_export_fbx_path = bpy.props.StringProperty(name="Export Path", subtype='FILE_PATH', default="")

def unregister_scene_props():
    del bpy.types.Scene.meshtools_exp_mesh_tools
    del bpy.types.Scene.meshtools_exp_warning
    del bpy.types.Scene.meshtools_exp_log
    del bpy.types.Scene.meshtools_status
    del bpy.types.Scene.meshtools_progress
    del bpy.types.Scene.meshtools_model_info
    del bpy.types.Scene.meshtools_log
    del bpy.types.Scene.merge_distance
    del bpy.types.Scene.quads_angle_limit
    del bpy.types.Scene.quads_shape_threshold
    del bpy.types.Scene.smooth_angle
    del bpy.types.Scene.material_metallic
    del bpy.types.Scene.material_roughness
    del bpy.types.Scene.target_faces
    del bpy.types.Scene.use_mesh_symmetry
    del bpy.types.Scene.use_preserve_sharp
    del bpy.types.Scene.use_preserve_boundary
    del bpy.types.Scene.smooth_normals
    del bpy.types.Scene.meshtools_export_fbx_path

# ------------------------------
# Model import
# ------------------------------
def import_model_file(filepath):
    try:
        ext = filepath.split('.')[-1].lower()
        if ext == "glb":
            bpy.ops.import_scene.gltf(filepath=filepath)
        elif ext == "obj":
            bpy.ops.import_scene.obj(filepath=filepath)
        elif ext == "fbx":
            bpy.ops.import_scene.fbx(filepath=filepath)
        else:
            bpy.ops.import_scene.gltf(filepath=filepath)
        set_status("Imported successfully", os.path.basename(filepath))
        log(f"Imported {os.path.basename(filepath)} successfully")
    except Exception as e:
        set_status("Import Error", str(e))
        log(f"Import failed: {e}")

def duplicate_and_quadriflow_remesh(self, context):
    original_obj = context.active_object
    """
    Complete workflow: duplicate, remesh, and bake using BakeLab2 operators
    """
    if not original_obj or original_obj.type != 'MESH':
        print("No mesh object selected or not a mesh.")
        return

    print(f"Processing object: {original_obj.name}")

    # Ensure we're in Object mode
    if bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Step 1: Duplicate the object
    bpy.ops.object.duplicate()
    duplicate_obj = bpy.context.active_object
    duplicate_obj.name = original_obj.name + "_QuadRemesh"
    print(f"Created duplicate: {duplicate_obj.name}")

    # Select the object explicitly
    bpy.context.view_layer.objects.active = duplicate_obj
    duplicate_obj.select_set(True)
        
    # Step 2: Apply transforms before remeshing
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # Step 3: QuadriFlow remesh
    bpy.ops.object.quadriflow_remesh(
        mode='FACES',
        target_ratio=1.0,
        target_faces=context.scene.target_faces,
        use_mesh_symmetry=context.scene.use_mesh_symmetry,
        use_preserve_sharp=context.scene.use_preserve_sharp,
        use_preserve_boundary=context.scene.use_preserve_boundary,
        smooth_normals=context.scene.smooth_normals,
        seed=0
    )

    # Step 4: Create proper UV unwrap to prevent texture mixing
    create_bake_optimized_uvs(duplicate_obj)

    # Step 5: Set up selection for BakeLab2 baking
    bpy.ops.object.select_all(action='DESELECT')
    original_obj.select_set(True)      # Source object
    duplicate_obj.select_set(True)     # Target object  
    bpy.context.view_layer.objects.active = duplicate_obj  # Make target active

    print("Objects prepared for baking:")
    print(f"  Source: {original_obj.name}")
    print(f"  Target: {duplicate_obj.name} (active)")

    # Step 6: Try to call BakeLab2
    print("\nAttempting to call BakeLab2...")
    
    # Method 1: Try common BakeLab2 operator patterns
    bake_with_bakelab2()

def create_bake_optimized_uvs(obj):
    """Create Smart UV Project unwrap for baking"""
    print("Creating Smart UV Project unwrap...")
    
    # Store selection
    original_selection = bpy.context.selected_objects[:]
    original_active = bpy.context.view_layer.objects.active
    
    # Select only the target object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    # Enter Edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Clear existing UV maps
    while obj.data.uv_layers:
        obj.data.uv_layers.remove(obj.data.uv_layers[0])
    
    # Create new UV map
    obj.data.uv_layers.new(name="BakeUV")
    
    # Smart UV Project (as you preferred)
    print("  Using Smart UV Project...")
    bpy.ops.uv.smart_project(
        angle_limit=1.15,  # ~66 degrees
        island_margin=0.001,
        area_weight=0.0,
        correct_aspect=True,
        scale_to_bounds=False
    )
    
    # Return to Object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Restore selection
    bpy.ops.object.select_all(action='DESELECT')
    for o in original_selection:
        if o.name in bpy.data.objects:
            o.select_set(True)
    if original_active and original_active.name in bpy.data.objects:
        bpy.context.view_layer.objects.active = original_active
        
    print("  Smart UV Project completed!")

def set_status(status, progress=""):
    _status_queue.put((status, progress))

def set_model_info(model_info):
    _model_info_queue.put(model_info)

def log(message):
    _log_queue.put(message)

def start_queue_timer():
    def queue_timer():
        # Process status updates
        try:
            status, progress = _status_queue.get_nowait()
            bpy.context.scene.meshtools_status = status
            bpy.context.scene.meshtools_progress = progress
        except queue.Empty:
            pass
            
        # Process model info updates
        try:
            model_info = _model_info_queue.get_nowait()
            bpy.context.scene.meshtools_model_info = model_info
        except queue.Empty:
            pass
            
        # Process log updates
        try:
            message = _log_queue.get_nowait()
            bpy.context.scene.meshtools_log = bpy.context.scene.meshtools_log + "\n" + message
        except queue.Empty:
            pass
            
        return 0.1  # Return interval for next check
    
    bpy.app.timers.register(queue_timer, first_interval=0.1)

def bake_with_bakelab2():
    while len(bpy.context.scene.BakeLabMaps) > 0:
        bpy.ops.bakelab.removemapitem()
    bpy.context.scene.BakeLabProps.bake_mode = 'TO_ACTIVE'
    bpy.context.scene.BakeLabProps.bake_margin = 2
    bpy.context.scene.BakeLabProps.anti_alias = 2
    bpy.ops.bakelab.newmapitem(width=2048, height=2048)
    bpy.context.scene.BakeLabMaps[0].samples = 4

    bpy.ops.bakelab.newmapitem(type='Normal', width=2048, height=2048)

    bpy.ops.bakelab.bake()
    
    def timer_function():
        applyBakelabMaterials()
        return None
    
    bpy.app.timers.register(timer_function, first_interval=15)
    
def applyBakelabMaterials():
    bpy.ops.bakelab.generate_mats()
    #bpy.app.timers.register(applyBakelabNormalMaterial, first_interval=5)
    bpy.ops.bakelab.finish()
    bpy.ops.bakelab.removemapitem()
    bpy.ops.bakelab.removemapitem()

# ------------------------------
# Operators
# ------------------------------
class MeshToolsImportOperator(bpy.types.Operator, ImportHelper):
    bl_idname = "wm.meshtools_import_model"
    bl_label = "Import Model"

    def execute(self, context):
        scene = context.scene
        if not scene.meshtools_model_info:
            self.report({'ERROR'}, "No model info to import")
            return {'CANCELLED'}
        model_info = json.loads(scene.meshtools_model_info)
        download_url = model_info["model_url"]
        temp_file = os.path.join(bpy.app.tempdir, model_info['filename'])
        try:
            r = requests.get(download_url)
            if r.status_code != 200:
                raise Exception(f"Download failed: {r.status_code}")
            with open(temp_file, "wb") as f:
                f.write(r.content)
            import_model_file(temp_file)
        except Exception as e:
            set_status("Import Error", str(e))
            log(f"Import failed: {e}")
        return {'FINISHED'}

class MeshToolsImportLocalOperator(bpy.types.Operator, ImportHelper):
    bl_idname = "wm.meshtools_import_local_model"
    bl_label = "Import Local Model"
    filename_ext = ".glb;.obj;.fbx"

    def execute(self, context):
        filepath = self.filepath
        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"File not found: {filepath}")
            return {'CANCELLED'}
        import_model_file(filepath)
        return {'FINISHED'}

class MeshToolsDuplicateOperator(bpy.types.Operator):
    bl_idname = "wm.meshtools_duplicate_object"
    bl_label = "Duplicate Selected Object"

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}
        bpy.ops.object.duplicate()
        return {'FINISHED'}

class MeshToolsTrisToQuadsOperator(bpy.types.Operator):
    bl_idname = "wm.meshtools_tris_to_quads"
    bl_label = "Tris to Quads"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.tris_convert_to_quads()
            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'INFO'}, "Converted tris to quads")
        else:
            self.report({'WARNING'}, "No mesh object selected")
        return {'FINISHED'}

class MeshToolsMergeVerticesOperator(bpy.types.Operator):
    bl_idname = "wm.meshtools_merge_vertices"
    bl_label = "Merge Vertices by Distance"

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=context.scene.merge_distance)
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, f"Merged vertices with distance {context.scene.merge_distance}")
        return {'FINISHED'}

class MeshToolsSmoothShadingOperator(bpy.types.Operator):
    bl_idname = "wm.meshtools_smooth_shading"
    bl_label = "Apply Smooth Shading"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import math
        obj = context.active_object
        scene = context.scene
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        # Apply smooth shading to mesh
        bpy.ops.object.shade_smooth()

        # Check if Edge Split modifier already exists
        mod = next((m for m in obj.modifiers if m.name == "Smooth by Angle"), None)
        if not mod:
            mod = obj.modifiers.new(name="Smooth by Angle", type='EDGE_SPLIT')

        # Update split angle
        mod.split_angle = math.radians(scene.smooth_angle)

        self.report({'INFO'}, f"Applied smooth shading with angle {scene.smooth_angle}°")
        return {'FINISHED'}

class MeshToolsMaterialOperator(bpy.types.Operator):
    bl_idname = "wm.meshtools_adjust_material"
    bl_label = "Adjust Material"

    def execute(self, context):
        update_material(self, context)
        self.report({'INFO'}, "Material updated")
        return {'FINISHED'}

class MeshToolsBakeOperator(bpy.types.Operator):
    bl_idname = "wm.meshtools_bake"
    bl_label = "Remesh + Bake"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        duplicate_and_quadriflow_remesh(self, context)
        self.report({'INFO'}, "Material updated")
        return {'FINISHED'}

class MeshToolsExportFBXOperator(bpy.types.Operator):
    bl_idname = "wm.meshtools_export_fbx"
    bl_label = "Export as FBX"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}
        
        # Get the export path from the user
        bpy.ops.export_scene.fbx('INVOKE_DEFAULT')
        return {'FINISHED'}

class MeshToolsQuickExportFBXOperator(bpy.types.Operator):
    bl_idname = "wm.meshtools_quick_export_fbx"
    bl_label = "Quick Export FBX"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}
        
        # Get the export path from scene properties or use default
        scene = context.scene
        export_path = scene.meshtools_export_fbx_path
        
        # If no export path is set, use a default location
        if not export_path:
            import os
            export_path = os.path.join(bpy.app.tempdir, f"{obj.name}.fbx")
        
        # Export the object to FBX
        bpy.ops.export_scene.fbx(
            filepath=export_path,
            use_selection=True,
            apply_scale_options='FBX_SCALE_ALL',
            bake_space_transform=False,
            use_mesh_modifiers=True,
            add_leaf_bones=False,
            path_mode='COPY'
        )
        
        self.report({'INFO'}, f"Exported {obj.name} to {export_path}")
        return {'FINISHED'}

# ------------------------------
# Operator classes list
# ------------------------------
classes = [
    MeshToolsImportOperator,
    MeshToolsImportLocalOperator,
    MeshToolsDuplicateOperator,
    MeshToolsTrisToQuadsOperator,
    MeshToolsMergeVerticesOperator,
    MeshToolsSmoothShadingOperator,
    MeshToolsMaterialOperator,
    MeshToolsBakeOperator,
    MeshToolsExportFBXOperator,
    MeshToolsQuickExportFBXOperator
]
