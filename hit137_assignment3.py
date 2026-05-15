"""
-------------------------------------------------------------------------------
    GROUP ASSIGNMENT 3 ("Spot the Hidden Differences Game by DAN/EXT 31") 
    HIT137 - Software Now
-------------------------------------------------------------------------------

    Group Name: DAN/EXT 31
    Group Members:
    JOYAL BIJU         - s400926
    VAN ANH VU         - s401462
    SOWROV CHANDRA DAS - s396166

GitHub Repository: [Add your repository link here]

Project info:
    Build a desktop application where two nearly identical images are displayed side by side. 
    One image is original, the other is a programmatically altered copy containing hidden differences.
    The player clicks on the modified image to locate the differences, 
    and the application validates each click against the known difference regions.
---------------------------------------------------------------------------------
"""
''' libraries used for our project "Spot the difference game'''
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import random
import os
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional
from dataclasses import dataclass

''' settings for our game'''
@dataclass
class Game_Setting:
    TOTAL_DIFFERENCE: int = 5
    MAXIMUM_WRONG_CLICKS: int = 3
    CLICK_RANGE: int = 15
    MINIMUM_BOX_SIZE: int = 30
    MAXIMUM_BOX_SIZE: int = 80
    IMAGE_FILES: Tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.bmp')

'''parent class for all objects in our game'''
class game_Asset(ABC):
    
    def __init__(self, x: int, y: int):
        if not isinstance(x, int) or not isinstance(y, int):
            raise TypeError("Coordinates must be integers")
        if x < 0 or y < 0:
            raise ValueError("Coordinates cannot be negative")
        
        self.x = x
        self.y = y
    
    @abstractmethod
    def draw(self, canvas: tk.Canvas) -> None:
        pass
    
    @abstractmethod
    def Contains_point(self, point_x: int, point_y: int, 
                      tolerance: int = 0) -> bool:
        pass

class Variance(ABC):
    
    def __init__(self, x: int, y: int, width: int, height: int):
        for parameter_name, parameter_value in [('x', x), ('y', y), 
                                        ('width', width), ('height', height)]:
            if not isinstance(parameter_value, int):
                raise TypeError(f"{parameter_name} must be an integer")
            if parameter_value < 0:
                raise ValueError(f"{parameter_name} cannot be negative")
        
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.found = False
    
    @abstractmethod
    def apply(self, image: np.ndarray) -> np.ndarray:
        pass
    
    def Get_Area(self) -> Tuple[int, int, int, int]:
        left_x = max(0, self.x - self.width // 2)
        right_x = self.x + self.width // 2
        top_y = max(0, self.y - self.height // 2)
        bottom_y = self.y + self.height // 2
        return left_x, top_y, right_x, bottom_y
    
    def Contains_point(self, point_x: int, point_y: int, 
                      tolerance: int = 15) -> bool:
        return (abs(point_x - self.x) <= self.width / 2 + tolerance and 
                abs(point_y - self.y) <= self.height / 2 + tolerance)

'''Different types of hidden spots in our game'''
class color_Difference(Variance):
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        left_x, top_y, right_x, bottom_y = self.Get_Area()
        
        if right_x <= left_x or bottom_y <= top_y:
            return image
        
        right_x = min(right_x, image.shape[1])
        bottom_y = min(bottom_y, image.shape[0])
        
        Selected_Area = image[top_y:bottom_y, left_x:right_x].copy()
        if Selected_Area.size == 0:
            return image
        
        hsv = cv2.cvtColor(Selected_Area, cv2.COLOR_BGR2HSV).astype(np.float32)
        hue_shift = random.randint(-20, 20)
        hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 180
        sat_shift = random.randint(-30, 30)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] + sat_shift, 0, 255)
        hsv = hsv.astype(np.uint8)
        modified_region = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        image[top_y:bottom_y, left_x:right_x] = modified_region
        return image

class Shape_change(Variance):
    ''' Adds circle or rectangle to a selected area in the image'''
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        left_x, top_y, right_x, bottom_y = self.Get_Area()
        
        if right_x <= left_x or bottom_y <= top_y:
            return image
        
        right_x = min(right_x, image.shape[1])
        bottom_y = min(bottom_y, image.shape[0])
        shape_type = random.choice(['circle', 'rectangle'])
        center_x = (left_x + right_x) // 2
        center_y = (top_y + bottom_y) // 2
        radius = min(right_x - left_x, bottom_y - top_y) // 3
        
        ''' random color in BGR format'''
        color = (random.randint(50, 200), 
                random.randint(50, 200), 
                random.randint(50, 200))
        
        '''draw shape'''
        if shape_type == 'circle':
            cv2.circle(image, (center_x, center_y), radius, color, -1)
        else:  # rectangle
            cv2.rectangle(image, (left_x, top_y), (right_x, bottom_y), color, -1)
        return image

class Texture_change(Variance):
    '''Adds grainy effect to the image'''
    
    def apply(self, image: np.ndarray) -> np.ndarray:
        left_x, top_y, right_x, bottom_y = self.Get_Area()
        if right_x <= left_x or bottom_y <= top_y:
            return image
        
        right_x = min(right_x, image.shape[1])
        bottom_y = min(bottom_y, image.shape[0])
        
        Selected_Area = image[top_y:bottom_y, left_x:right_x].copy()
        if Selected_Area.size == 0:
            return image
        
        noise = np.random.normal(0, 25, Selected_Area.shape).astype(np.float32)
        noisy_region = np.clip(Selected_Area.astype(np.float32) + noise, 0, 255)
        image[top_y:bottom_y, left_x:right_x] = noisy_region.astype(np.uint8)
        
        return image

class Circle_identification(game_Asset):
    ''' Draws a circle when a spot are found'''
    
    def __init__(self, x: int, y: int, radius: int = 20, color: str = "red"):
        super().__init__(x, y)
        if radius < 0:
            raise ValueError("Radius cannot be negative")
        self.radius = radius
        self.color = color
    
    def draw(self, canvas: tk.Canvas) -> None:
        '''Draw circle marker on canvas'''
        canvas.create_oval(
            self.x - self.radius, self.y - self.radius,
            self.x + self.radius, self.y + self.radius,
            outline=self.color, width=3
        )
    
    def Contains_point(self, point_x: int, point_y: int, 
                      tolerance: int = 15) -> bool:
        distance = np.sqrt((point_x - self.x) ** 2 + (point_y - self.y) ** 2)
        return distance <= self.radius + tolerance

'''Image editing and generating difference in the game'''
class Image_editing:
    DIFFERENCE_TYPES = [color_Difference, Shape_change, Texture_change]
    
    def __init__(self, config: Game_Setting = None):
        self.config = config if config else Game_Setting()
        self.Main_image = None
        self.Edited_image = None
        self.Hidden_Spots: List[Variance] = []
        self._image_shape = None
    
    def validate_image_file(self, filepath: str) -> Tuple[bool, str]:
        if not filepath or not isinstance(filepath, str):
            return False, "No file selected"
        
        if not os.path.exists(filepath):
            return False, "File does not exist"
        
        file_ext = os.path.splitext(filepath)[1].lower()
        if file_ext not in self.config.IMAGE_FILES:
            valid_str = ', '.join(self.config.IMAGE_FILES)
            return False, f"Invalid file type. Supported: {valid_str}"
        
        if not os.access(filepath, os.R_OK):
            return False, "File is not readable"
        
        return True, "Valid"
    
    def load_image(self, filepath: str) -> bool:
        is_valid, message = self.validate_image_file(filepath)
        if not is_valid:
            raise ValueError(message)
        
        try:
            self.Main_image = cv2.imread(filepath)
            if self.Main_image is None:
                raise IOError("Could not decode image file")
            
            self._image_shape = self.Main_image.shape
            return True
        except Exception as e:
            raise IOError(f"Error loading image: {str(e)}")
    
    def _Spots_touched(self, new_spots: Variance, 
                      old_spots: List[Variance]) -> bool:
        new_bounds = new_spots.Get_Area()
        for existing in old_spots:
            existing_bounds = existing.Get_Area()
            
            if (new_bounds[0] - 20 < existing_bounds[2] and
                new_bounds[2] + 20 > existing_bounds[0] and
                new_bounds[1] - 20 < existing_bounds[3] and
                new_bounds[3] + 20 > existing_bounds[1]):
                return True
        
        return False
    
    def _Create_Spot(self, height: int, width: int) -> Optional[Variance]:
        region_width = random.randint(
            self.config.MINIMUM_BOX_SIZE, 
            self.config.MAXIMUM_BOX_SIZE
        )
        region_height = random.randint(
            self.config.MINIMUM_BOX_SIZE, 
            self.config.MAXIMUM_BOX_SIZE
        )
        
        max_x = width - region_width // 2
        max_y = height - region_height // 2
        
        if max_x <= region_width // 2 or max_y <= region_height // 2:
            return None
        
        x = random.randint(region_width // 2, max_x)
        y = random.randint(region_height // 2, max_y)
        
        diff_class = random.choice(self.DIFFERENCE_TYPES)
        return diff_class(x, y, region_width, region_height)
    
    def Create_Game_Image(self) -> bool:
        if self.Main_image is None:
            raise ValueError("No image loaded. Load image first.")
        
        '''Cloning original Images'''
        self.Edited_image = self.Main_image.copy()
        self.Hidden_Spots = []
        
        height, width = self.Main_image.shape[:2]
        max_attempts = 200
        attempts = 0
        
        while len(self.Hidden_Spots) < self.config.TOTAL_DIFFERENCE and attempts < max_attempts:
            attempts += 1
            
            spot = self._Create_Spot(height, width)
            if spot is None:
                continue
            
            if self._Spots_touched(spot, self.Hidden_Spots):
                continue
            
            self.Edited_image = spot.apply(self.Edited_image)
            self.Hidden_Spots.append(spot)
        
        if len(self.Hidden_Spots) < self.config.TOTAL_DIFFERENCE:
            raise RuntimeError(
                f"Could only create {len(self.Hidden_Spots)} Hidden_Spots. "
                f"Image may be too small."
            )
        
        return True
    
    def get_original_image(self) -> Optional[np.ndarray]:
        '''Get original image'''
        return self.Main_image.copy() if self.Main_image is not None else None
    
    def altered_image(self) -> Optional[np.ndarray]:
        '''Get modified image'''
        return self.Edited_image.copy() if self.Edited_image is not None else None
    
    def Check_spots_clicked(self, point_x: int, point_y: int) -> Optional[Variance]:
        for spot in self.Hidden_Spots:
            if not spot.found and spot.Contains_point(
                point_x, point_y, self.config.CLICK_RANGE
            ):
                return spot
        return None
    
    def get_remaining_differences(self) -> int:
        '''Returns how many spots are still left'''
        return sum(1 for spot in self.Hidden_Spots if not spot.found)

class Game_manager:
    '''Manages game progress and score'''
    
    def __init__(self, config: Game_Setting = None):
        '''Initialize game state'''
        self.config = config if config else Game_Setting()
        self.reset_image_state()
        self.total_score = 0
        self.images_played = 0
    
    def reset_image_state(self) -> None:
        self.mistakes = 0
        self.found_count = 0
        self.game_over = False
    
    def Wrong_Click(self) -> bool:
        self.mistakes += 1
        if self.mistakes >= self.config.MAXIMUM_WRONG_CLICKS:
            self.game_over = True
            self._end_image()
            return False
        return True
    
    def Found_spot(self) -> bool:
        self.found_count += 1
        if self.found_count >= self.config.TOTAL_DIFFERENCE:
            self.game_over = True
            self._end_image()
            return True
        return False
    
    def _end_image(self) -> None:
        if self.found_count == self.config.TOTAL_DIFFERENCE:
            points_earned = self.config.TOTAL_DIFFERENCE
        else:
            points_earned = self.found_count
        
        self.total_score += points_earned
        self.images_played += 1
    
    def get_score_info(self) -> str:
        return f"Score: {self.total_score} | Images: {self.images_played}"

'''Graphical user interface'''
class SpotDifference_game:
    '''Main GUI interface'''
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Spot the Hidden Difference by DAN/EXT 31")
        self.root.geometry("1400x750")
        
        self.config = Game_Setting()
        self.processor = Image_editing(self.config)
        self.game_state = Game_manager(self.config)
        
        self.original_photo = None
        self.modified_photo = None
        self.canvas_modified = None
        self.markers = []
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        '''Create user interface'''
        Game_frame = tk.Frame(self.root, bg="#2b2b2b")
        Game_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        Top_frame = tk.Frame(Game_frame, bg="#2b2b2b")
        Top_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = tk.Label(
            Top_frame, 
            text="Spot the difference game",
            font=("Arial", 20, "bold"),
            bg="#2b2b2b",
            fg="#ff6b6b"
        )
        title_label.pack(side=tk.LEFT)
        
        score_label = tk.Label(
            Top_frame,
            text=self.game_state.get_score_info(),
            font=("Arial", 12),
            bg="#2b2b2b",
            fg="#ffff00",
            name="score_label"
        )
        score_label.pack(side=tk.RIGHT)
        self.score_label = score_label

        Picture_Frame = tk.Frame(Game_frame, bg="#1a1a1a")
        Picture_Frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        left_frame = tk.Frame(Picture_Frame, bg="#1a1a1a")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(left_frame, text="ORIGINAL", font=("Arial", 10, "bold"),
                bg="#1a1a1a", fg="#888").pack()
        
        self.canvas_original = tk.Canvas(
            left_frame, bg="gray", cursor="cross"
        )
        self.canvas_original.pack(fill=tk.BOTH, expand=True)
        
        right_frame = tk.Frame(Picture_Frame, bg="#1a1a1a")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        tk.Label(right_frame, text="MODIFIED (CLICK TO FIND)", 
                font=("Arial", 10, "bold"),
                bg="#1a1a1a", fg="#888").pack()
        
        self.canvas_modified = tk.Canvas(
            right_frame, bg="gray", cursor="cross"
        )
        self.canvas_modified.pack(fill=tk.BOTH, expand=True)
        self.canvas_modified.bind("<Button-1>", self._on_canvas_click)
        
        Information_Frame = tk.Frame(Game_frame, bg="#2b2b2b")
        Information_Frame.pack(fill=tk.X, pady=10)
        
        self.status_label = tk.Label(
            Information_Frame,
            text="Load an image to start",
            font=("Arial", 11),
            bg="#2b2b2b",
            fg="#ffffff"
        )
        self.status_label.pack(side=tk.LEFT)
        
        self.remaining_label = tk.Label(
            Information_Frame,
            text="",
            font=("Arial", 11, "bold"),
            bg="#2b2b2b",
            fg="#00ff00"
        )
        self.remaining_label.pack(side=tk.RIGHT)
        
        Button_Frame = tk.Frame(Game_frame, bg="#2b2b2b")
        Button_Frame.pack(fill=tk.X, pady=10)
        
        buttons_config = [
            ("Load Image", self._load_image, "#4CAF50"),
            ("Reveal All", self._reveal_all, "#FF9800"),
            ("New Game", self._new_game, "#2196F3"),
            ("Exit", self.root.quit, "#f44336"),
        ]
        
        for text, command, color in buttons_config:
            btn = tk.Button(
                Button_Frame,
                text=text,
                command=command,
                font=("Arial", 10, "bold"),
                bg=color,
                fg="white",
                padx=15,
                pady=8,
                relief=tk.FLAT
            )
            btn.pack(side=tk.LEFT, padx=5)
    
    def _load_image(self) -> None:
        '''Load image'''
        filepath = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png *.bmp"),
                ("All Files", "*.*")
            ]
        )
        
        if not filepath:
            return
        
        try:
            self.processor.load_image(filepath)
            self.processor.Create_Game_Image()
            self.game_state.reset_image_state()
            self.markers = []
            self._display_images()
            self._Update_Image()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image:\n{str(e)}")
    
    def _display_images(self) -> None:
        '''Display original and modified image'''
        original = self.processor.get_original_image()
        modified = self.processor.altered_image()
        
        if original is None or modified is None:
            return
        
        display_height = 500
        aspect = original.shape[1] / original.shape[0]
        display_width = int(display_height * aspect)
        
        RGB_original = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
        RGB_changed = cv2.cvtColor(modified, cv2.COLOR_BGR2RGB)
        
        original_resized = cv2.resize(RGB_original, (display_width, display_height))
        modified_resized = cv2.resize(RGB_changed, (display_width, display_height))
        
        original_pil = Image.fromarray(original_resized)
        modified_pil = Image.fromarray(modified_resized)
        
        self.original_photo = ImageTk.PhotoImage(original_pil)
        self.modified_photo = ImageTk.PhotoImage(modified_pil)
        
        self.canvas_original.create_image(
            0, 0, image=self.original_photo, anchor=tk.NW
        )
        self.canvas_modified.create_image(
            0, 0, image=self.modified_photo, anchor=tk.NW
        )
        
        self.scale_x = display_width / self.processor._image_shape[1]
        self.scale_y = display_height / self.processor._image_shape[0]
    
    def _on_canvas_click(self, event) -> None:
        '''Handle click on modified image'''
        if not self.processor.Hidden_Spots or self.game_state.game_over:
            return
        
        image_x = int(event.x / self.scale_x)
        image_y = int(event.y / self.scale_y)
        
        clicked_spot = self.processor.Check_spots_clicked(image_x, image_y)
        
        if clicked_spot:
            clicked_spot.found = True
            is_complete = self.game_state.Found_spot()
            
            marker = Circle_identification(
                int(event.x), int(event.y), radius=15, color="red"
            )
            self.markers.append(marker)
            marker.draw(self.canvas_modified)
            marker.draw(self.canvas_original)
            
            if is_complete:
                messagebox.showinfo(
                    "Success!",
                    f"All Hidden_Spots found!\n\n"
                    f"Mistakes: {self.game_state.mistakes}\n"
                    f"Points earned: {self.game_state.found_count}"  # our group believes we shoudn't give negative marking
                )
            
            self._Update_Image()
        else:
            if not self.game_state.Wrong_Click():
                points_earned = self.game_state.found_count  # No subtraction - just count found
                messagebox.showwarning(
                    "Game Over",
                    f"Maximum mistakes reached!\n\n"
                    f"Found: {self.game_state.found_count}/{self.config.TOTAL_DIFFERENCE}\n"
                    f"Points earned: {points_earned}\n"
                    f"Load a new image to continue."
                )
                self.remaining_label.config(fg="#ff0000")
            
            self._Update_Image()
    
    def _reveal_all(self) -> None:
         # Reveal all remaining HiddenSpots
        if not self.processor.Hidden_Spots or self.game_state.game_over:
            messagebox.showinfo("Info", "Load an image first or game is over")
            return
        
        for spot in self.processor.Hidden_Spots:
            if not spot.found:
                marker = Circle_identification(
                    int(spot.x * self.scale_x),
                    int(spot.y * self.scale_y),
                    radius=15,
                    color="blue"
                )
                self.markers.append(marker)
                marker.draw(self.canvas_modified)
                marker.draw(self.canvas_original)
                spot.found = True
        
        self.game_state.game_over = True
        self._Update_Image()
        messagebox.showinfo("Revealed", "All Hidden_Spots revealed!")
    
    def _new_game(self) -> None:
        '''Start new game'''
        self._load_image()
    
    def _Update_Image(self) -> None:
        '''Update status'''
        remaining = self.processor.get_remaining_differences()
        
        status_text = f"Mistakes: {self.game_state.mistakes}/{self.config.MAXIMUM_WRONG_CLICKS}"
        self.status_label.config(text=status_text)
        
        remaining_text = f"Remaining: {remaining}"
        self.remaining_label.config(text=remaining_text)
        
        score_text = self.game_state.get_score_info()
        self.score_label.config(text=score_text)

def main():
    '''Launch Spot the difference game by DAN/EXT 31'''
    root = tk.Tk()
    app = SpotDifference_game(root)
    root.mainloop()

if __name__ == "__main__":
    main()