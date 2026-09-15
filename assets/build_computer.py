"""Build the custom profile workstation. Execute through Blender MCP, then render.
Only the dedicated Profile Workstation scene is replaced on regeneration.
"""
import bpy
import sys
from mathutils import Vector
from pathlib import Path

OUT = Path(__file__).resolve().parent
previous = bpy.data.scenes.get('Profile Workstation')
scene = bpy.data.scenes.new('Profile Workstation')
bpy.context.window.scene = scene
if previous:
    for obj in list(previous.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(previous)
scene.name = 'Profile Workstation'

def material(name, color, metallic=0, rough=.4, emission=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = rough
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1)
        p.inputs['Emission Strength'].default_value = emission
    return m

shell = material('Graphite anodized aluminium', (.045,.060,.052), .78, .28)
edge = material('Satin edge', (.15,.20,.17), .72, .3)
black = material('Obsidian glass', (.005,.012,.008), .25, .21)
key = material('Graphite keycaps', (.07,.09,.08), .35, .34)
mint = material('Phosphor mint', (.49,.79,.62), .1, .3, 1.2)
dim = material('Muted phosphor', (.08,.23,.15), .15, .45, .7)
lightkey = material('Mint keycaps', (.43,.64,.51), .35, .34)

def box(name, loc, scale, mat, bevel=.05):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod=obj.modifiers.new('Machined radii', 'BEVEL'); mod.width=bevel; mod.segments=4
        obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return obj

box('Monitor enclosure', (0,0,2.03), (3.18,.40,2.15), shell, .12)
box('Bezel chamfer', (0,-.217,2.06), (3.01,.055,1.96), edge, .065)
box('Inset display glass', (0,-.251,2.09), (2.86,.036,1.79), black, .035)
box('Display lower chin', (0,-.242,1.11), (2.89,.035,.15), shell, .025)
box('Stand upright', (0,.08,.76), (.40,.28,.81), shell, .04)
box('Stand inset', (.015,-.069,.75), (.21,.012,.55), edge, .012)
box('Weighted base', (0,-.03,.34), (1.35,.91,.13), shell, .06)
box('Base polished edge', (0,-.06,.29), (1.27,.84,.018), edge, .014)
box('Power LED', (1.27,-.272,1.105), (.043,.008,.018), mint, .006)
# Side ventilation slots and machined case details.
for i in range(9):
    box('Vent %02d'%i,(1.588,.045,1.58+i*.11),(.009,.17,.032),black,.012)
for x in [-1.39,1.39]:
    box('Lower bezel fastener',(x,-.268,1.11),(.026,.008,.026),edge,.008)
# Crisp UI geometry on the screen: editor chrome, pixel monogram and code.
for x in [-1.28,-1.17,-1.06]:
    box('Window pixel',(x,-.275,2.84),(.042,.008,.042),mint if x==-1.28 else dim,.003)
box('Header divider',(0,-.275,2.72),(2.58,.008,.009),dim,.002)
font={'A':['01110','10001','10001','11111','10001','10001','10001'], 'L':['10000','10000','10000','10000','10000','10000','11111']}
for n,ch in enumerate('AL'):
    for row,line in enumerate(font[ch]):
        for col,v in enumerate(line):
            if v=='1': box('Phosphor pixel',(-1.19+(n*6+col)*.092,-.278,2.50-row*.092),(.078,.009,.078),mint,.002)
for row, lengths in enumerate([[.36,.29],[.24,.40],[.17,.29,.13],[.31,.17],[.20,.39]]):
    start=.10
    for j,length in enumerate(lengths):
        box('Code segment',(start+length/2,-.278,2.49-row*.14),(length,.009,.034),mint if j==0 else dim,.004)
        start+=length+.07
for row,length in enumerate([1.42,1.10,.74]):
    box('Terminal line',(-1.23+length/2,-.278,1.66-row*.12),(length,.009,.025),dim,.003)
box('Terminal cursor',(-.39,-.28,1.42),(.07,.009,.08),mint,.002)
# A compact keyboard with individual sculpted caps, mint escape and return keys.
box('Keyboard chassis',(0,-1.16,.27),(2.88,1.00,.18),shell,.09)
box('Keyboard top plate',(0,-1.16,.371),(2.70,.86,.035),black,.035)
for row in range(4):
    for col in range(13):
        x=-1.23+col*.204
        y=-.85-row*.194
        mat=lightkey if (row==0 and col==0) or (row==2 and col==12) else key
        box('Key %d %02d'%(row,col),(x,y,.414),(.178,.166,.075),mat,.025)
        if row<3:
            box('Key legend',(x-.035,y+.025,.454),(.035,.009,.003),dim,.001)
# Replace the middle keys of the bottom row with a proper spacebar.
for obj in list(scene.objects):
    if obj.name in ['Key 3 %02d'%i for i in range(3,10)]: bpy.data.objects.remove(obj,do_unlink=True)
box('Spacebar',(-.006,-1.432,.414),(1.40,.166,.075),key,.025)
# Lighting on a transparent background, for seamless placement over the profile grid.
world=bpy.data.worlds.new('Black studio'); scene.world=world; world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.035,.045,.04,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.35

def area(name,loc,power,color,size,target=(0,0,1.5)):
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.color=color; data.shape='DISK'; data.size=size
    obj=bpy.data.objects.new(name,data); scene.collection.objects.link(obj); obj.location=loc
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
area('Large softbox',(-3,-4,7),650,(.82,1,.9),5)
area('Mint rim',(4,2,5),1000,(.58,1,.77),3)
area('Front fill',(2,-4,2),150,(.85,.94,1),4)
camdata=bpy.data.cameras.new('Orthographic product camera'); cam=bpy.data.objects.new('Orthographic product camera',camdata)
scene.collection.objects.link(cam); cam.location=(5,-9,5.1)
cam.rotation_euler=(Vector((0,-.35,1.6))-cam.location).to_track_quat('-Z','Y').to_euler()
camdata.type='ORTHO'; camdata.ortho_scale=4.9; scene.camera=cam
scene.render.engine='CYCLES'; scene.cycles.samples=64; scene.cycles.use_denoising=True
scene.render.resolution_x=1200; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(OUT/'computer.png')
scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'computer.blend'))
print('Built workstation:',len(scene.objects),'objects. Ready to render.')
if '--render' in sys.argv:
    bpy.ops.render.render(write_still=True)
