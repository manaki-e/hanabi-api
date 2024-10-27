from api.models.card import Card


class Player:
    def __init__(self, first_hand):
        self.hand = first_hand
        self.info = [Card(None, None) for _ in range(5)]

    def add(self, card):
        self.hand.append(card)
        self.info.append(Card(None, None))

    def discard(self, index):
        self.hand.pop(index)
        self.info.pop(index)

    def get_info(self, color=None, number=None):
        for index, card in enumerate(self.hand):
            if card.color == color:
                self.info[index].color = color
            if card.number == number:
                self.info[index].number = number
