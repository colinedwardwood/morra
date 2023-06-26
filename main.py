import logging      # for logging
import uuid         # for generating game ids
import requests     # for requesting turns from player apis
import nanoid       # for generating player ids

logging.basicConfig(format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)


class Player:
    def __init__(self, player_name, player_url) -> None:
        self.player_id = nanoid.generate(size=8)
        self.player_name = player_name
        self.player_url = player_url
        self.score = 0
        return None

    def __str__(self) -> str:
        serial = self.player_name + " " + str(self.score)
        return serial

    def win(self) -> None:
        self.score += 1
        return None

    def get_url(self) -> str:
        return self.player_url

    def get_name(self) -> str:
        return self.player_name


class Game:

    def __init__(self) -> None:
        logger.debug("Initializing game")
        self.game_id = uuid.uuid4()
        self.round_no = 0
        self.players = []
        self.rounds = []
        logger.info("Game " + str(self.game_id) + " started")
        logger.debug("Trying to add players to game")
        self._add_player()
        self.player_count = len(self.players)
        logger.debug("Trying to start game play")
        self.play()
        return None

    def _add_player(self) -> None:
        logger.debug("Adding players to game")
        self.players.append(Player("player_one", "http://localhost:8000/turn/"))
        self.players.append(Player("player_two", "http://localhost:8001/turn/"))
        logger.debug("Players added to game")
        return None

    def play(self):
        logger.debug("Starting game play")

        logger.debug("Round: " + str(self.round_no))

        winner = False
        while not winner:
            self.round_no += 1
            logger.debug("Trying to start round")
            round = Round(self.game_id, self.round_no, self.players)
            self.rounds.append(round)
            logger.debug("Round complete")

            logger.debug("Checking for game winners")
            for p in self.players:
                if p.score == 3:
                    logger.debug("Game won by " + p.get_name())
                    winner = True
        logger.debug("Game over")
        return None

    def get_game_summary(self) -> list:
        round_list = []
        for r in self.rounds:
            round_list.append(r.get_round_dict())
        return round_list


class Round:
    """
    Defines a round within a game.
    """

    def __init__(self, game_id, round_no, players) -> None:
        """
        --------------------------------------------------
        USE:
        - <description>
        --------------------------------------------------
        PARAMETERS:
        <name> - <description> (<datatype>)
        --------------------------------------------------
        RETURNS:
        <name> - <description> (<datatype>)
        --------------------------------------------------
        """
        logger.debug("Initializing round")
        self.turns = []
        self.game_id = game_id
        self.round_no = round_no
        self.player_count = len(players)
        self.throw_total = 0
        self.correct_guesses = 0
        self.players = players

        logger.debug("Starting round - taking turns")
        self._take_turns()              # call the web services to get each players throw and call

        logger.debug("Judging round - totalling throws and checking calls")
        self._total_throws()            # judge the results
        self._check_calls()             # check guesses against round total

        return None

    def _take_turns(self) -> None:
        for i in range(0, self.player_count):
            logger.debug("Requesting turn " + str(i+1))
            turn = Turn(self.game_id, self.round_no, self.players[i])
            self.turns.append(turn)
            logger.debug("Turn " + str(i+1) + " complete")
        return None

    def _total_throws(self) -> None:
        logger.debug("Totalling throws")
        for t in self.turns:
            self.throw_total += t.throw
        logger.info("Throw total is " + str(self.throw_total))
        return None

    def _check_calls(self) -> None:
        logger.debug("Checking calls against throw total.")
        for i in range(0, len(self.turns)):
            logger.debug("Player " + str(i+1) + " call " + str(self.turns[i].call))
            if self.turns[i].call == self.throw_total:
                self.correct_guesses += 1
                winner = self.turns[i].get_player()
            logger.debug("Number of correct guesses: " + str(self.correct_guesses))

        if self.correct_guesses == 1:
            logger.debug("Round winner: " + str(winner.get_name()))
            winner.win()
        return None

    def get_round_dict(self) -> dict:
        turn_dicts = []
        for t in self.turns:
            turn_dicts.append(t.get_turn_dict())

        round_dict = {"game_id": str(self.game_id),
                      "round_no": self.round_no,
                      "throw_total": self.throw_total,
                      "correct_guesses": self.correct_guesses,
                      "turns": turn_dicts
                      }
        return round_dict


class Turn:
    """
    Defines a turn which is made up of a call (guess) and a throw (fingers).
    """

    # METHODS
    def __init__(self, game_id, round_no, player) -> None:
        """
        --------------------------------------------------
        USE:
        - <description>
        --------------------------------------------------
        PARAMETERS:
        <name> - <description> (<datatype>)
        --------------------------------------------------
        RETURNS:
        <name> - <description> (<datatype>)
        --------------------------------------------------
        """
        logger.debug("Initializing turn")
        self.game_id = game_id
        self.round_no = round_no
        self.player = player
        logger.debug("Starting turn")
        request_body = {"game_id": str(self.game_id),
                        "round_no": self.round_no,
                        "player_count": 2}
        logger.debug("Request sent " + str(request_body))
        self._response = requests.post(player.get_url(), json=request_body).json()
        logger.debug("Request response received")
        logger.debug("Response " + str(self._response))
        self.throw = self._response[0]["throw"]
        self.call = self._response[0]["call"]
        return None

    def get_turn_dict(self) -> dict:
        turn_dict = {"player_id": self.player.player_id, 
                     "player_name": self.player.player_name,
                     "throw": self.throw,
                     "call": self.call}
        return turn_dict

    def get_player(self) -> Player:
        logger.debug("Getting turn player")
        return self.player


def main():

    # make a game object this will store the record of game
    # a game is made up of a variable number of rounds
    # a game continues until one player reaches three points
    # a point is earned by winning a round

    # TODO figure out how to add players, or do autodiscovery of players
    logger.debug("Application started")
    game = Game()

    # logger.debug("This is a debug log")
    # logger.info("This is an info log")
    # logger.critical("This is critical")
    # logger.error("An error occurred")
    return None


if __name__ == "__main__":
    main()
