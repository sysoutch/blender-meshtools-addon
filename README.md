# Mesh Tools Add-on

A comprehensive mesh editing add-on for Blender that provides import/export functionality, mesh conversion tools, advanced remeshing with built-in QuadriFlow integration, and automated baking workflows through BakeLab2. Features a user-friendly interface with collapsible sections, real-time status tracking, and detailed logging for efficient 3D workflow optimization.

## Screenshots

![Mesh Tools Interface](https://github.com/sysoutch/blender-meshtools-addon/blob/main/meshtools_screen.png?raw=true)

## Features

- **Import/Export Tools**: Multiple format support (GLB, OBJ, FBX) with local file import and FBX export functionality
- **Mesh Editing**: Tris to quads conversion, vertex merging, smooth shading with angle control, and mesh duplication
- **Advanced Remeshing**: QuadriFlow remeshing with target face count control and BakeLab2 integration
- **Material Management**: Real-time material property controls (metallic/roughness) with automatic shader node setup
- **User Interface**: Collapsible sections, status tracking, and detailed operation logging

## Installation

1. Download the add-on file
2. In Blender, go to Edit → Preferences → Add-ons
3. Click "Install" and select the downloaded file
4. Enable the "Mesh Tools" add-on
5. Access the tools in the 3D Viewport under the "MeshTools" tab

## Requirements
- [Blender 4.5.0 or higher](https://www.blender.org/download/) 
- [BakeLab2 add-on](https://github.com/specoolar/Blender-BakeLab2) (for baking functionality) - If you want to run this with --background command line argument use my fork of BakeLab2 until they (hopefully) accept my pull request 🤞 https://github.com/sysoutch/Blender-BakeLab2

## Workflow Recommendations

- Always duplicate your original mesh before remeshing
- Convert triangles to quads before merging vertices
- Use the warning system to avoid common workflow pitfalls
- Check the log for detailed operation information

This add-on is designed to be a one-stop solution for mesh preparation, optimization, and texturing workflows, making complex operations accessible through an intuitive interface.