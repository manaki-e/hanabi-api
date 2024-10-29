from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from api.hanabi import Game
from api.models.player import Player
from api.models.agent import Agent
import random

app = Flask(__name__)
CORS(app)

games = {i: Game() for i in range(200)}
players = {
    i: {
        0: Player([games[i].deck.draw() for _ in range(5)]),
        1: (
            Player([games[i].deck.draw() for _ in range(5)])
            if i < 100
            else Agent([games[i].deck.draw() for _ in range(5)])
        ),
    }
    for i in range(200)
}


@app.route("/api/rooms", methods=["GET"])
def rooms():
    return jsonify(
        [
            {
                "room_id": i,
                "is_finished": games[i].check_finished(),
            }
            for i in range(200)
        ]
    )


@app.route("/api/<room_id>/<player_id>", methods=["GET"])
def get_info(room_id, player_id):

    # * VSエージェントまたはVS人間
    isVsAgent = int(player_id) == 2

    # * ルーティング変数の取得
    room_id = int(room_id)
    player_id = int(player_id) % 2

    # * クエリパラメータの取得
    elapsed_time = request.args.get("time")

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

    # * クエリパラメータの取得
    elapsed_time = request.args.get("time")

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

    form_id = request.form.get("form_id")

    if form_id == "action":
        index = int(request.form.get("index"))
        action = request.form.get("act")
        card = player.hand[index]

        # * アクション（プレイ / 捨てる）別の行動
        if action == "play":
            game.add_history(game.play(card), player_id)
        elif action == "trash":
            game.add_history(game.trash(card), player_id)

        # * 手札の更新
        player.discard(index)
        if len(game.deck.cards) > 0:
            new_card = game.deck.draw()
            player.add(new_card)
            if isVsAgent:
                for card_model in opponent.info:
                    card_model.decrement_card(new_card.color, new_card.number - 1)

    elif form_id == "hint":
        game.teach_token -= 1
        if request.form.get("teach") == "color":
            color = request.form.get("color")
            opponent.get_info(color=color)
            game.add_history(f"{color}のカードについて、ヒントを伝えました", player_id)
        else:
            number = int(request.form.get("number"))
            opponent.get_info(number=number)
            game.add_history(f"{number}のカードについて、ヒントを伝えました", player_id)

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

    # * クエリパラメータの取得
    elapsed_time = request.args.get("time")

    game = games[room_id]
    player = players[room_id][player_id]
    opponent = players[room_id][1 - player_id]

    #  * ゲームが終了している場合
    if game.check_finished():
        return Response(status=200)

    # * エージェントのターンでない場合
    if game.current_player != 1:
        return Response(status=200)

    # * 残山札が0の場合
    if len(game.deck.cards) == 0:
        game.is_finished -= 1

    # * エージェントの行動
    thinking_time = 5
    # * プレイ可能なカードを持っていればプレイする
    if opponent.check_playable(game.field_cards) is not None:
        index = opponent.check_playable(game.field_cards)
        card = opponent.hand[index]
        game.add_history(game.play(card), 1)
        opponent.discard(index)
        if len(game.deck.cards) > 0:
            opponent.add(game.deck.draw())
            opponent.update_first_info(game.trash_table, game.field_cards, player.hand)
    # * 山札が0の場合はヒントを与えたり捨てたりせずににプレイする
    elif len(game.deck.cards) == 0:
        index = random.randint(0, 4)
        card = opponent.hand[index]
        game.add_history(game.play(card), 1)
        opponent.discard(index)
    # * 破棄可能なカードを持っていば捨てる
    elif opponent.check_discardable(game.get_discardable_cards()) is not None:
        index = opponent.check_discardable(game.get_discardable_cards())
        card = opponent.hand[index]
        game.add_history(game.trash(card), 1)
        opponent.discard(index)
        if len(game.deck.cards) > 0:
            opponent.add(game.deck.draw())
            opponent.update_first_info(game.trash_table, game.field_cards, player.hand)
    elif game.teach_token > 0:
        # * 相⼿がプレイ可能なカードを持っていたら、⾊または数字のヒントを与える
        if any(opponent.check_opponent_playable(player.hand, game.field_cards)):
            game.teach_token -= 1
            color, number = opponent.teach_hint(
                opponent.check_opponent_playable(player.hand, game.field_cards),
                player.hand,
            )
            player.get_info(color=color, number=number)
            game.add_history(
                f"{color or number}のカードについて、ヒントを伝えました", 1
            )
        # * 相⼿がプレイ可能なカードを持っていないかつ、残りのヒントトークンが少なければ、ヒントをもらっていないカードからランダムに捨てる
        elif game.teach_token < 3:
            index = opponent.random_discard()
            card = opponent.hand[index]
            game.add_history(game.trash(card), 1)
            opponent.discard(index)
            if len(game.deck.cards) > 0:
                opponent.add(game.deck.draw())
                opponent.update_first_info(
                    game.trash_table, game.field_cards, player.hand
                )
        # * 相⼿がプレイ可能なカードを持っていなかったら、与えてない情報の中からランダムにヒントを与える
        else:
            game.teach_token -= 1
            color, number = opponent.teach_random_hint(player.hand)
            player.get_info(color=color, number=number)
            game.add_history(
                f"{color or number}のカードについて、ヒントを伝えました", 1
            )
    # * ヒントトークンが残っていなかったら、⾃分のカードからランダムに1枚捨てる
    else:
        index = opponent.random_discard()
        card = opponent.hand[index]
        game.add_history(game.trash(card), 1)
        opponent.discard(index)
        if len(game.deck.cards) > 0:
            opponent.add(game.deck.draw())
            opponent.update_first_info(game.trash_table, game.field_cards, player.hand)
    game.switch_turn()
    return jsonify({"thinking_time": thinking_time})


if __name__ == "__main__":
    app.run(debug=True)
