# Skill: Build a Blender Add-on to Set Up Studio Cameras for Laser-Cut Product Renders

## Goal

Build a Blender add-on that creates or refreshes a reusable studio camera setup for rendering laser-cut product scenes. The add-on should be designed to work alongside an existing SVG processing add-on that imports/extrudes laser-cut parts. The user should be able to open a prepared product scene, run one operator, and get a consistent set of cameras aimed at the product.

The add-on must be simple enough for a Blender beginner to use, but robust enough for repeated production use.

## Target Environment

- Blender 5.x, with compatibility preferred for Blender 4.2+
- macOS and Linux/Manjaro
- Python add-on file, single-file implementation preferred
- Installable via:
  - `Edit → Preferences → Add-ons → Install from Disk`
- No external Python dependencies
- Use only Blender's built-in `bpy` API

## User Context

The user has extensive CAD/SolidWorks experience but limited Blender experience. The add-on should therefore avoid requiring manual scene setup or Blender-specific knowledge. It should create named objects and use predictable defaults.

The user wants to render laser-cut products assembled from SVG-imported/extruded parts. The scene should behave like a product photography studio template.

## Add-on Name

Use a clear name such as:

```text
Laser Render Studio Cameras
```

Suggested operator label:

```text
Set Up Laser Render Cameras
```

Suggested operator id:

```python
object.setup_laser_render_cameras
```

## Primary User Workflow

The desired workflow is:

1. User opens a Blender scene containing product parts.
2. User runs:
   - `Object → Set Up Laser Render Cameras`
   - or uses a keyboard shortcut assigned via `F3` search.
3. Add-on creates/updates:
   - target empty at product centre
   - 3 or 4 cameras
   - camera tracking constraints
   - optional focal lengths/depth of field
   - optional render resolution settings
4. User can render from each camera manually or via a future batch render add-on/operator.

## Functional Requirements

### 1. Create or Reuse a Product Target

Create or reuse an Empty named:

```text
Product_Target
```

The target should be placed at the centre of the product geometry.

Preferred behaviour:

- If objects are selected, use the bounding box of selected mesh/curve objects.
- If nothing is selected, use all visible mesh/curve objects in the scene, excluding cameras, lights, empties, and known studio objects.
- If no suitable objects exist, place the target at origin `(0, 0, 0)`.

The target should be a Plain Axes empty.

Suggested size:

```python
empty.empty_display_size = 0.05
```

### 2. Create or Refresh Cameras

Create or update the following cameras:

```text
Camera_Front_3Q
Camera_Top
Camera_Closeup
Camera_Side_3Q
```

If the camera already exists, update its transform and settings rather than creating duplicates.

All cameras should point at `Product_Target` using a `TRACK_TO` constraint.

Recommended constraint settings:

```python
constraint.type = 'TRACK_TO'
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'
constraint.target = product_target
```

### 3. Camera Placement

Camera placement should scale based on the product bounding box size.

Calculate:

```python
bbox_width = max_x - min_x
bbox_depth = max_y - min_y
bbox_height = max_z - min_z
product_size = max(bbox_width, bbox_depth, bbox_height, minimum_size)
```

Use a minimum size such as:

```python
minimum_size = 0.1
```

Recommended positions relative to target:

```text
Camera_Front_3Q:
  x = -1.4 * product_size
  y = -1.8 * product_size
  z =  1.1 * product_size

Camera_Top:
  x = 0
  y = 0
  z = 2.3 * product_size

Camera_Closeup:
  x = -0.7 * product_size
  y = -1.0 * product_size
  z =  0.55 * product_size

Camera_Side_3Q:
  x = 1.8 * product_size
  y = -0.8 * product_size
  z = 0.8 * product_size
```

These are offsets from `Product_Target.location`.

The top camera should also use the same Track To constraint, pointing down at the target.

### 4. Camera Settings

Use sensible product-render defaults.

Recommended settings:

```python
camera.data.lens = 70
camera.data.type = 'PERSP'
camera.data.sensor_width = 32
```

For `Camera_Top`, optionally use a slightly longer focal length:

```python
camera.data.lens = 85
```

For `Camera_Closeup`:

```python
camera.data.lens = 90
```

Depth of field should be optional, but a good default is:

```python
camera.data.dof.use_dof = True
camera.data.dof.focus_object = product_target
camera.data.dof.aperture_fstop = 8.0
```

Avoid overly shallow depth of field by default. Laser-cut products need crisp edges.

### 5. Set Active Camera

Set the scene active camera to:

```text
Camera_Front_3Q
```

```python
context.scene.camera = bpy.data.objects['Camera_Front_3Q']
```

### 6. Optional Studio Lighting Setup

The core request is camera setup, but the add-on may optionally include studio lights if straightforward.

If implemented, create or update these lights:

```text
Studio_Key_Light
Studio_Fill_Light
Studio_Rim_Light
Studio_Top_Light
```

Use Area lights.

Suggested defaults:

```text
Studio_Key_Light:
  type: AREA
  power: 600
  size: 4.0
  position: (-1.5 * product_size, -1.8 * product_size, 2.0 * product_size)

Studio_Fill_Light:
  type: AREA
  power: 150
  size: 5.0
  position: (1.5 * product_size, -1.5 * product_size, 1.3 * product_size)

Studio_Rim_Light:
  type: AREA
  power: 300
  size: 3.0
  position: (0.0, 1.8 * product_size, 1.5 * product_size)

Studio_Top_Light:
  type: AREA
  power: 150
  size: 4.0
  position: (0.0, 0.0, 2.5 * product_size)
```

If lights are included, make this optional via an operator property:

```python
setup_lights: BoolProperty(default=True)
```

### 7. Optional Render Settings

The add-on may set basic render settings:

```python
scene.render.resolution_x = 2000
scene.render.resolution_y = 2000
scene.render.film_transparent = False
```

Prefer not to force a render engine unless explicitly requested. If setting one, use a safe default compatible with Blender 4/5:

```python
scene.render.engine = 'BLENDER_EEVEE_NEXT'
```

But this can vary by Blender version, so guard it with a try/except or avoid setting it.

### 8. Collections

Create a collection named:

```text
Laser_Render_Studio
```

Place generated cameras, target empty, and optional studio lights inside that collection.

Do not delete user objects.

When refreshing, update known named objects rather than clearing the collection blindly.

### 9. Menu Integration

Register the operator under the Object menu:

```text
Object → Set Up Laser Render Cameras
```

Example:

```python
def menu_func(self, context):
    self.layout.operator(OBJECT_OT_setup_laser_render_cameras.bl_idname)

bpy.types.VIEW3D_MT_object.append(menu_func)
```

### 10. Shortcut Assignment

Do not hard-code a keyboard shortcut unless there is a strong reason.

The operator must be discoverable through `F3` search by its label:

```text
Set Up Laser Render Cameras
```

The user can then assign a shortcut manually by right-clicking the search result.

Recommended shortcut for user documentation:

```text
Ctrl + Alt + C
```

or:

```text
Ctrl + Alt + K
```

Avoid common Blender shortcuts such as `G`, `R`, `S`, `Ctrl + R`, `Ctrl + E`, and `Alt + E`.

## Implementation Guidance

### Add-on Header

Use a valid `bl_info` block:

```python
bl_info = {
    "name": "Laser Render Studio Cameras",
    "author": "OpenAI / Roland",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "Object > Set Up Laser Render Cameras",
    "description": "Creates a reusable multi-camera studio setup for laser-cut product renders.",
    "category": "Object",
}
```

### Operator Skeleton

```python
class OBJECT_OT_setup_laser_render_cameras(bpy.types.Operator):
    bl_idname = "object.setup_laser_render_cameras"
    bl_label = "Set Up Laser Render Cameras"
    bl_options = {"REGISTER", "UNDO"}

    setup_lights: bpy.props.BoolProperty(
        name="Set Up Studio Lights",
        default=True,
    )

    setup_render_settings: bpy.props.BoolProperty(
        name="Set Render Resolution",
        default=True,
    )

    def execute(self, context):
        # create/update target, cameras, optional lights
        self.report({'INFO'}, "Laser render cameras set up")
        return {'FINISHED'}
```

### Bounding Box Calculation

Implement a helper that works for meshes and curves:

```python
from mathutils import Vector

VALID_PRODUCT_TYPES = {'MESH', 'CURVE'}

def get_world_bbox(objects):
    points = []
    for obj in objects:
        if obj.type not in VALID_PRODUCT_TYPES:
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))

    if not points:
        return Vector((0, 0, 0)), Vector((0, 0, 0)), Vector((0, 0, 0)), 0.1

    min_v = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    max_v = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    center = (min_v + max_v) / 2
    size = max(max_v.x - min_v.x, max_v.y - min_v.y, max_v.z - min_v.z, 0.1)
    return min_v, max_v, center, size
```

### Product Object Selection Logic

Use selected product objects first:

```python
selected_products = [obj for obj in context.selected_objects if obj.type in VALID_PRODUCT_TYPES]
```

If empty, use visible scene products:

```python
visible_products = [
    obj for obj in context.scene.objects
    if obj.type in VALID_PRODUCT_TYPES
    and obj.visible_get()
    and not obj.name.startswith("Camera_")
    and not obj.name.startswith("Studio_")
]
```

### Camera Creation Helper

```python
def get_or_create_camera(name, collection):
    obj = bpy.data.objects.get(name)
    if obj and obj.type == 'CAMERA':
        return obj

    cam_data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, cam_data)
    collection.objects.link(obj)
    return obj
```

### Collection Linking Helper

Ensure generated objects are linked to `Laser_Render_Studio` without breaking if they are already in other collections.

```python
def get_or_create_collection(name, scene):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
    return collection
```

### Track To Constraint Helper

Before adding a new constraint, reuse or replace the existing named constraint:

```python
def set_track_to(obj, target):
    constraint = obj.constraints.get("Track Product Target")
    if constraint is None:
        constraint = obj.constraints.new(type='TRACK_TO')
        constraint.name = "Track Product Target"
    constraint.target = target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'
```

## Acceptance Criteria

The add-on is acceptable when:

1. It installs successfully from a single `.py` file.
2. It appears in Preferences → Add-ons when searching for:
   - `Laser Render Studio Cameras`
   - or `Laser`
3. It adds a command to:
   - `Object → Set Up Laser Render Cameras`
4. It appears in `F3` search as:
   - `Set Up Laser Render Cameras`
5. Running the operator creates or updates:
   - `Product_Target`
   - `Camera_Front_3Q`
   - `Camera_Top`
   - `Camera_Closeup`
   - `Camera_Side_3Q`
6. All cameras point at `Product_Target`.
7. The active camera becomes `Camera_Front_3Q`.
8. Running the operator repeatedly does not create duplicate cameras or duplicate targets.
9. If product objects are selected, cameras frame the selected product.
10. If no product objects are selected, cameras frame visible mesh/curve product objects.
11. Optional lights, if implemented, are created or updated without duplicates.
12. The add-on reports success in Blender's status area.

## Nice-to-Have Features

These are optional and should not block the first implementation:

### Camera Preview Markers

Add small text labels or custom properties to generated cameras.

### Batch Render Operator

A future operator could render all cameras:

```text
Render All Laser Studio Cameras
```

Expected cameras:

```python
[obj for obj in scene.objects if obj.type == 'CAMERA' and obj.name.startswith('Camera_')]
```

Output path:

```python
//renders/<scene-name>_<camera-name>.png
```

### Background Plane

Create a neutral floor plane and curved backdrop, but only if requested. Avoid interfering with user geometry.

### UI Panel

Add a small panel in the 3D View sidebar:

```text
N-panel → Laser Studio
```

Buttons:

- Set Up Cameras
- Set Up Cameras + Lights
- Render All Cameras

## Important Non-Goals

Do not implement SVG import or extrusion in this add-on. That belongs to the separate SVG processing add-on.

Do not destructively modify product objects.

Do not delete user-created cameras unless they use the exact generated names and are being refreshed.

Do not require external add-ons, external render engines, or downloaded assets.

## Documentation to Include for the User

Add short usage instructions in a comment at the top of the file or in a README-style docstring:

```text
Usage:
1. Select the product objects, or leave nothing selected to use all visible mesh/curve product objects.
2. Run Object → Set Up Laser Render Cameras.
3. View through the active camera with Numpad 0.
4. Assign a shortcut by pressing F3, searching for Set Up Laser Render Cameras, right-clicking, then choosing Assign Shortcut.
```

## Recommended Manual Test

1. Open Blender.
2. Create a cube or import/extrude an SVG part.
3. Select the object.
4. Run `Object → Set Up Laser Render Cameras`.
5. Confirm four cameras appear.
6. Press `Numpad 0`.
7. Confirm the camera points at the object.
8. Run the operator again.
9. Confirm no duplicate cameras are created.
