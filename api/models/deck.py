import random, copy
from api.models.card import Card
from api.core.config import decks


class Deck:
    def __init__(self, room_id):
        self.cards = copy.deepcopy(decks[room_id % 5])

    def draw(self):
        return self.cards.pop()
