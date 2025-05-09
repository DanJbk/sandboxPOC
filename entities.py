import pygame
from pygame.locals import *
from render import Render

class EntitySprite(pygame.sprite.Sprite):
    def __init__(self, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()
        self.collision_rects = None  # Rectangles for collision detection

    def check_collision(self, rect):
        """Checks for collisions with other rectangles."""
        for collision_rect in self.collision_rects or []:
            if rect.colliderect(collision_rect):
                # print(f"{collision_rect=}")
                # print(f"{rect=}")
                return collision_rect
        return None

    def sync_position(self, pos):
        """Syncs the sprite's position with the logical player's position."""
        self.rect.topleft = pos * 16  # Scale up to pixel coordinates


class MovableEntity:
    def __init__(self, image, pos, properties={}, speed=0.125, render_image=True):
        self.position = pygame.math.Vector2(pos) / 16 # Logical position
        self.velocity = pygame.math.Vector2(0, 0)
        self.speed = speed

        self.properties = properties
        
        if "inventory" in properties:
            self.inventory = set([
                MovableEntity(
                    properties={"name": astring.strip()}, 
                    render_image=True,
                    image=None,
                    pos=(0, 0),
                    ) for astring in properties["inventory"].split(",")
                ])
            self.properties.pop("inventory")
        else:
            self.inventory = set()
        
        self.render_image = render_image
        self.active = render_image

        self.sprite = None

        if image is None:
            return
        
        self.sprite = EntitySprite(image)  # Create the associated sprite
        self.sync_position()  # Sync sprite position

    def move(self, direction):
        """Moves the player logically, handling collisions separately for x and y."""

        self.velocity = direction * self.speed

        new_position_x = self.position.x + self.velocity.x

        test_rect = self.sprite.rect.copy()
        test_rect.x = new_position_x * 16 # Move only horizontally

        collision = self.sprite.check_collision(test_rect)
        if collision:
            if self.velocity.x > 0:  # Moving right
                new_position_x = (collision.left - test_rect.width) / 16
            elif self.velocity.x < 0:  # Moving left
                new_position_x = collision.right / 16

        self.position.x = new_position_x
        self.sync_position()

        new_position_y = self.position.y + self.velocity.y

        test_rect = self.sprite.rect.copy()
        test_rect.y = new_position_y * 16  # Move only vertically

        collision = self.sprite.check_collision(test_rect)
        if collision:
            if self.velocity.y > 0:  # Moving down
                new_position_y = (collision.top - test_rect.height) / 16
            elif self.velocity.y < 0:  # Moving up
                new_position_y = collision.bottom / 16

        self.position.y = new_position_y
        self.sync_position()


    def update(self):
        """Sync sprite position with logical position."""
        self.sync_position()

    def sync_position(self):

        if self.sprite is None:
            return
    
        self.sprite.sync_position(self.position)
