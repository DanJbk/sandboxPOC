import pytmx
from pytmx import TiledObjectGroup
import pygame
import textwrap


class Render:

    def __init__(self, tmx_data, MAP_WIDTH, MAP_HEIGHT):

        self.TILE_SIZE = 16  # Original tile size
        self.SCALE = 2  # Scale factor for zooming in

        # Scaled tile size
        self.FPS = 60

        self.tmx_data = tmx_data

        self.MAP_WIDTH = MAP_WIDTH
        self.MAP_HEIGHT = MAP_HEIGHT
        print(f"{self.MAP_HEIGHT=} {self.MAP_WIDTH=}")

        self.SCREEN_WIDTH = self.MAP_WIDTH * self.TILE_SIZE * self.SCALE
        self.SCREEN_HEIGHT = self.MAP_HEIGHT * self.TILE_SIZE * self.SCALE

        pygame.display.set_caption("TMX Map with Player and NPCs (Zoomed In)")
        self.base_surface = pygame.Surface(
            (
                self.MAP_WIDTH * self.TILE_SIZE,
                self.MAP_HEIGHT * self.TILE_SIZE,
            )
        )

    def get_tile_image(self, gid):
        tile = self.tmx_data.get_tile_image_by_gid(gid)
        if tile:
            # Scale the tile image
            tile = pygame.transform.scale(tile, (self.TILE_SIZE, self.TILE_SIZE))
        return tile

    def draw_tile_layer(self, tmx_data, layer_name, surface):
        layer = tmx_data.get_layer_by_name(layer_name)
        if layer and isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                if gid == 0:
                    continue  # Skip empty tiles
                tile_image = self.get_tile_image(gid)
                # tile_image = pygame.transform.scale(tile_image, (16 * 2, 16 * 2))

                if tile_image:
                    surface.blit(
                        tile_image,
                        (x * self.TILE_SIZE, y * self.TILE_SIZE),
                    )



    def draw_optionbox(self, optionbox):
        box_coords = tuple(optionbox.coords)

        # Initialize surface
        font = pygame.font.Font(None, 22)
        font_height = font.get_height()

        num_lines = len(optionbox.options) + (1 if optionbox.title else 0)
        required_height = num_lines * font_height + 10  # Dynamic height calculation
        textbox_surface = pygame.Surface((optionbox.box_width, max(optionbox.box_height, required_height)))
        textbox_surface.fill((25, 25, 25))
        textbox_surface.set_alpha(220)

        # Prepare option list
        has_title = optionbox.title is not None
        option_list = [{"text": optionbox.title}] + optionbox.options if has_title else optionbox.options

        # Render text
        line_height = 10  # Initial padding
        selected_option = optionbox.get_selected()
        for i, option in enumerate(option_list):
            color = (255, 255, 100) if i - 1 in selected_option else (255, 255, 255)
            if has_title and i == 0:
                color = (255, 100, 100)

            text = font.render(option["text"], True, color)
            textbox_surface.blit(text, (10, line_height))
            line_height += font_height

        return textbox_surface, box_coords



    def draw_textbox(
        self, chat_history=[{"speaker": "system", "text": "hello world!"}]
    ):

        # surface_width = self.base_surface.get_width()
        # surface_height = self.base_surface.get_height()

        surface_width = self.SCREEN_WIDTH
        surface_height = self.SCREEN_HEIGHT

        box_top = int(surface_height * 0.5)
        box_bottom = surface_height - box_top

        textbox_surface = pygame.Surface((surface_width, box_bottom))
        textbox_surface.fill((25, 25, 25))
        textbox_surface.set_alpha(220)
        font = pygame.font.Font(None, 22)

        font_height = font.get_height()
        line_height = 0

        for chat_message in chat_history:

            chat_text = textwrap.wrap(chat_message["text"], 115)
            if len(chat_text) > 0:
                chat_text[0] = f"{chat_message['speaker']}: {chat_text[0]}"

            for chat_text_line in chat_text:
                text = font.render(chat_text_line, True, (150, 150, 150))
                textbox_surface.blit(text, (10, 10 + line_height))
                line_height += font_height

        # self.base_surface.blit(textbox_surface, (0, box_top))
        return textbox_surface, (0, box_top)

    def update(self, npcs_group, screen, textboxes, optionboxes):

        self.base_surface.fill(
            self.tmx_data.background_color
            if self.tmx_data.background_color
            else (0, 0, 0)
        )

        # Optionally, draw other layers like "metadata", etc.
        # For example, drawing objects from "metadata" as needed
        metadata_layer = self.tmx_data.get_layer_by_name("metadata")
        if isinstance(metadata_layer, TiledObjectGroup):
            for obj in metadata_layer:
                # Example: Draw a simple rectangle around objects
                if obj.name.lower() != "player":  # Avoid drawing the player if present
                    # Choose a color based on object type
                    # if obj.type == "doorway":
                    #     color = (0, 0, 255)  # Blue for doorways
                    # elif obj.type == "furniture":
                    #     color = (139, 69, 19)  # Brown for furniture
                    # elif obj.type == "object":
                    #     color = (255, 255, 0)  # Yellow for generic objects
                    # elif obj.type == "transport":
                    #     color = (0, 255, 255)  # Cyan for transport objects
                    # else:
                    #     color = (255, 255, 255)  # White for others
                    color = (100, 100, 100)  # White for others

                    # Draw the rectangle
                    pygame.draw.rect(
                        self.base_surface,
                        color,
                        pygame.Rect(
                            obj.x,
                            obj.y,
                            obj.width,
                            obj.height,
                        ),
                        1,  # Border thickness
                    )


        # Draw "on_ground" layer
        # self.draw_tile_layer(self.tmx_data, "on_ground", screen)
        self.draw_tile_layer(self.tmx_data, "on_ground", self.base_surface)

        # Draw "collision" layer
        # self.draw_tile_layer(self.tmx_data, "collision", screen)
        self.draw_tile_layer(self.tmx_data, "collision", self.base_surface)

        # Draw NPC sprites
        npcs_group.draw(self.base_surface)

        # Draw "above_ground" layer
        self.draw_tile_layer(self.tmx_data, "above_ground", self.base_surface)
        self.draw_tile_layer(self.tmx_data, "npcs", self.base_surface)


        # for textbox in textboxes:
        #     if textbox.active:
        #         self.draw_textbox(textbox.history + [textbox.text + "_"])

        # Update the display
        scaled_surface = pygame.transform.scale(
            self.base_surface,
            (
                self.TILE_SIZE * self.MAP_WIDTH * self.SCALE,
                self.TILE_SIZE * self.MAP_HEIGHT * self.SCALE,
            ),
        )

        screen.blit(scaled_surface, (0, 0))

        for textbox in textboxes:
            if textbox.active:
                textbox_surface, coords = self.draw_textbox(
                    textbox.get_history_to_display()
                    + [{"speaker": textbox.turn, "text": f"{textbox.text}_"}]
                )
                screen.blit(textbox_surface, coords)

        for optionbox in optionboxes:
            if not optionbox.active:
                continue

            optionbox_surface, coords = self.draw_optionbox(optionbox)
            screen.blit(optionbox_surface, coords)

        pygame.display.flip()
