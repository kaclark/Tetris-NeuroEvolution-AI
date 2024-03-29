import arcade
import random
import PIL
import colorama
from colorama import Fore, init
init()#Needed for Windows to use the colorama codes for colors
import numpy as np
import winsound
import pickle

# Set how many rows and columns we will have
ROW_COUNT = 24
COLUMN_COUNT = 10

# This sets the WIDTH and HEIGHT of each grid location
WIDTH = 20
HEIGHT = 20

# This sets the margin between each cell
# and on the edges of the screen.
MARGIN = 1

# Do the math to figure out our screen dimensions
SCREEN_WIDTH = (WIDTH + MARGIN) * COLUMN_COUNT + MARGIN
SCREEN_HEIGHT = (HEIGHT + MARGIN) * ROW_COUNT + MARGIN
SCREEN_TITLE = "Tetris"

colors = [
          (0,   0,   0  ),
          (255, 0,   0  ),
          (0,   150, 0  ),
          (0,   0,   255),
          (255, 120, 0  ),
          (255, 255, 0  ),
          (180, 0,   255),
          (0,   220, 220)
          ]

# Define the shapes of the single parts
tetris_shapes = [
    [[0, 1, 0],
     [1, 1, 1]],

    [[0, 2, 2],
     [2, 2, 0]],

    [[3, 3, 0],
     [0, 3, 3]],

    [[4, 0, 0],
     [4, 4, 4]],

    [[0, 0, 5],
     [5, 5, 5]],

    [[6, 6, 6, 6]],

    [[7, 7],
     [7, 7]]
]


def create_textures():
    texture_list = []
    for color in colors:
        image = PIL.Image.new('RGB', (WIDTH, HEIGHT), color)
        texture_list.append(arcade.Texture(str(color), image=image))
    return texture_list
texture_list = create_textures()

def rotate_clockwise(shape):
    return np.rot90(shape)

def rotate_counter_clockwise(shape):
    np.rot90(shape)
    np.rot90(shape)
    return np.rot90(shape)

def check_collision(board, shape, offset):
    off_x, off_y = offset
    for cy, row in enumerate(shape):
        for cx, cell in enumerate(row):
            try:
                if cell and board[cy + off_y][cx + off_x]:
                    return True
            except IndexError:
                pass
    return False


def remove_row(board, row):
    del board[row]
    return [[0 for i in range(COLUMN_COUNT)]] + board


def join_matrixes(matrix_1, matrix_2, matrix_2_offset):
    offset_x, offset_y = matrix_2_offset
    for cy, row in enumerate(matrix_2):
        for cx, val in enumerate(row):
            try:
                matrix_1[cy + offset_y - 1][cx + offset_x] += val
            except IndexError:
                pass
    return matrix_1


def new_board():
    """ Create a grid of 0's. Add 1's to the bottom for easier collision detection. """
    # Create the main board of 0's
    board = [[0 for x in range(COLUMN_COUNT)] for y in range(ROW_COUNT)]
    # Add a bottom border of 1's
    board += [[1 for x in range(COLUMN_COUNT)]]
    return board


class MyGame(arcade.Window):
    """ Main application class. """

    def __init__(self, width, height, title):
        """ Set up the application. """

        super().__init__(width, height, title)

        #Set Background Color
        arcade.set_background_color(arcade.color.BLACK_LEATHER_JACKET)

        self.board = None
        self.frame_count = 0
        self.game_over = False
        self.paused = False
        self.board_sprite_list = None
        self.score = 0

    def new_stone(self):
        self.stone = random.choice(tetris_shapes)
        self.stone_x = int(COLUMN_COUNT / 2 - len(self.stone[0]) / 2)
        #self.stone_x = random.randint(0, 8)
        self.stone_y = 0

        if self.stone[0][0] != 0:
            self.shape = self.stone[0][0]
        else:
            self.shape = self.stone[1][1]
        self.rotation = 1

        if check_collision(self.board, self.stone, (self.stone_x, self.stone_y)):
            self.restart()


    def setup(self):
        self.board = new_board()

        self.board_sprite_list = arcade.SpriteList()
        for row in range(len(self.board)):
            for column in range(len(self.board[0])):
                sprite = arcade.Sprite()
                for texture in texture_list:
                    sprite.append_texture(texture)
                sprite.set_texture(0)
                sprite.center_x = (MARGIN + WIDTH) * column + MARGIN + WIDTH // 2
                sprite.center_y = SCREEN_HEIGHT - (MARGIN + HEIGHT) * row + MARGIN + HEIGHT // 2

                self.board_sprite_list.append(sprite)

        self.new_stone()
        self.update_board()
        with open("./data/legend.pickle", "rb") as pickle_in:
            self.net = pickle.load(pickle_in)

    def drop(self):
        """
        Drop the stone down one place.
        Check for collision.
        If collided, then
          join matrixes
          Check for rows we can remove
          Update sprite list with stones
          Create a new stone
        """
        self.stone_y += 1#was 1
        if check_collision(self.board, self.stone, (self.stone_x, self.stone_y)):
            self.board = join_matrixes(self.board, self.stone, (self.stone_x, self.stone_y))
            while True:
                for i, row in enumerate(self.board[:-1]):
                    if 0 not in row:
                        self.board = remove_row(self.board, i)
                        self.score += 1
                        break
                else:
                    break
            self.update_board()
            self.new_stone()

    def rotate_stone(self):
        """ Rotate the stone, check collision. """
        new_stone = rotate_clockwise(self.stone)
        if not check_collision(self.board, new_stone, (self.stone_x, self.stone_y)):
            self.stone = new_stone
            if self.rotation == 4:
                self.rotation = 1
            else:
                self.rotation += 1

    def rotate_stone_counter_clockwise(self):
        """ Rotate the stone, check collision. """
        new_stone = rotate_counter_clockwise(self.stone)
        if not check_collision(self.board, new_stone, (self.stone_x, self.stone_y)):
            self.stone = new_stone
            if self.rotation == 1:
                self.rotation = 4
            else:
                self.rotation -= 1
                
    def update(self, dt):
        """ Update, drop stone if warrented """
        self.frame_count += 1
        if self.frame_count > 1:
            output = self.net.activate(self.output_info())
            max_index = 0
            max = 0
            for d in range(len(output)):  
                if output[d] > max:
                    max = output[d]
                    max_index = d
            self.run_ai(max_index)
            self.drop() 

    def move(self, delta_x):
        """ Move the stone back and forth based on delta x. """
        new_x = self.stone_x + delta_x
        if new_x < 0:
            new_x = 0
        if new_x > COLUMN_COUNT - len(self.stone[0]):
            new_x = COLUMN_COUNT - len(self.stone[0])
        if not check_collision(self.board, self.stone, (new_x, self.stone_y)):
            self.stone_x = new_x

    def on_key_press(self, key, modifiers):
        pass
        # if key == arcade.key.LEFT:
        #     self.move(-1)
        # elif key == arcade.key.RIGHT:
        #     self.move(1)
        # elif key == arcade.key.UP:
        #     self.rotate_stone()
        # elif key == arcade.key.DOWN:
        #     self.rotate_stone_counter_clockwise()

    def run_ai(self, input):
        if input == 1:
            self.move(-1)
        elif input == 2:
            self.move(1)
        elif input == 3:
            self.rotate_stone()
        elif input == 4:
            self.rotate_stone_counter_clockwise()

    def draw_grid(self, grid, offset_x, offset_y):
        """
        Draw the grid. Used to draw the falling stones. The board is drawn
        by the sprite list.
        """
        # Draw the grid
        for row in range(len(grid)):
            for column in range(len(grid[0])):
                # Figure out what color to draw the box
                if grid[row][column]:
                    color = colors[grid[row][column]]
                    # Do the math to figure out where the box is
                    x = (MARGIN + WIDTH) * (column + offset_x) + MARGIN + WIDTH // 2
                    y = SCREEN_HEIGHT - (MARGIN + HEIGHT) * (row + offset_y) + MARGIN + HEIGHT // 2

                    # Draw the box
                    arcade.draw_rectangle_filled(x, y, WIDTH, HEIGHT, color)

    def update_board(self):
        """
        Update the sprite list to reflect the contents of the 2d grid
        """
        for row in range(len(self.board)):
            for column in range(len(self.board[0])):
                v = self.board[row][column]
                i = row * COLUMN_COUNT + column
                self.board_sprite_list[i].set_texture(v)

    def on_draw(self):
        """ Render the screen. """

        # This command has to happen before we start drawing
        arcade.start_render()
        self.board_sprite_list.draw()
        self.draw_grid(self.stone, self.stone_x, self.stone_y)

    def output_board(self):
        pixels = []
        for row in range(len(self.board) -1):#leaves out the pre-populated bottom row
            for column in range(len(self.board[0])):
                if self.board[row][column] != 0:
                    value = 1
                else:
                    value = 0
                pixels.append(value)
        return pixels

    def output_shape(self):
        shape_list = [0,0,0,0,0,0,0]
        shape_list[self.shape - 1] = 1
        return shape_list

    def output_rotation(self):
        rotation_list = [0,0,0,0]
        rotation_list[self.rotation - 1] = 1
        return rotation_list

    def output_shape_location(self):
        #Scales the number from a small fraction to 1
        x_locations = [0,0,0,0,0,0,0,0,0]
        y_locations = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        x_locations[self.stone_x - 1] = 1
        y_locations[self.stone_y - 1] = 1
        locations = []
        locations.extend(x_locations)
        locations.extend(y_locations)
        return locations

    #The outputs are as follows: Current Shape, Shape Location, Shape Rotation, Grid Data 
    def output_info(self):
        outputs = []
        outputs.extend(self.output_shape())
        outputs.extend(self.output_rotation())
        outputs.extend(self.output_shape_location())
        outputs.extend(self.output_board())
        return outputs

    def restart(self):
        if self.score > 0:
            print(Fore.YELLOW + "Final Score: ", self.score)
        self.score = 0
        self.board = new_board()
        self.update_board()



tetris = MyGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
def main():
    
    tetris.setup()
    arcade.run()
    

if __name__ == "__main__":
    main()