from typing import Dict, List, Tuple

WALL: str = "#"
PLAYER: str = "@"
PLAYER_ON_GOAL: str = "+"
BOX: str = "$"
BOX_ON_GOAL: str = "*"
GOAL: str = "."
FLOOR: str = " "

ACTIONS: Dict[str, Tuple[int, int]] = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}

SIDEBAR_WIDTH: int = 250
DASHBOARD_WIDTH: int = 270
HEADER_HEIGHT: int = 60
FPS: int = 60

MIN_SPEED_MS: int = 10     
MAX_SPEED_MS: int = 500    

DEFAULT_SPEED_MS: int = 250

COLOR_BG: Tuple[int, int, int] = (15, 15, 20)                
COLOR_PANEL: Tuple[int, int, int] = (35, 35, 45)             
COLOR_BORDER_LIGHT: Tuple[int, int, int] = (100, 100, 120)   
COLOR_BORDER_DARK: Tuple[int, int, int] = (15, 15, 20)       
COLOR_BORDER: Tuple[int, int, int] = (70, 70, 90)            

COLOR_TEXT: Tuple[int, int, int] = (250, 250, 250)           
COLOR_TEXT_DIM: Tuple[int, int, int] = (170, 170, 190)       
COLOR_TEXT_FAINT: Tuple[int, int, int] = (100, 100, 120)

COLOR_PRIMARY: Tuple[int, int, int] = (255, 204, 0)          
COLOR_PRIMARY_DIM: Tuple[int, int, int] = (160, 120, 0)      
COLOR_SECONDARY: Tuple[int, int, int] = (0, 220, 255)        
COLOR_TERTIARY: Tuple[int, int, int] = (50, 255, 100)        
COLOR_HIGHLIGHT: Tuple[int, int, int] = (255, 50, 100)       

COLOR_PLAYER_FALLBACK: Tuple[int, int, int] = (255, 204, 0)
COLOR_BOX_FALLBACK: Tuple[int, int, int] = (180, 100, 30)
COLOR_BOX_ON_GOAL_FALLBACK: Tuple[int, int, int] = (50, 255, 100)
COLOR_GOAL_FALLBACK: Tuple[int, int, int] = (0, 220, 255)

ALGORITHMS: List[str] = ["BFS", "DFS", "UCS", "Greedy", "A*", "IDA*", "Weighted A*", "Beam Search"]