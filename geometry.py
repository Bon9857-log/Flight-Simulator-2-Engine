# Darkstar 3D model geometry
# 11 vertices, 16 triangular faces

VERTICES = [
    ("nose", 0, 0, 50),
    ("fuselage_top_front", -8, 8, 30),
    ("fuselage_top_back", -8, 8, -40),
    ("fuselage_bottom_front", -8, -8, 30),
    ("fuselage_bottom_back", -8, -8, -40),
    ("wing_left_front", -25, 0, 20),
    ("wing_left_back", -25, 0, -20),
    ("wing_right_front", 25, 0, 20),
    ("wing_right_back", 25, 0, -20),
    ("tail_top", 0, 8, -50),
    ("tail_bottom", 0, -8, -50),
]

FACES = [
    # Nose cone (front faces)
    (0, 1, 3, (200, 100, 50)),    # nose to top-front to bottom-front
    
    # Fuselage top faces
    (1, 2, 4, (180, 80, 40)),     # top-front to top-back to bottom-back
    (1, 4, 3, (180, 80, 40)),     # top-front to bottom-back to bottom-front
    
    # Fuselage bottom faces
    (3, 4, 2, (160, 60, 20)),     # bottom-front to bottom-back to top-back
    
    # Left wing
    (1, 5, 3, (150, 150, 150)),   # fuselage-top to wing-front to fuselage-bottom
    (5, 6, 3, (140, 140, 140)),   # wing-front to wing-back to fuselage-bottom
    (1, 6, 2, (140, 140, 140)),   # fuselage-top to wing-back to fuselage-top-back
    (5, 6, 2, (130, 130, 130)),   # wing-front to wing-back to fuselage-top-back
    
    # Right wing
    (1, 7, 3, (150, 150, 150)),   # fuselage-top to wing-front to fuselage-bottom
    (7, 8, 3, (140, 140, 140)),   # wing-front to wing-back to fuselage-bottom
    (1, 8, 2, (140, 140, 140)),   # fuselage-top to wing-back to fuselage-top-back
    (7, 8, 2, (130, 130, 130)),   # wing-front to wing-back to fuselage-top-back
    
    # Tail cone
    (2, 9, 4, (200, 100, 50)),    # fuselage-top-back to tail-top to fuselage-bottom-back
    (4, 9, 10, (200, 100, 50)),   # fuselage-bottom-back to tail-top to tail-bottom
    (2, 4, 10, (180, 80, 40)),    # fuselage-top-back to fuselage-bottom-back to tail-bottom
    (2, 10, 9, (180, 80, 40)),    # fuselage-top-back to tail-bottom to tail-top
]
