from random import randint, uniform, choice
from collections import defaultdict
from direct.actor.Actor import Actor
from mazegen import Maze
from tiles import *
from creature import *


DIRS = [(0,-1),(1, 0),(0, 1),(-1,0)]
LOCS = [(4, 0),(8, 4),(4, 8),(0, 4)]
OPPOSITE = {
    "n":"s",
    "e":"w",
    "s":"n",
    "w":"e",
}



class Props():
    def __init__(self):
        self.floor = randint(0,3)
        self.wall = 0

class Room():
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.rect = [self.x,self.y,9,9]
        self.props = Props()
        self.root = base.map.static.attach_new_node("room")
        self.unlit = base.map.unlit.attach_new_node("room")
        self.backsides = base.map.backsides.attach_new_node("room")
        self.construct()

    def construct(self):
        self.generate()
        self.make_doors()
        self.set_neighbors()
        self.finalize()

    def set_neighbors(self):
        dirs = [[0,-1], [1,0], [0,1], [-1,0]]
        solids = "#"
        for y in range(self.rect[3]+2):
            for x in range(self.rect[2]+2):
                sx = x-1+self.rect[0]
                sy = y-1+self.rect[1]
                tile = base.map.tiles[sx,sy]
                tile.neighbors = []
                for dir in dirs:
                    try:
                        n = base.map.tiles[sx+dir[0],sy+dir[1]]
                        if not n.char in solids:
                            tile.neighbors.append(n)
                    except IndexError:
                        pass

    def make_door(self, direction="n"):
        d = "nesw".index(direction)
        x = LOCS[d][0]+self.x
        y = LOCS[d][1]+self.y
        base.map.tiles[x,y] = Door(self.props, [x,y], direction)

    def make_doors(self):
        for door in base.map.new_doors:
            self.make_door(door)

    def connect_doors(self):
        for door in base.map.doors:
            d = "nesw".index(door)
            x = LOCS[d][0]+self.x
            y = LOCS[d][1]+self.y
            w = int(self.rect[2]/2)+self.rect[0]
            h = int(self.rect[3]/2)+self.rect[1]
            self.draw_line(x,y,w,h," ")

    def draw(self, x, y, char):
        base.map.tiles[x,y] = Tile(self.props, [x, y], char)

    def draw_line(self, x1, y1, x2, y2, char):
        #self.draw(x1, y1, char)
        while True:
            if   x1 < x2: x1 += 1
            elif x1 > x2: x1 -= 1
            elif y1 < y2: y1 += 1
            elif y1 > y2: y1 -= 1
            else: return
            self.draw(x1, y1, char)

    def draw_square(self, rect, chance=9):
        for y in range(rect[3]):
            for x in range(rect[2]):
                if randint(0,chance):
                    rx, ry = rect[0]+x, rect[1]+y
                    self.draw(rx, ry, " ")
                    if not randint(0,9):
                        w = Worm("fat",(rx, -ry, 0))
                        w.root.hide()
                        base.map.enemies.append(w)

    def generate(self):
        self.connect_doors()
        x, y, w, h = self.rect
        w = randint(1,self.rect[2]-2)
        h = randint(1,self.rect[3]-2)
        x += (self.rect[2]//2)-(w//2)
        y += (self.rect[3]//2)-(h//2)
        self.draw_square((x,y,w,h))

    def finalize(self):
        for y in range(self.rect[3]):
            for x in range(self.rect[2]):
                t = base.map.tiles[self.x+x,self.y+y]
                if not t.char == "#":
                    if not t.made:
                        t.made = True
                        t.get_surrounding_tiles()
                        t.make_mesh()
                        t.root.reparent_to(self.root)
                        t.unlit.reparent_to(self.unlit)
                        for side in t.root.find_all_matches("**/*_backside"):
                            side.wrt_reparent_to(self.backsides)
        self.root.flatten_strong()
        self.unlit.flatten_strong()
        self.backsides.flatten_strong()
        self.backsides.hide(0b001)

class Map(Maze):
    def __init__(self):
        Maze.__init__(self, 32)
        self.tiles = defaultdict(Tile)
        self.root = render.attach_new_node("map_root")
        self.static = self.root.attach_new_node("map-static")
        self.unlit = render.attach_new_node("map-unlit")
        self.backsides = self.root.attach_new_node("map-backsides")
        self.dynamic = render.attach_new_node("map-dynamic")
        self.enemies = []
        self.rooms = {}
        self.load_tile_set()

    def pos(self, size):
        return self.current_room.x*8, self.current_room.y*8

    def set(self, pos):
        x, y, z = pos
        x = int(x)//8
        y = -int(y)//8
        self._current_room = x, y

    def load_tile_set(self, name="medical"):
        self.tile_set = {}
        tile_set_root = loader.load_model("assets/models/decks/"+name+".bam")
        for child in tile_set_root.get_children():
            self.tile_set[child.name] = child
            child.detach_node()
            child.clear_transform()
        self.tile_set["door"] = Actor("assets/models/decks/doors.bam")

    def build(self, direction):
        self.move(direction)
        p = self.pos(8)
        if not p in self.rooms:
            self.rooms[p] = Room(*p)
        self.move(OPPOSITE[direction])

    def scan(self, start, end, vector):
        vector.normalize()
        while True:
            start -= vector
            x,y,z = start
            x,y = round(x), round(y)
            t = base.map.tiles[x,-y]
            if t.char == "#":
                return False
            elif x == round(end.x) and y == round(end.y):
                return True

    def flow_field(self, start_tile, target_tile):
        marks = {target_tile: 0}
        last_step_marked = [target_tile]
        current_mark = 0
        number_tries = 0
        while start_tile not in marks:
            current_mark += 1
            newly_marked_tiles = []
            new_neighbors = set()
            for tile in last_step_marked:
                for new_neighbor in tile.neighbors:
                    new_neighbors.add(new_neighbor)
            for new_neighbor in new_neighbors:
                marks[new_neighbor] = current_mark
                newly_marked_tiles.append(new_neighbor)
            last_step_marked = newly_marked_tiles
            number_tries += 1
            if number_tries > 32:
                break
        lower = start_tile
        for neighbor in start_tile.neighbors:
            try:
                if marks[neighbor] == marks[lower]:
                    lower = neighbor
                elif marks[neighbor] < marks[lower]:
                    lower = neighbor
            except:
                pass
        return lower
