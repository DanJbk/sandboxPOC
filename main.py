import logging
import sys
import re
import pygame
from pygame.locals import (
    QUIT,
    K_a,
    K_d,
    K_w,
    K_s,
    K_TAB,
    K_RETURN,
    K_BACKSPACE,
    K_UP,
    K_DOWN,
)
import pytmx
from pytmx import TiledObjectGroup, load_pygame

# External modules from your project
from lm_com import generate_text_non_streaming
from render import Render
from entities import MovableEntity
from llm_logic import llm_logic
from utils import extract_property_info, extract_tags, get_best_match, remove_scratchpad

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global constant for the base tile size
TILE_SIZE = 16

# ---------------------------------------------------------------
# UI CLASSES
# ---------------------------------------------------------------

class TextBox:
    """
    A UI element for displaying and handling text input/output (dialogue terminal).
    """
    def __init__(self):
        self.text = ""
        self.active = False
        self.history = []
        self.text_generator = None
        self.turn = "player"
        self.cursor_pos = 0
        self.window_size = 10

    def toggle(self):
        self.active = not self.active

    def update_text(self):
        self.history.append({"speaker": self.turn, "text": self.text})
        self.text = ""
        self.turn = "player" if self.turn == "system" else "system"

    def write_text(self, key):
        self.text += key

    def backspace_text(self):
        if self.text:
            self.text = self.text[:-1]

    def update(self):
        if self.text_generator:
            try:
                next_text = next(self.text_generator)
                self.write_text(next_text)
            except StopIteration:
                self.text_generator = None
                self.update_text()

    def move_cursor(self, direction):
        self.cursor_pos -= direction
        self.cursor_pos = max(0, min(self.cursor_pos, len(self.history)))

    def get_history_to_display(self):
        start = self.cursor_pos
        end = start + self.window_size
        return self.history[start:end]


class OptionBox:
    def __init__(self, options=None, coords=(0, 0), selected_index=-1):
        self.coords = coords
        self.options = options if options is not None else []
        self.entity = None
        self.box_width = 0
        self.box_height = 0
        self.active = False
        self.text_height = 15
        self.title = ""
        self.selected_index = selected_index

    def update_dimensions(self, options, linked_entity, coords, title="Options", screen_height=9000):
        self.coords = coords
        self.options = [{"text": o} for o in options]
        self.entity = linked_entity
        max_text_length = max((len(option["text"]) for option in self.options), default=0)
        self.box_width = 10 + max_text_length * 10
        self.box_height = 15 * (len(self.options) + (1 if title else 0))
        self.active = True
        self.selected_index = -1
        self.title = title

        if self.box_height + self.coords[1] + 20 > screen_height:
            self.coords = (self.coords[0], screen_height - self.box_height - 20)

    def update_selected_index(self, index):
        self.selected_index = int(index)

    def get_selected(self) -> list:
        return [int(min(self.selected_index, len(self.options) - 1))]

# ---------------------------------------------------------------
# SYSTEMS
# ---------------------------------------------------------------

class InputSystem:
    """Handles all user input, including UI interactions, keyboard, and mouse events."""
    def __init__(self, game):
        self.game = game

    def find_closest_entity(self, mouse_grid_pos, entities):
        mouse_vector = pygame.math.Vector2(mouse_grid_pos)
        for entity in entities:
            # Assumes an entity is "clicked" if its grid position matches exactly.
            if mouse_vector.distance_to(round(entity.position)) == 0:
                logger.debug(f"Entity found: {entity.properties.get('name', 'Unknown')} at {entity.position}")
                return entity
        return None

    def is_point_inside(self, x, y, rect_x, rect_y, rect_w, rect_h):
        return rect_x <= x <= rect_x + rect_w and rect_y <= y <= rect_y + rect_h

    def process_events(self):
        """Process all events, including UI events; returns False if a QUIT event is received."""
        for event in pygame.event.get():
            if event.type == QUIT:
                return False

            # --- MOUSE EVENTS ---
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                scale = self.game.scale
                adjusted_x = mouse_x // scale
                adjusted_y = mouse_y // scale
                grid_x = adjusted_x // TILE_SIZE
                grid_y = adjusted_y // TILE_SIZE

                clicked_entity = self.find_closest_entity((grid_x, grid_y), self.game.interactable_entities)

                if event.button == 1:  # Left-click
                        if self.game.text_box.turn.startswith("interact ->") and clicked_entity:
                            self.game.text_box.turn = f"trade -> {clicked_entity.properties.get('name', '')}"
                        elif clicked_entity:
                            self.game.text_box.turn = f"interact -> {clicked_entity.properties.get('name', '')}"
                        else:
                            self.game.text_box.turn = "player"
                        
                        self.game.option_box_primary.active = False
                        
                        
                elif event.button == 3:  # Right-click
                    if clicked_entity:
                        
                        # information window
                        self.game.option_box_primary.active = True
                        title = clicked_entity.properties.get("name", "Options")
                        coords = (
                            int(clicked_entity.position.x * TILE_SIZE * scale),
                            int(clicked_entity.position.y * TILE_SIZE * scale),
                        )
                        coords = (mouse_x, mouse_y)
                        options = [f"{k}: {v}" for k, v in clicked_entity.properties.items()]
                        clicked_entity_inventory = getattr(clicked_entity, 'inventory', [])
                        if clicked_entity_inventory:
                            options.append(f"Inventory:")
                        for item in clicked_entity_inventory:
                            options.append("   " + item.properties.get('name', '--'))
                        self.game.option_box_primary.update_dimensions(options, clicked_entity, coords, title, self.game.screen_height)
                    else:
                        self.game.option_box_primary.active = False

            # --- KEYBOARD EVENTS ---
            elif event.type == pygame.KEYDOWN:
                if event.key == K_TAB:
                    self.game.text_box.toggle()
                elif event.key == K_RETURN and self.game.text_box.active:

                    # Parse the player's input using llm_logic.
                    llm_output = llm_logic.parse_player_input(
                        self.game.text_box.turn, self.game.text_box.text, self.game.player, self.game.interactable_entities
                    )
                    if llm_output["type"] == "interact":
                        target_details = llm_output["target"]
                        match = re.search(r'new_property_value\("([^"]*)"\)', llm_output["text"])
                        if match:
                            interaction_result = match.group(1)
                            entity_index = target_details["entity_index"]
                            property_name = target_details["property"].strip()
                            self.game.interactable_entities[entity_index].properties[property_name] = interaction_result
                    elif llm_output["type"] == "trade":
                        # Process trade logic (if any)
                        trade_result = llm_output["target"]["property"]
                        if len(trade_result) == 2:
                            traded, recived = trade_result
                            print("%%%%", traded, recived)
                            
                            entity_to_trade = None
                            entity_to_recive = None
                            
                            inv_items = list(self.game.player.inventory)
                            possible_matches = [anentity.properties.get("name") for anentity in inv_items]
                            best_match, best_score = get_best_match(traded, possible_matches)
                            best_match_index = possible_matches.index(best_match)
                            entity_to_trade = inv_items[best_match_index]

                            trader_index = llm_output["target"]["entity_index"]

                            inv_items = list(self.game.interactable_entities[trader_index].inventory)
                            possible_matches = [anentity.properties.get("name") for anentity in self.game.interactable_entities[llm_output["target"]["entity_index"]].inventory]
                            best_match, best_score = get_best_match(recived, possible_matches)
                            best_match_index = possible_matches.index(best_match)
                            entity_to_recive = inv_items[best_match_index]

                            if entity_to_trade and entity_to_recive:
                                self.game.player.inventory.remove(entity_to_trade)
                                self.game.interactable_entities[trader_index].inventory.add(entity_to_trade)
                                self.game.player.inventory.add(entity_to_recive)
                                self.game.interactable_entities[trader_index].inventory.remove(entity_to_recive)
                        
                    elif llm_output["type"] == "pickup":
                        text_output = llm_output["text"]
                        text_output = remove_scratchpad(text_output)
                        if "success" in text_output and "fail" not in text_output:
                            entity_index = llm_output["target"]["entity_index"]
                            self.game.player.inventory.add(self.game.interactable_entities[entity_index])
                            # Mark the entity as picked up.
                            self.game.interactable_entities[entity_index].render_image = False

                    elif llm_output["type"] == "do":
                        text_output = llm_output["text"]
                        text_output = remove_scratchpad(text_output)
                        if "success" in text_output and "fail" not in text_output:
                            text_output = llm_output["text"]
                            object_index = llm_output["target"]["entity_index"]
                            prompt, _ = llm_logic.do_interact_all_command(self.game.text_box.turn, self.game.text_box.text, self.game.player, self.game.interactable_entities, object_index)                            
                            print(prompt)
                            text_output = generate_text_non_streaming(prompt)
                            print(f"{text_output=}")
                            out = extract_property_info(text_output)
                            for o in out:
                                print(f"{o['entity_name']=}")
                                print(f"{o['property_name']=}")
                                print(f"{o['value']=}")
                                print()
                                
                                if self.game.interactable_entities[object_index].properties.get(o['property_name'], None) is not None:
                                    self.game.interactable_entities[object_index].properties[o['property_name']] = o['value']

                        else:
                            pass
                    
                    self.game.text_box.update_text()
                    self.game.text_box.text_generator = llm_output["output"]
                    
                elif self.game.text_box.active:
                    if event.key == K_BACKSPACE:
                        self.game.text_box.backspace_text()
                    elif event.key == K_UP:
                        self.game.text_box.move_cursor(1)
                    elif event.key == K_DOWN:
                        self.game.text_box.move_cursor(-1)
                    else:
                        self.game.text_box.write_text(event.unicode)

        return True


class MovementSystem:
    """Updates movement for all entities with a move() method."""
    def __init__(self, entities, player):
        self.entities = entities  # List of game entities (NPCs, etc.)
        self.player = player      # The player entity

    def update(self, dt):
        """Updates the player movement based on key inputs."""
        keys = pygame.key.get_pressed()
        direction = pygame.math.Vector2(0, 0)

        if keys[K_a]:
            direction.x = -1
        if keys[K_d]:
            direction.x = 1
        if keys[K_w]:
            direction.y = -1
        if keys[K_s]:
            direction.y = 1

        if direction.length_squared() != 0:
            direction = direction.normalize()

        self.player.move(direction)


class RenderSystem:
    """Handles drawing of game layers, entities, and UI elements."""
    def __init__(self, render_obj, screen, ui_elements):
        self.render = render_obj
        self.screen = screen
        self.ui_elements = ui_elements  # Dict with keys "text_boxes" and "option_boxes"

    def render_all(self, entity_sprite_group):
        """
        Renders the base tile map layers, then the player, NPCs, and finally
        any UI elements.
        """
        self.render.update(
            entity_sprite_group,
            self.screen,
            self.ui_elements.get("text_boxes", []),
            self.ui_elements.get("option_boxes", []),
        )


# ---------------------------------------------------------------
# GAME CLASS (ECS-LIKE DESIGN)
# ---------------------------------------------------------------

class Game:
    def __init__(self, tmx_map_path: str, tileset_image_path: str, scale: int = 2):
        pygame.init()
        # Set a temporary display mode so that image operations (like convert_alpha) work.
        pygame.display.set_mode((1, 1))

        self.scale = scale
        self.tmx_data = load_pygame(tmx_map_path)
        self.tileset_image = pygame.image.load(tileset_image_path).convert_alpha()

        # Initialize Render object
        self.render = Render(self.tmx_data, self.tmx_data.width, self.tmx_data.height)

        # Set up screen dimensions based on map size
        self.screen_width = self.tmx_data.width * TILE_SIZE * self.scale
        self.screen_height = self.tmx_data.height * TILE_SIZE * self.scale
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Tile Map Game - ECS Version with UI")

        # Clock for controlling FPS
        self.clock = pygame.time.Clock()

        # Store static collisions from the map (from tile layers that are truly static).
        self.map_collision_rects = self._get_map_collision_rects()

        # Initialize player.
        self.player = self._load_player()

        # Load dynamic entities from metadata.
        self.logic_entities = self._load_metadata_entities()
        self.interactable_entities = self.logic_entities + [self.player]

        # Build sprite groups for rendering.
        self.player_group = pygame.sprite.Group(self.player.sprite)
        self.entity_sprite_group = pygame.sprite.Group([entity.sprite for entity in self.logic_entities])

        # Instantiate UI elements.
        self.text_box = TextBox()
        self.option_box_primary = OptionBox()
        # self.option_box_secondary = OptionBox()
        # self.option_box_thirdy = OptionBox()
        self.ui_elements = {
            "text_boxes": [self.text_box],
            "option_boxes": [self.option_box_primary],
        }

        # Initialize systems.
        self.input_system = InputSystem(self)
        self.movement_system = MovementSystem(self.logic_entities, self.player)
        self.render_system = RenderSystem(self.render, self.screen, self.ui_elements)

        # Initialize dynamic collision list.
        self.update_dynamic_collisions()


    # -------------------------------
    # Helper Methods
    # -------------------------------
    def _get_map_collision_rects(self):
        """
        Extracts static collision rectangles from the tile layer "collision" only.
        (Exclude "npcs" so that dynamic items from metadata are not duplicated.)
        """
        collision_rects = []
        layer = self.tmx_data.get_layer_by_name("collision")
        if layer and hasattr(layer, "data"):
            for x, y, gid in layer:
                if gid != 0:
                    rect = pygame.Rect(
                        x * self.render.TILE_SIZE,
                        y * self.render.TILE_SIZE,
                        self.render.TILE_SIZE,
                        self.render.TILE_SIZE,
                    )
                    collision_rects.append(rect)
        return collision_rects

    def update_dynamic_collisions(self):
        """
        Recalculates the active collision rectangles by:
          1. Filtering the static map collisions to remove any rectangle whose grid cell
             is occupied by a dynamic entity that is picked up (render_image is False).
          2. Adding dynamic collision rectangles for visible (render_image True) entities.
        Then updates the player's sprite collision list.
        """
        filtered_static = []
        for rect in self.map_collision_rects:
            grid_x = rect.x // TILE_SIZE
            grid_y = rect.y // TILE_SIZE
            remove = False
            for entity in self.logic_entities:
                if not entity.render_image:
                    if int(entity.position.x) == grid_x and int(entity.position.y) == grid_y:
                        remove = True
                        break
            if not remove:
                filtered_static.append(rect)

        dynamic_collisions = []
        for entity in self.logic_entities:
            if entity.render_image:
                dynamic_collisions.append(
                    pygame.Rect(
                        int(entity.position.x) * TILE_SIZE,
                        int(entity.position.y) * TILE_SIZE,
                        TILE_SIZE,
                        TILE_SIZE,
                    )
                )
        self.collision_rects = filtered_static + dynamic_collisions
        self.player.sprite.collision_rects = self.collision_rects

    def _get_tile_from_tileset(self, tile_x: int, tile_y: int):
        """Extract and scale a single tile image from the tileset."""
        rect = pygame.Rect(
            tile_x * self.render.TILE_SIZE,
            tile_y * self.render.TILE_SIZE,
            self.render.TILE_SIZE,
            self.render.TILE_SIZE,
        )
        try:
            tile_image = self.tileset_image.subsurface(rect).copy()
        except ValueError:
            logger.error(f"Tile ({tile_x}, {tile_y}) is out of bounds.")
            return None
        tile_image = pygame.transform.scale(tile_image, (self.render.TILE_SIZE, self.render.TILE_SIZE))
        return tile_image

    def _load_player(self):
        """Loads the player entity using a specific tile from the tileset."""
        player_image = self._get_tile_from_tileset(31, 1)
        if player_image is None:
            player_image = pygame.Surface((self.render.TILE_SIZE, self.render.TILE_SIZE))
            player_image.fill((255, 0, 0))

        player_start_x = TILE_SIZE * 2
        player_start_y = TILE_SIZE * 2

        for obj in self.tmx_data.get_layer_by_name("metadata"):
            print(f"{obj.name=}")
            if obj.name == "player":
                
                player_start_x = obj.x
                player_start_y = obj.y
                print("Player start position:", player_start_x, player_start_y)

        player_properties = {
            "background": "A thief, spent a life stealing and sneaking throught the big cities.",
            "name": "John Skiss",
            "inventory": "lockpick, dagger, dark cloak",
            "stength": "average person stength, will often fail tasks that require brute force"
        }

        return MovableEntity(player_image, (player_start_x, player_start_y), player_properties)

    def _load_metadata_entities(self):
        """
        Loads entities from the TMX metadata layer using fallback layers.
        These entities are considered dynamic; their collisions will be updated each frame.
        """
        entities = []
        metadata_layer = self.tmx_data.get_layer_by_name("metadata")
        if not metadata_layer:
            return entities

        npc_layer = self.tmx_data.get_layer_by_name("npcs")
        above_ground_layer = self.tmx_data.get_layer_by_name("above_ground")
        collision_layer = self.tmx_data.get_layer_by_name("collision")
        on_ground_layer = self.tmx_data.get_layer_by_name("on_ground")

        for obj in metadata_layer:
            if obj.name == "player":
                continue  # Skip the player start position object entirely
            
            grid_x = int(obj.x // self.render.TILE_SIZE)
            grid_y = int(obj.y // self.render.TILE_SIZE)

            tile_image = None

            if npc_layer and npc_layer.data[grid_y][grid_x] != 0:
                tile_image = self.tmx_data.get_tile_image(x=grid_x, y=grid_y, layer=npc_layer.id - 1)
                npc_layer.data[grid_y][grid_x] = 0
            elif above_ground_layer and above_ground_layer.data[grid_y][grid_x] != 0:
                tile_image = self.tmx_data.get_tile_image(x=grid_x, y=grid_y, layer=above_ground_layer.id - 1)
                above_ground_layer.data[grid_y][grid_x] = 0
            elif collision_layer and collision_layer.data[grid_y][grid_x] != 0:
                tile_image = self.tmx_data.get_tile_image(x=grid_x, y=grid_y, layer=collision_layer.id - 1)
                collision_layer.data[grid_y][grid_x] = 0
            elif on_ground_layer and on_ground_layer.data[grid_y][grid_x] != 0:
                tile_image = self.tmx_data.get_tile_image(x=grid_x, y=grid_y, layer=on_ground_layer.id - 1)
                on_ground_layer.data[grid_y][grid_x] = 0

            if tile_image:
                properties = {**obj.properties, "name": obj.name}
                entity = MovableEntity(
                    tile_image,
                    (grid_x * self.render.TILE_SIZE, grid_y * self.render.TILE_SIZE),
                    properties
                )
                entities.append(entity)
        return entities


    # -------------------------------
    # Main Game Loop
    # -------------------------------
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(self.render.FPS) / 1000.0

            # --- PROCESS INPUT ---
            running = self.input_system.process_events()
            if not running:
                break

            # --- UPDATE GAME STATE ---
            if not self.text_box.active:
                self.movement_system.update(dt)
            self.player.update()
        
            for entity in self.logic_entities:
                entity.update()

            # --- UPDATE SPRITE GROUPS ---
            for entity in self.logic_entities:
                if entity.render_image:
                    if entity.sprite not in self.entity_sprite_group:
                        self.entity_sprite_group.add(entity.sprite)
                else:
                    if entity.sprite in self.entity_sprite_group:
                        self.entity_sprite_group.remove(entity.sprite)

            # --- UPDATE DYNAMIC COLLISIONS ---
            self.update_dynamic_collisions()

            # --- RENDER FRAME ---
            render_group = pygame.sprite.Group(self.player_group, self.entity_sprite_group)
            self.render_system.render_all(render_group)

            # Update the UI text box (if a text generator is active)
            self.text_box.update()

        pygame.quit()
        sys.exit()


# ---------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------

def main():
    tmx_map_path = r"assets\map\demo_map.tmx"
    # tmx_map_path = r"assets\map\level_1.tmx"
    tileset_image_path = r"tilesets\1bit\colored-transparent_packed.png"
    game = Game(tmx_map_path, tileset_image_path, scale=2)
    game.run()

if __name__ == "__main__":
    main()
