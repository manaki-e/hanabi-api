from flask import jsonify

from api.models.card import Card
from api.models.deck import Deck
from api.models.trash_table import TrashTable
from api.core.config import colors, teach_token, mistake_token, card_numbers


# * ゲームのクラス
class Game:
    def __init__(self):
        # デッキを作成
        self.deck = Deck()

        # フィールドを作成
        self.field_cards = [Card(color, 0) for color in colors]

        # トークンを設定
        self.teach_token = teach_token
        self.mistake_token = mistake_token

        self.current_player = 0
        self.is_finished = 2

        # 履歴
        self.history = []

        # 捨てられたカード
        self.trash_table = TrashTable()

    def switch_turn(self):
        self.current_player = 1 - self.current_player

    def check_finished(self):
        return self.mistake_token == 0 or self.is_finished == 0

    def play(self, card):
        for field_card in self.field_cards:
            if field_card.color == card.color:
                if card.number == field_card.number + 1:
                    field_card.number = card.number
                    if card.number == 5:
                        self.teach_token += 1
                    return f"「{card.color} - {card.number}」のプレイに成功しました！"

        self.mistake_token -= 1
        self.trash_table.add(card)
        return f"「{card.color} - {card.number}」のプレイに失敗しました..."

    def trash(self, card):
        self.trash_table.add(card)
        self.teach_token += 1
        return f"「{card.color} - {card.number}」のカードを捨てました。"

    def add_history(self, message, player_id):
        self.history.append({"message": message, "player_id": player_id})

    def return_data(self, player, opponent):
        return jsonify(
            {
                "teach_token": self.teach_token,
                "mistake_token": self.mistake_token,
                "field_cards": [card.to_dict() for card in self.field_cards],
                "opponent_hand": [card.to_dict() for card in opponent.hand],
                "player_hand": [card.to_dict() for card in player.hand],
                "player_info": [card.to_dict() for card in player.info],
                "remaining_cards": len(self.deck.cards),
                "history": self.history,
                "trash_table": self.trash_table.to_dict(),
                "current_player": self.current_player,
                "is_finished": self.check_finished(),
            }
        )

    def get_discardable_cards(self):
        """
        _summary_
            捨てられたカードと場にあるカードから、捨てることができるカード一覧を取得する

        Returns:
            _type_: List[Card]
        """
        discardable_cards = []
        for color, numbers in self.trash_table.cards.items():
            for index, number in enumerate(numbers):
                if number == card_numbers[index]:
                    discardable_cards.extend(
                        Card(color, i + 1) for i in range(index, len(numbers))
                    )
                    break

        for card in self.field_cards:
            if card.number == 0:
                continue
            discardable_cards.extend(
                Card(card.color, i + 1) for i in range(card.number)
            )

        return discardable_cards
