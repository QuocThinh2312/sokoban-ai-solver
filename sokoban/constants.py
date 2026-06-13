from typing import Dict, Tuple, Final

WALL: Final[str] = "#"
PLAYER: Final[str] = "@"
PLAYER_ON_GOAL: Final[str] = "+"
BOX: Final[str] = "$"
BOX_ON_GOAL: Final[str] = "*"
GOAL: Final[str] = "."
FLOOR: Final[str] = " "

ACTIONS: Final[Dict[str, Tuple[int, int]]] = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}

SIDEBAR_WIDTH: Final[int] = 260
DASHBOARD_WIDTH: Final[int] = 270
HEADER_HEIGHT: Final[int] = 60
FPS: Final[int] = 60

MIN_SPEED_MS: Final[int] = 10     
MAX_SPEED_MS: Final[int] = 500    

DEFAULT_SPEED_MS: Final[int] = 250

COLOR_BG: Final[Tuple[int, int, int]] = (15, 15, 20)                
COLOR_PANEL: Final[Tuple[int, int, int]] = (35, 35, 45)             
COLOR_BORDER_LIGHT: Final[Tuple[int, int, int]] = (100, 100, 120)   
COLOR_BORDER_DARK: Final[Tuple[int, int, int]] = (15, 15, 20)       
COLOR_BORDER: Final[Tuple[int, int, int]] = (70, 70, 90)            

COLOR_TEXT: Final[Tuple[int, int, int]] = (250, 250, 250)           
COLOR_TEXT_DIM: Final[Tuple[int, int, int]] = (170, 170, 190)       
COLOR_TEXT_FAINT: Final[Tuple[int, int, int]] = (100, 100, 120)

COLOR_PRIMARY: Final[Tuple[int, int, int]] = (255, 204, 0)          
COLOR_PRIMARY_DIM: Final[Tuple[int, int, int]] = (160, 120, 0)      
COLOR_SECONDARY: Final[Tuple[int, int, int]] = (0, 220, 255)        
COLOR_TERTIARY: Final[Tuple[int, int, int]] = (50, 255, 100)        
COLOR_HIGHLIGHT: Final[Tuple[int, int, int]] = (255, 50, 100)       

COLOR_PLAYER_FALLBACK: Final[Tuple[int, int, int]] = (255, 204, 0)
COLOR_BOX_FALLBACK: Final[Tuple[int, int, int]] = (180, 100, 30)
COLOR_BOX_ON_GOAL_FALLBACK: Final[Tuple[int, int, int]] = (50, 255, 100)
COLOR_GOAL_FALLBACK: Final[Tuple[int, int, int]] = (0, 220, 255)

ALGORITHMS: Final[Tuple[str, ...]] = (
    "A*", 
    "Weighted A*", 
    "UCS", 
    "Beam Search", 
    "BFS", 
    "Greedy", 
    "DFS"
)