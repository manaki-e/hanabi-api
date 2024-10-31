from api.models.card import Card
import copy


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

    def is_info_updated(self, color=None, number=None):
        update_info = copy.deepcopy(self.info)
        for index, card in enumerate(self.hand):
            if card.color == color:
                update_info[index].color = color
            if card.number == number:
                update_info[index].number = number
        return update_info != self.info
