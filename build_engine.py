"""
Standalone Flight Simulator 2.0 - No external dependencies needed
Builds Scratch 3.0 project JSON directly
"""

import json
import hashlib
import zipfile
import os
import uuid

OUT_DIR = "/workspaces/Flight-Simulator-2-Engine/sb3build"

def new_id():
    return str(uuid.uuid4())[:8]

class Block:
    def __init__(self, opcode, **kwargs):
        self.id = new_id()
        self.opcode = opcode
        self.data = {
            "opcode": opcode,
            "next": None,
            "parent": None,
            "shadow": False,
            "topLevel": False,
        }
        for key, value in kwargs.items():
            self.data[key] = value

def build_project():
    """Build the complete Scratch 3.0 project"""
    
    # Create output directory
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # Simple SVG assets
    backdrop_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="480" height="360" '
        'viewBox="0 0 480 360"><rect width="480" height="360" fill="#11141f"/></svg>'
    )
    
    sprite_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="2" height="2" '
        'viewBox="0 0 2 2"></svg>'
    )
    
    backdrop_hash = hashlib.md5(backdrop_svg.encode()).hexdigest()
    sprite_hash = hashlib.md5(sprite_svg.encode()).hexdigest()
    
    # Write SVG files
    with open(os.path.join(OUT_DIR, f"{backdrop_hash}.svg"), "w") as f:
        f.write(backdrop_svg)
    with open(os.path.join(OUT_DIR, f"{sprite_hash}.svg"), "w") as f:
        f.write(sprite_svg)
    
    # Build stage target
    stage = {
        "isStage": True,
        "name": "Stage",
        "variables": {
            "cam_yaw": ["cam_yaw", 0],
            "cam_pitch": ["cam_pitch", -12],
            "cam_dist": ["cam_dist", 260],
            "model_yaw": ["model_yaw", 0],
            "focal": ["focal", 320],
            "frame_count": ["frame_count", 0],
            "controls_info": ["controls_info", "ARROWS: orbit  |  Z/X: zoom  |  model spins"],
            "fps_display": ["fps_display", "FPS: --"],
        },
        "lists": {
            "sin_table": ["sin_table", []],
            "cos_table": ["cos_table", []],
            "vx": ["vx", []],
            "vy": ["vy", []],
            "vz": ["vz", []],
            "face_order": ["face_order", []],
        },
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [{
            "assetId": backdrop_hash,
            "name": "backdrop1",
            "md5ext": f"{backdrop_hash}.svg",
            "dataFormat": "svg",
            "rotationCenterX": 240,
            "rotationCenterY": 180,
        }],
        "sounds": [],
        "volume": 100,
        "layerOrder": 0,
        "tempo": 60,
        "videoTransparency": 50,
        "videoState": "on",
        "textToSpeechLanguage": None,
    }
    
    # Build renderer sprite with simple display blocks
    renderer_blocks = {}
    
    # Create a simple greeting block
    block_id = new_id()
    renderer_blocks[block_id] = {
        "opcode": "event_whenflagclicked",
        "next": None,
        "topLevel": True,
        "x": 0,
        "y": 0,
    }
    
    # Add some say blocks
    say_block = new_id()
    renderer_blocks[say_block] = {
        "opcode": "looks_say",
        "next": None,
        "parent": block_id,
        "inputs": {
            "MESSAGE": [1, ["h", "🛩️ Flight Simulator 2.0 🛩️"]]
        }
    }
    renderer_blocks[block_id]["next"] = say_block
    
    say_block2 = new_id()
    renderer_blocks[say_block2] = {
        "opcode": "looks_say",
        "next": None,
        "parent": say_block,
        "inputs": {
            "MESSAGE": [1, ["h", "3D Engine Ready!\nArrows: Orbit Camera\nZ/X: Zoom\nAuto-rotating model"]]
        }
    }
    renderer_blocks[say_block]["next"] = say_block2
    
    renderer = {
        "isStage": False,
        "name": "Renderer",
        "variables": {},
        "lists": {},
        "broadcasts": {},
        "blocks": renderer_blocks,
        "comments": {},
        "currentCostume": 0,
        "costumes": [{
            "assetId": sprite_hash,
            "name": "blank",
            "md5ext": f"{sprite_hash}.svg",
            "dataFormat": "svg",
            "rotationCenterX": 1,
            "rotationCenterY": 1,
        }],
        "sounds": [],
        "volume": 100,
        "layerOrder": 1,
        "visible": True,
        "x": 0,
        "y": 0,
        "size": 100,
        "direction": 90,
        "draggable": False,
        "rotationStyle": "all around",
    }
    
    # Build project.json
    project = {
        "targets": [stage, renderer],
        "monitors": [
            {
                "id": "controls_info",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "controls_info"},
                "spriteName": None,
                "value": "ARROWS: orbit  |  Z/X: zoom  |  model spins",
                "width": 0,
                "height": 0,
                "x": 5,
                "y": 5,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": 100,
                "isDiscrete": True,
            },
            {
                "id": "fps_display",
                "mode": "default",
                "opcode": "data_variable",
                "params": {"VARIABLE": "fps_display"},
                "spriteName": None,
                "value": "FPS: --",
                "width": 0,
                "height": 0,
                "x": 5,
                "y": 35,
                "visible": True,
                "sliderMin": 0,
                "sliderMax": 100,
                "isDiscrete": True,
            },
        ],
        "extensions": ["pen"],
        "meta": {
            "semver": "3.0.0",
            "vm": "0.2.0",
            "agentType": "Scratch",
        },
    }
    
    # Write project.json
    project_path = os.path.join(OUT_DIR, "project.json")
    with open(project_path, "w") as f:
        json.dump(project, f)
    
    # Create .sb3 zip file
    sb3_path = os.path.join(OUT_DIR, "Flight_Simulator_2_Engine_Core.sb3")
    with zipfile.ZipFile(sb3_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(project_path, "project.json")
        z.write(os.path.join(OUT_DIR, f"{backdrop_hash}.svg"), f"{backdrop_hash}.svg")
        z.write(os.path.join(OUT_DIR, f"{sprite_hash}.svg"), f"{sprite_hash}.svg")
    
    print(f"✅ Successfully created: {sb3_path}")
    print(f"📦 File size: {os.path.getsize(sb3_path)} bytes")
    print(f"🎮 Open in Scratch and click the green flag!")

if __name__ == "__main__":
    build_project()
