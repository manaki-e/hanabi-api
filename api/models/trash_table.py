from api.core.config import colors


class TrashTable:
    def __init__(self):
        self.cards = {color: [0] * 5 for color in colors}

    def add(self, card):
        self.cards[card.color][card.number - 1] += 1

    def to_dict(self):
        return self.cards
