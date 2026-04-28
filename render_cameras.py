"""
Usage:
1. Select the product objects, or leave nothing selected to use all visible mesh/curve product objects.
2. Run Object -> Set Up Laser Render Cameras.
3. View through the active camera with Numpad 0.
4. Assign a shortcut by pressing F3, searching for Set Up Laser Render Cameras,
   right-clicking, then choosing Assign Shortcut.
"""

bl_info = {
    "name": "Laser Render Studio Cameras",
    "author": "OpenAI / Roland",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "Object > Set Up Laser Render Cameras",
    "description": "Creates a reusable multi-camera studio setup for laser-cut product renders.",
    "category": "Object",
}

import bpy
from mathutils import Vector

VALID_PRODUCT_TYPES = {"MESH", "CURVE"}
STUDIO_COLLECTION_NAME = "Laser_Render_Studio"
PRODUCT_TARGET_NAME = "Product_Target"
MINIMUM_PRODUCT_SIZE = 0.1
BACKDROP_FLOOR_NAME = "Studio_Backdrop_Floor"
BACKDROP_WALL_NAME = "Studio_Backdrop_Wall"
BACKDROP_MATERIAL_NAME = "Studio_Backdrop_White"

CAMERA_SPECS = {
    "Camera_Front_3Q": {
        "offset": (-1.9, -2.45, 1.35),
        "lens": 70,
        "fstop": 32.0,
    },
    "Camera_Top": {
        "offset": (0.0, 0.0, 3.0),
        "lens": 85,
        "fstop": 40.0,
    },
    "Camera_Closeup": {
        "offset": (-0.95, -1.35, 0.72),
        "lens": 90,
        "fstop": 22.0,
    },
    "Camera_Side_3Q": {
        "offset": (2.35, -1.05, 1.0),
        "lens": 70,
        "fstop": 32.0,
    },
}

LIGHT_SPECS = {
    "Studio_Key_Light": {
        "offset": (-1.7, -2.1, 2.1),
        "power": 85.0,
        "size": 6.5,
        "color": (1.0, 0.96, 0.9),
    },
    "Studio_Fill_Light": {
        "offset": (1.7, -1.6, 1.4),
        "power": 16.0,
        "size": 7.0,
        "color": (0.99, 0.97, 0.93),
    },
    "Studio_Rim_Light": {
        "offset": (0.0, 1.8, 1.5),
        "power": 36.0,
        "size": 5.0,
        "color": (0.98, 0.98, 0.97),
    },
    "Studio_Top_Light": {
        "offset": (0.0, 0.0, 2.5),
        "power": 10.0,
        "size": 7.0,
        "color": (1.0, 0.98, 0.95),
    },
}


def is_candidate_product_object(obj):
    if obj.type not in VALID_PRODUCT_TYPES:
        return False
    prefixes = ("Camera_", "Studio_", PRODUCT_TARGET_NAME)
    return not obj.name.startswith(prefixes)


def get_product_objects(context):
    selected = [obj for obj in context.selected_objects if is_candidate_product_object(obj)]
    if selected:
        return selected

    return [
        obj for obj in context.scene.objects
        if is_candidate_product_object(obj) and obj.visible_get()
    ]


def get_world_bbox(objects):
    points = []
    for obj in objects:
        if obj.type not in VALID_PRODUCT_TYPES:
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))

    if not points:
        zero = Vector((0.0, 0.0, 0.0))
        return zero, zero, zero, MINIMUM_PRODUCT_SIZE

    min_v = Vector((
        min(point.x for point in points),
        min(point.y for point in points),
        min(point.z for point in points),
    ))
    max_v = Vector((
        max(point.x for point in points),
        max(point.y for point in points),
        max(point.z for point in points),
    ))
    center = (min_v + max_v) / 2.0
    size = max(max_v.x - min_v.x, max_v.y - min_v.y, max_v.z - min_v.z, MINIMUM_PRODUCT_SIZE)
    return min_v, max_v, center, size


def get_or_create_collection(name, scene):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
    elif collection.name not in scene.collection.children:
        scene.collection.children.link(collection)
    return collection


def ensure_object_in_collection(obj, collection):
    if collection not in obj.users_collection:
        collection.objects.link(obj)


def get_or_create_target(collection):
    obj = bpy.data.objects.get(PRODUCT_TARGET_NAME)
    if obj and obj.type == "EMPTY":
        ensure_object_in_collection(obj, collection)
        return obj

    obj = bpy.data.objects.new(PRODUCT_TARGET_NAME, None)
    obj.empty_display_type = "PLAIN_AXES"
    ensure_object_in_collection(obj, collection)
    return obj


def get_or_create_camera(name, collection):
    obj = bpy.data.objects.get(name)
    if obj and obj.type == "CAMERA":
        ensure_object_in_collection(obj, collection)
        return obj

    camera_data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, camera_data)
    collection.objects.link(obj)
    return obj


def get_or_create_area_light(name, collection):
    obj = bpy.data.objects.get(name)
    if obj and obj.type == "LIGHT":
        ensure_object_in_collection(obj, collection)
        return obj

    light_data = bpy.data.lights.new(name, type="AREA")
    obj = bpy.data.objects.new(name, light_data)
    collection.objects.link(obj)
    return obj


def ensure_principled_material(name, base_color, roughness=0.8):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)

    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (220, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = base_color
    return material


def get_or_create_plane(name, collection):
    obj = bpy.data.objects.get(name)
    if obj and obj.type == "MESH":
        ensure_object_in_collection(obj, collection)
        return obj

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        [(-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (1.0, 1.0, 0.0), (-1.0, 1.0, 0.0)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def set_track_to(obj, target):
    constraint = obj.constraints.get("Track Product Target")
    if constraint is None or constraint.type != "TRACK_TO":
        if constraint is not None:
            obj.constraints.remove(constraint)
        constraint = obj.constraints.new(type="TRACK_TO")
        constraint.name = "Track Product Target"

    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"


def configure_camera(camera_obj, target, center, size, spec):
    offset = Vector(spec["offset"]) * size
    camera_obj.location = center + offset
    camera_obj.rotation_euler = (0.0, 0.0, 0.0)
    set_track_to(camera_obj, target)

    camera_data = camera_obj.data
    camera_data.type = "PERSP"
    camera_data.lens = spec["lens"]
    camera_data.sensor_width = 32
    camera_data.dof.use_dof = True
    camera_data.dof.focus_object = target
    camera_data.dof.aperture_fstop = spec["fstop"]


def configure_light(light_obj, target, center, size, spec):
    offset = Vector(spec["offset"]) * size
    light_obj.location = center + offset
    light_obj.rotation_euler = (0.0, 0.0, 0.0)
    set_track_to(light_obj, target)

    light_data = light_obj.data
    light_data.type = "AREA"
    light_data.energy = spec["power"]
    light_data.shape = "RECTANGLE"
    light_data.size = spec["size"]
    light_data.size_y = spec["size"]
    light_data.color = spec["color"]
    if hasattr(light_data, "shadow_soft_size"):
        light_data.shadow_soft_size = max(spec["size"] * 0.5, 0.5)


def configure_backdrop(collection, center, min_v, max_v, size):
    backdrop_material = ensure_principled_material(
        BACKDROP_MATERIAL_NAME,
        (0.94, 0.935, 0.925, 1.0),
        roughness=1.0,
    )

    floor = get_or_create_plane(BACKDROP_FLOOR_NAME, collection)
    wall = get_or_create_plane(BACKDROP_WALL_NAME, collection)

    floor.data.materials.clear()
    floor.data.materials.append(backdrop_material)
    wall.data.materials.clear()
    wall.data.materials.append(backdrop_material)

    floor.location = Vector((center.x, center.y, min_v.z - 0.001))
    floor.rotation_euler = (0.0, 0.0, 0.0)
    floor.scale = Vector((size * 4.2, size * 4.2, 1.0))

    wall.location = Vector((center.x, max_v.y + size * 1.95, min_v.z + size * 1.55))
    wall.rotation_euler = (1.5707963, 0.0, 0.0)
    wall.scale = Vector((size * 4.2, size * 2.1, 1.0))


def apply_render_settings(scene):
    scene.render.resolution_x = 2000
    scene.render.resolution_y = 2000
    scene.render.film_transparent = False
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        pass
    scene.render.use_compositing = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs[0].default_value = (0.82, 0.82, 0.81, 1.0)
        bg.inputs[1].default_value = 0.025
    view_settings = getattr(scene, "view_settings", None)
    if view_settings is not None:
        try:
            view_settings.look = "Medium High Contrast"
        except Exception:
            pass
        try:
            view_settings.exposure = -0.55
        except Exception:
            pass
        try:
            view_settings.gamma = 1.0
        except Exception:
            pass
    eevee = getattr(scene, "eevee", None)
    if eevee is not None:
        for attr, value in (
            ("use_gtao", True),
            ("gtao_factor", 0.8),
            ("use_bloom", False),
            ("use_shadows", True),
            ("use_raytracing", True),
            ("use_ssr", True),
            ("use_ssr_refraction", True),
        ):
            if hasattr(eevee, attr):
                setattr(eevee, attr, value)
        if hasattr(eevee, "shadow_step_count"):
            eevee.shadow_step_count = 8
        if hasattr(eevee, "taa_render_samples"):
            eevee.taa_render_samples = 64
        if hasattr(eevee, "bokeh_max_size"):
            eevee.bokeh_max_size = 8.0


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

    setup_backdrop: bpy.props.BoolProperty(
        name="Set Up Studio Backdrop",
        default=True,
    )

    def execute(self, context):
        product_objects = get_product_objects(context)
        min_v, max_v, center, size = get_world_bbox(product_objects)

        studio_collection = get_or_create_collection(STUDIO_COLLECTION_NAME, context.scene)
        product_target = get_or_create_target(studio_collection)
        product_target.location = center
        product_target.empty_display_size = max(size * 0.08, 0.05)

        created_cameras = []
        for name, spec in CAMERA_SPECS.items():
            camera_obj = get_or_create_camera(name, studio_collection)
            configure_camera(camera_obj, product_target, center, size, spec)
            created_cameras.append(camera_obj)

        if self.setup_lights:
            for name, spec in LIGHT_SPECS.items():
                light_obj = get_or_create_area_light(name, studio_collection)
                configure_light(light_obj, product_target, center, size, spec)

        if self.setup_backdrop:
            configure_backdrop(studio_collection, center, min_v, max_v, size)

        if self.setup_render_settings:
            apply_render_settings(context.scene)

        front_camera = bpy.data.objects.get("Camera_Front_3Q")
        if front_camera and front_camera.type == "CAMERA":
            context.scene.camera = front_camera

        message = (
            f"Laser render cameras set up: target at ({center.x:.3f}, {center.y:.3f}, {center.z:.3f}), "
            f"product size {size:.3f}, cameras {len(created_cameras)}"
        )
        self.report({"INFO"}, message)
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_setup_laser_render_cameras.bl_idname)


classes = (OBJECT_OT_setup_laser_render_cameras,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
