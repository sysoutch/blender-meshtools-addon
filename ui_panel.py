import bpy

class MeshToolsPanel(bpy.types.Panel):
    bl_label = "Mesh Tools"
    bl_idname = "VIEW3D_PT_mesh_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MeshTools"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Add scrollability by setting the column to be a scrollable layout
        col = layout.column(align=True)

        col.operator("wm.meshtools_import_model", icon='IMPORT')
        col.operator("wm.meshtools_import_local_model", icon='FILE_FOLDER')

        # ---------------------------
        # Warning Box Section (Collapsible)
        # ---------------------------
        if scene.meshtools_exp_warning:
            warning_box = col.box()
            warning_box.label(text="⚠️ Warning:", icon='ERROR')
            warning_box.label(text="Merge your original mesh and then continue remeshing on a duplicate.")
            warning_box.label(text="If textures get messed up when merging, convert tris to quads first and try again.")
            warning_box.operator("wm.meshtools_duplicate_object", text="Duplicate Selected Object", icon='DUPLICATE')
        else:
            col.prop(scene, "meshtools_exp_warning", text="⚠️ Warning", icon='ERROR')

        # ---------------------------
        # Mesh Tools Section (Collapsible)
        # ---------------------------
        if scene.meshtools_exp_mesh_tools:
            mesh_box = col.box()
            mesh_box.label(text="Mesh Tools:")
            mesh_box.operator("wm.meshtools_tris_to_quads", icon='MESH_GRID')
            mesh_box.prop(scene, "quads_angle_limit")
            mesh_box.prop(scene, "quads_shape_threshold")
            row = mesh_box.row()
            row.prop(scene, "merge_distance")
            row.operator("wm.meshtools_merge_vertices", icon='AUTOMERGE_ON')

            mesh_box.prop(scene, "smooth_angle")
            mesh_box.operator("wm.meshtools_smooth_shading", icon='SHADING_SOLID')
            mesh_box.prop(scene, "material_metallic")
            mesh_box.prop(scene, "material_roughness")
            mesh_box.operator("wm.meshtools_adjust_material", icon='MATERIAL')
            mesh_box.prop(scene, "use_mesh_symmetry")
            mesh_box.prop(scene, "use_preserve_sharp")
            mesh_box.prop(scene, "use_preserve_boundary")
            mesh_box.prop(scene, "smooth_normals")
            mesh_box.prop(scene, "target_faces")
            mesh_box.operator("wm.meshtools_bake", icon='MOD_REMESH')
        else:
            col.prop(scene, "meshtools_exp_mesh_tools", text="Mesh Tools", icon='MODIFIER')

        # ---------------------------
        # Export Section
        # ---------------------------
        col.operator("wm.meshtools_export_fbx", icon='EXPORT')
        col.operator("wm.meshtools_quick_export_fbx", icon='EXPORT')
        col.prop(scene, "meshtools_export_fbx_path", text="Export Path")

        # ---------------------------
        # Status / Progress Section
        # ---------------------------
        col.label(text=f"Status: {scene.meshtools_status}")
        if scene.meshtools_progress:
            col.label(text=f"Progress: {scene.meshtools_progress}")

        # ---------------------------
        # Log Section (Collapsible)
        # ---------------------------
        if scene.meshtools_exp_log:
            log_box = col.box()
            log_box.label(text="Log:")
            log_box.prop(scene, "meshtools_log", text="")
            log_box.operator("wm.meshtools_clear_log", text="Clear Log", icon='X')
        else:
            col.prop(scene, "meshtools_exp_log", text="Log", icon='TEXT')