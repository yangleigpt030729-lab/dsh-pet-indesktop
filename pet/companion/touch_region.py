"""Conservative visible head core; ambiguous overlap belongs to ordinary clicking."""
from .. import catalog


def head_core_at(character, point, draw_rect, mirrored=False):
    box = catalog.character_head_box(character)
    if not box or draw_rect.width() <= 0 or draw_rect.height() <= 0:
        return False
    x = (point.x()-draw_rect.x())*catalog.CANVAS_W/draw_rect.width()
    y = (point.y()-draw_rect.y())*catalog.CANVAS_H/draw_rect.height()
    if mirrored:
        x = catalog.CANVAS_W-x
    x1, y1, x2, y2 = box
    # Use the central upper head only. Full body_box overlap would erase this
    # core on shenshen; borders/lower face always retain the body click behavior.
    return x1+(x2-x1)*.22 < x < x2-(x2-x1)*.22 and y1+(y2-y1)*.15 < y < y1+(y2-y1)*.7
