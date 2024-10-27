import random
from api.models.card import Card
from api.core.config import colors, card_numbers


class Deck:
    def __init__(self):
        self.cards = []
        for i in range(len(colors)):
            for j in range(5):
                for k in range(card_numbers[j]):
                    self.cards.append(Card(colors[i], j + 1))
        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop()
