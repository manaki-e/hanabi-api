import random
from api.models.card import Card
from api.models.card_model import CardModel
from api.core.config import colors


class Agent:
    def __init__(self, first_hand):
        self.hand = first_hand
        self.info = [CardModel() for _ in range(5)]

    def add(self, card):
        self.hand.append(card)
        self.info.append(CardModel())

    def discard(self, index):
        self.hand.pop(index)
        self.info.pop(index)

    def update_first_info(self, trash_table, field_cards, opponent_hand):
        self.info[-1].cards = {
            color: [
                a - b
                for a, b in zip(self.info[-1].cards[color], trash_table.cards[color])
            ]
            for color in self.info[-1].cards
        }
        for card in field_cards:
            for number in range(card.number):
                self.info[-1].decrement_card(card.color, number)
        for card in opponent_hand:
            self.info[-1].decrement_card(card.color, card.number - 1)

    def get_info(self, color=None, number=None):
        if color is not None:
            for index, card in enumerate(self.hand):
                if card.color == color:
                    for color_variant in colors:
                        if color_variant != color:
                            self.info[index].cards[color_variant] = [0] * 5
                else:
                    self.info[index].cards[color] = [0] * 5
        if number is not None:
            for index, card in enumerate(self.hand):
                if card.number == number:
                    for color_variant in colors:
                        for i in range(5):
                            if i != number - 1:
                                self.info[index].cards[color_variant][i] = 0
                else:
                    for color_variant in colors:
                        self.info[index].cards[color_variant][number - 1] = 0

    def check_playable(self, field_cards):
        """
        _summary_
            プレイ可能なカードがあるかどうかをチェックする

        Returns
            __type__ : int
        """
        for index, card_model in enumerate(self.info):
            possible_cards = card_model.get_possible_cards()
            if set(
                [
                    Card(color, number)
                    for color, numbers in possible_cards.items()
                    for number in numbers
                ]
            ).issubset(field_cards):
                return index
        return None

    def check_opponent_playable(self, opponent_hand, field_cards):
        """
        _summary_
            相手の手札に対してプレイ可能なカードがあるかどうかをチェックする

        Returns
            __type__ : list[bool]
        """
        playable_cards = []
        for index, card in enumerate(opponent_hand):
            if Card(card.color, card.number - 1) in field_cards:
                playable_cards.append(True)
            else:
                playable_cards.append(False)
        return playable_cards

    def check_discardable(self, discardable_cards):
        """
        _summary_
            プレイ可能なカードがあるかどうかをチェックする

        Returns
            __type__ : int
        """
        for index, card_model in enumerate(self.info):
            possible_cards = card_model.get_possible_cards()
            if set(
                [
                    Card(color, number + 1)
                    for color, numbers in possible_cards.items()
                    for number in numbers
                ]
            ).issubset(discardable_cards):
                return index
        return None

    def teach_hint(self, playable_cards, opponent):
        """
        _summary_
            相手がプレイ可能なカードを持っているときに、色または数字のヒントを与える

        Returns
            __type__ : str, int
        """
        teach_color = None
        teach_number = None
        teachable_colors = {card.color for card in opponent.hand}
        teachable_numbers = {card.number for card in opponent.hand}
        max_probability = 0
        for color in teachable_colors:
            probability_list = [
                playable_cards[i]
                for i, card in enumerate(opponent.hand)
                if card.color == color
            ]
            if probability_list:
                if (sum(probability_list) / len(probability_list)) >= max_probability:
                    if (
                        not opponent.is_info_updated(color=color)
                        and max_probability != 0
                    ):
                        continue
                    max_probability = sum(probability_list) / len(probability_list)
                    teach_number = None
                    teach_color = color
        for number in teachable_numbers:
            probability_list = [
                playable_cards[i]
                for i, card in enumerate(opponent.hand)
                if card.number == number
            ]
            if probability_list:
                if (sum(probability_list) / len(probability_list)) >= max_probability:
                    if (
                        not opponent.is_info_updated(number=number)
                        and max_probability != 0
                    ):
                        continue
                    max_probability = sum(probability_list) / len(probability_list)
                    teach_number = number
                    teach_color = None
        return teach_color, teach_number

    def teach_random_hint(self, opponent_hand):
        """
        _summary_
            相手にランダムなヒントを与える

        Returns
            __type__ : str, int
        """
        teachable_colors = {card.color for card in opponent_hand}
        teachable_numbers = {card.number for card in opponent_hand}
        if random.choice([True, False]):
            return (random.choice(list(teachable_colors)), None)
        else:
            return (None, random.choice(list(teachable_numbers)))

    def random_discard(self):
        """
        _summary_
            与えられたヒントが最も少ないカードを捨てる

        Returns
            __type__ : int
        """
        number_of_zeros = [card_model.count_zero() for card_model in self.info]
        return number_of_zeros.index(min(number_of_zeros))
