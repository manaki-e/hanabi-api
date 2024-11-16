from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from api.hanabi import Game
from api.models.card import Card
from api.models.player import Player
from api.models.agent import Agent
from api.core.config import (
    colors,
    long_thinking_time,
    short_thinking_time,
    border_thinking_time,
    default_thinking_time,
)
import random, re

app = Flask(__name__)
CORS(app)

games = {i: Game(i) for i in range(250)}
players = {
    i: {
        0: Player([games[i].deck.draw() for _ in range(5)]),
        1: (
            Player([games[i].deck.draw() for _ in range(5)])
            if i < 150
            else Agent([games[i].deck.draw() for _ in range(5)])
        ),
    }
    for i in range(250)
}


@app.route("/api/rooms", methods=["GET"])
def rooms():
    return jsonify(
        [
            {
                "room_id": i,
                "is_finished": games[i].check_finished(),
            }
            for i in range(250)
        ]
    )


@app.route("/api/<room_id>", methods=["GET"])
def get_room(room_id):
    room_id = int(room_id)
    game = games[room_id]
    return jsonify(
        {
            "room_id": room_id,
            "is_finished": game.check_finished(),
            "total_points": sum(card.number for card in game.field_cards),
            "teach_token": game.teach_token,
            "mistake_token": game.mistake_token,
            "deck_number": room_id % 5,
            "remaining_cards": len(game.deck.cards),
            "playing_card_hint": game.playing_card_hint,
            "history": game.history,
            "elapsed_times": game.elapsed_times,
            "agent_action_types": game.agent_action_types,
        }
    )


@app.route("/api/<room_id>/<player_id>", methods=["GET"])
def get_info(room_id, player_id):

    # * VSエージェントまたはVS人間
    isVsAgent = int(player_id) == 2

    # * ルーティング変数の取得
    room_id = int(room_id)
    player_id = int(player_id) % 2

    game = games[room_id]
    player = players[room_id][player_id]
    opponent = players[room_id][1 - player_id]

    #  * ゲームが終了している場合
    if game.check_finished():
        return game.return_data(player, opponent)

    return game.return_data(player, opponent)


@app.route("/api/<room_id>/<player_id>", methods=["POST"])
def post_info(room_id, player_id):

    # * VSエージェントまたはVS人間
    isVsAgent = int(player_id) == 2

    # * ルーティング変数の取得
    room_id = int(room_id)
    player_id = int(player_id) % 2

    game = games[room_id]
    player = players[room_id][player_id]
    opponent = players[room_id][1 - player_id]

    #  * ゲームが終了している場合
    if game.check_finished():
        return Response(status=200)

    # * 自分のターンでない場合
    if game.current_player != player_id:
        return Response(status=200)

    # * 残山札が0の場合
    if len(game.deck.cards) == 0:
        game.is_finished -= 1

    # * 思考時間の記録
    elapsed_time = int(request.args.get("time"))
    game.elapsed_times.append({"elapsed_time": elapsed_time, "player_id": player_id})

    form_id = request.form.get("form_id")

    if form_id == "action":
        index = int(request.form.get("index"))
        action = request.form.get("act")
        card = player.hand[index]

        # * アクション（プレイ / 捨てる）別の行動
        if action == "play":
            game.add_history(game.play(card), player_id)
            game.playing_card_hint.append(player.info[index].count_not_none())
        elif action == "trash":
            game.add_history(game.trash(card), player_id)

        # * 手札の更新
        player.discard(index)
        if len(game.deck.cards) > 0:
            new_card = game.deck.draw()
            player.add(new_card)
            if isVsAgent:
                for card_model in opponent.info_model:
                    card_model.decrement_card(new_card.color, new_card.number - 1)

    elif form_id == "hint":
        game.teach_token -= 1
        if request.form.get("teach") == "color":
            color = request.form.get("color")
            opponent.get_info(color=color)
            game.add_history(f"「{color}」に関するヒントを伝えました。", player_id)
        else:
            number = int(request.form.get("number"))
            opponent.get_info(number=number)
            game.add_history(f"「{number}」に関するヒントを伝えました。", player_id)

    # * ターンの切り替え
    game.switch_turn()
    return Response(status=200)


@app.route("/api/<room_id>/<player_id>/agent", methods=["GET"])
def agent_action(room_id, player_id):

    # * VSエージェントまたはVS人間
    isVsAgent = int(player_id) == 2
    if not isVsAgent:
        return Response(status=200)

    # * ルーティング変数の取得
    room_id = int(room_id)
    player_id = int(player_id) % 2

    game = games[room_id]
    player = players[room_id][player_id]
    agent = players[room_id][1 - player_id]

    #  * ゲームが終了している場合
    if game.check_finished():
        return jsonify({"thinking_time": game.elapsed_times[-1]["elapsed_time"]})

    # * エージェントのターンでない場合
    if game.current_player != 1:
        return jsonify({"thinking_time": game.elapsed_times[-1]["elapsed_time"]})

    # * 残山札が0の場合
    if len(game.deck.cards) == 0:
        game.is_finished -= 1

    # * 思考時間が短かった場合の準備
    is_get_action_by_short_thinking_time = False
    hint_target_cards = []
    if (
        room_id >= 200
        and "ヒント" in game.history[-1]["message"]
        and game.elapsed_times[-1]["elapsed_time"] <= border_thinking_time
    ):
        is_get_action_by_short_thinking_time = True
        hint = re.search(r"「(.*?)」", game.history[-1]["message"]).group(1)
        if hint in colors:
            for index, card in enumerate(agent.hand):
                if card.color == hint:
                    possible_cards = agent.info_model[index].get_possible_cards()
                    possible_card_list = [
                        Card(color, number)
                        for color, numbers in possible_cards.items()
                        for number in numbers
                    ]
                    matching_cards = [
                        card for card in possible_card_list if card in game.field_cards
                    ]
                    if len(matching_cards) > 0:
                        hint_target_cards.append(index)
        else:
            for index, card in enumerate(agent.hand):
                if card.number == int(hint):
                    possible_cards = agent.info_model[index].get_possible_cards()
                    possible_card_list = [
                        Card(color, number)
                        for color, numbers in possible_cards.items()
                        for number in numbers
                    ]
                    matching_cards = [
                        card for card in possible_card_list if card in game.field_cards
                    ]
                    if len(matching_cards) > 0:
                        hint_target_cards.append(index)

    # * エージェントの行動
    thinking_time = default_thinking_time
    # * プレイ可能なカードを持っていればプレイする
    if agent.check_playable(game.field_cards) is not None:
        game.agent_action_types.append(1)
        index = agent.check_playable(game.field_cards)
        card = agent.hand[index]
        game.add_history(game.play(card), 1)
        game.playing_card_hint.append(agent.info[index].count_not_none())
        agent.discard(index)
        if len(game.deck.cards) > 0:
            agent.add(game.deck.draw())
            agent.update_first_info(game.trash_table, game.field_cards, player.hand)
        if room_id >= 200:
            thinking_time = short_thinking_time
    # * 山札が0の場合はヒントを与えたり捨てたりせずににプレイする
    elif len(game.deck.cards) == 0:
        game.agent_action_types.append(2)
        index = random.randint(0, 4)
        card = agent.hand[index]
        game.add_history(game.play(card), 1)
        agent.discard(index)
        if room_id >= 200:
            thinking_time = short_thinking_time
    # * 破棄可能なカードを持っていば捨てる
    elif agent.check_discardable(game.get_discardable_cards()) is not None:
        game.agent_action_types.append(3)
        index = agent.check_discardable(game.get_discardable_cards())
        card = agent.hand[index]
        game.add_history(game.trash(card), 1)
        agent.discard(index)
        if len(game.deck.cards) > 0:
            agent.add(game.deck.draw())
            agent.update_first_info(game.trash_table, game.field_cards, player.hand)
        if room_id >= 200:
            thinking_time = short_thinking_time
    # * タイミングを考慮する処理を追加
    elif is_get_action_by_short_thinking_time and len(hint_target_cards) > 0:
        game.agent_action_types.append(4)
        index = random.choice(hint_target_cards)
        card = agent.hand[index]
        game.add_history(game.play(card), 1)
        game.playing_card_hint.append(player.info[index].count_not_none())
        agent.discard(index)
        if len(game.deck.cards) > 0:
            agent.add(game.deck.draw())
            agent.update_first_info(game.trash_table, game.field_cards, player.hand)
        if room_id >= 200:
            thinking_time = short_thinking_time
    elif game.teach_token > 0:
        # * 相⼿がプレイ可能なカードを持っていたら、⾊または数字のヒントを与える
        if any(agent.check_opponent_playable(player.hand, game.field_cards)):
            game.agent_action_types.append(5)
            game.teach_token -= 1
            color, number = agent.teach_hint(
                agent.check_opponent_playable(player.hand, game.field_cards), player
            )
            player.get_info(color=color, number=number)
            game.add_history(f"「{color or number}」に関するヒントを伝えました。", 1)
            if room_id >= 200:
                thinking_time = short_thinking_time
        # * 相⼿がプレイ可能なカードを持っていないかつ、残りのヒントトークンが少なければ、ヒントをもらっていないカードからランダムに捨てる
        elif game.teach_token < 2:
            game.agent_action_types.append(6)
            index = agent.random_discard()
            card = agent.hand[index]
            game.add_history(game.trash(card), 1)
            agent.discard(index)
            if len(game.deck.cards) > 0:
                agent.add(game.deck.draw())
                agent.update_first_info(game.trash_table, game.field_cards, player.hand)
            if room_id >= 200:
                thinking_time = long_thinking_time
        # * 相⼿がプレイ可能なカードを持っていなかったら、与えてない情報の中からランダムにヒントを与える
        else:
            game.agent_action_types.append(7)
            game.teach_token -= 1
            color, number = agent.teach_random_hint(player.hand)
            player.get_info(color=color, number=number)
            game.add_history(f"「{color or number}」に関するヒントを伝えました。", 1)
            if room_id >= 200:
                thinking_time = long_thinking_time
    # * ヒントトークンが残っていなかったら、⾃分のカードからランダムに1枚捨てる
    else:
        game.agent_action_types.append(8)
        index = agent.random_discard()
        card = agent.hand[index]
        game.add_history(game.trash(card), 1)
        agent.discard(index)
        if len(game.deck.cards) > 0:
            agent.add(game.deck.draw())
            agent.update_first_info(game.trash_table, game.field_cards, player.hand)
        if room_id >= 200:
            thinking_time = long_thinking_time
    game.switch_turn()
    game.elapsed_times.append({"elapsed_time": thinking_time, "player_id": 1})
    return jsonify({"thinking_time": thinking_time})


if __name__ == "__main__":
    app.run(debug=True)
