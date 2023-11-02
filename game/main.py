# main.py

import argparse                     # for parsing command line arguments
import logging                      # for logging
import uuid                         # for generating game ids
import requests                     # for requesting turns from player apis
import nanoid                       # for generating player ids
import time                         # for sleeping between games
from rich import print              # for pretty printing
from rich.console import Console 
from rich.columns import Columns
from rich.panel import Panel
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)


# LOGGING SETUP
logging.basicConfig(format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    filemode='w',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
RequestsInstrumentor().instrument()

# MANUAL TRACING SETUP
resource = Resource(attributes={ SERVICE_NAME: "main_game" })
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="agent:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("main-game")

# ARGUMENT PARSING
logger.debug("Initializing application and parsing arguments") # Log the start of the application
parser = argparse.ArgumentParser()  # Create the parser
parser.add_argument('-i', '--interactive',  # Add an argument for interactive mode
                    action='store_const',
                    dest='interactive',
                    const=True,
                    default=False,
                    required=False, 
                    help='Add this option to run in interactive mode, default is non-interactive mode.')
parser.add_argument('-d','--debug',  # Add an argument for debug mode
                    action='store_const',
                    dest='debug',
                    const=True,
                    default=False,
                    required=False,
                    help='Add this option to r un in debug mode, default is non-debug mode.')
parser.add_argument('-n','--num_rounds',  # Add an argument for number of rounds
                    action='store',
                    dest='num_rounds',
                    type=int,
                    default=1,
                    required=False,
                    help='Add this option to specify the number of rounds to play, default is 1.')
parser.add_argument('-t','--timeout',  # Add an argument for timeout between games
                    action='store',
                    dest='timeout',
                    type=int,
                    default=0,
                    required=False,
                    help='Add this option to specify the number of seconds to wait between games.')

args = parser.parse_args()  # Parse the argument
logger.debug("Application started with arguments: " + str(args)) # Log the arguments
if args.debug:
    logger.info("Debug mode enabled")
    logger.setLevel(logging.DEBUG)
else:
    logger.info("Debug mode disabled")
    logger.setLevel(logging.INFO)
if args.interactive:
    console = Console()


class Player:
    def __init__(self, player_name, player_url) -> None:
        self.player_id = nanoid.generate(size=8)
        self.player_name = player_name
        self.player_url = player_url
        self.score = 0
        return None

    # @tracer.start_as_current_span("player_str")
    def __str__(self) -> str:
        serial = self.player_name + " " + str(self.score)
        return serial

    # @tracer.start_as_current_span("player_win")
    def win(self) -> None:
        self.score += 1
        return None

    # @tracer.start_as_current_span("player_get_url")
    def get_url(self) -> str:
        return self.player_url

    # @tracer.start_as_current_span("player_get_name")
    def get_name(self) -> str:
        return self.player_name
    
    # @tracer.start_as_current_span("player_get_score")
    def get_score(self) -> int:
        return self.score

class Game:
    def __init__(self) -> None:
        self.game_id = uuid.uuid4()
        with tracer.start_as_current_span("game_init") as game_init_span:
            logger.debug("Initializing game")
            game_init_span.set_attribute("game.id", str(self.game_id))
            self.round_no = 0
            self.players = []
            self.rounds = []
            logger.info("Game " + str(self.game_id) + " started")
            logger.debug("Trying to add players to game")
            self._add_player()
            self.player_count = len(self.players)
            game_init_span.set_attribute("game.player_count", self.player_count)
            logger.debug("Trying to start game play")
            self.play()
            return None
    
    # @tracer.start_as_current_span("game_add_player")
    def _add_player(self) -> None:
        logger.debug("Adding players to game")
        self.players.append(Player("python_player", "http://python_player:80"))
        self.players.append(Player("go_player", "http://go_player:80"))
        self.players.append(Player("node_player", "http://node_player:80"))
        logger.debug("Players added to game")
        return None
    
    # @tracer.start_as_current_span("_game_print_game_summary")
    def _print_game_summary(self) -> None:
        logger.debug("Printing game summary")
        panels = []  # create list of panels
        panels.append(Panel(f"WINNER!\n", expand=True, width=20))  # add round total panel
        for p in self.players:
            a = f"[green]{p.get_name()}[/green]" if p.get_score() == 3 else f"[white]{p.get_name()}[/white]"  # set colour of player name if they guessed correctly
            b = f"[green]Final Score: {str(p.get_score())}[/green]" if p.get_score() == 3 else f"Final Score: {str(p.get_score())}"
            c = a + "\n" + b  # set panel text
            panels.append(Panel(c, expand=True, width=30))  # add panel to list
        
        console.print(Columns(panels))  # print the panels
        return None

    def play(self):
        with tracer.start_as_current_span("game_play") as game_play:

            logger.debug("Starting game play")

            winner = False
            while not winner:
                self.round_no += 1
                logger.debug("Trying to start round")
                logger.debug("Round: " + str(self.round_no))
                round = Round(self.game_id, self.round_no, self.players)
                self.rounds.append(round)
                logger.debug("Round complete")

                logger.debug("Checking for game winners")
                for p in self.players:
                    if p.score == 3:
                        logger.debug("Game won by " + p.get_name())
                        if args.interactive:
                            self._print_game_summary()
                        winner = True
                        game_play.set_attribute("game.winner", p.player_name)

                        break
                    
            logger.debug("Game over")

            return None

    # @tracer.start_as_current_span("game_get_summary")
    def get_summary(self) -> list:
        round_list = []
        for r in self.rounds:
            round_list.append(r.get_round_dict())
        return round_list

class Round:
    """
    Defines a round within a game.
    A round is made up of a number of turns.
    The init will start the roound and create a turn object for each player.
    Then it will judge the results of the round.
    """
    def __init__(self, game_id, round_no, players) -> None:
        with tracer.start_as_current_span("round_init") as round_init_span:

            # Initialize the round and set trace attributes
            logger.debug("Initializing round")
            self.turns = []
            self.game_id = game_id
            round_init_span.set_attribute("round.game_id", str(self.game_id))
            self.round_no = round_no
            round_init_span.set_attribute("round.round_no", self.round_no)
            self.player_count = len(players)
            round_init_span.set_attribute("round.player_count", self.player_count)
            self.throw_total = 0
            self.correct_guesses = 0
            self.players = players

            # Play the round
            logger.debug("Starting round - taking turns")
            self._take_turns()              # call the web services to get each players throw and call
            logger.debug("Judging round - totalling throws and checking calls")
            self._total_throws()            # judge the results
            self._check_calls()             # check guesses against round total
            self._post_summary()            # post the round summary to the players
            if args.interactive: self._print_round_summary()
            return None

    def _take_turns(self) -> None:
        for i in range(0, self.player_count):
            logger.debug("Requesting turn " + str(i+1))
            turn = Turn(self.game_id, self.round_no, self.players[i])
            self.turns.append(turn)
            logger.debug("Turn " + str(i+1) + " complete")
        return None

    # @tracer.start_as_current_span("round_total_throws")
    def _total_throws(self) -> None:
        logger.debug("Totalling throws")
        for t in self.turns:
            self.throw_total += t.throw
        logger.info("Throw total is " + str(self.throw_total))
        return None

    # @tracer.start_as_current_span("round_check_calls")
    def _check_calls(self) -> None:
        logger.debug("Checking calls against throw total.")
        for i in range(0, len(self.turns)):
            logger.debug("Player " + str(i+1) + " call " + str(self.turns[i].call))
            if self.turns[i].call == self.throw_total:
                self.turns[i].get_player().win()
        return None

    # @tracer.start_as_current_span("round_get_round_dict")
    def get_round_dict(self) -> dict:
        turn_dicts = []
        for t in self.turns:
            turn_dicts.append(t.get_turn_dict())

        round_dict = {"game_id": str(self.game_id),
                      "round_no": self.round_no,
                      "turns": turn_dicts
                      }
        return round_dict

    def get_round_total(self) -> int:
        return self.throw_total
    
    def _post_summary(self) -> None:
        logger.debug("Posting round summary")
        _round_record = self.get_round_dict()
        for i in range(0, self.player_count):
            logger.debug("Posting round record to player " + str(i+1))
            try:
                self._response = requests.post(self.players[i].get_url()+"/record/", json=_round_record)
                _status_code = self._response.status_code
                _json_response = self._response.json()
            except requests.exceptions.Timeout:
                # Maybe set up for a retry, or continue in a retry loop
                logger.error("Timeout error posting round record to player " + str(i+1))
            except requests.exceptions.TooManyRedirects:
                # Tell the user their URL was bad and try a different one
                logger.error("Too many redirects error posting round record to player " + str(i+1))
            except requests.exceptions.RequestException as e:
                # catastrophic error. bail.
                logger.error("Catastrophic error posting round record to player " + str(i+1))
        return None

    def _print_round_summary(self) -> None:
        r = self.get_round_dict()     # get round outcomes
        tot = self.get_round_total()  # get round total
        panels = []  # build empty panel list
        panels.append(Panel(f"[bold]Round {r['round_no']}[/bold]\nTotal {tot}", expand=True, width=20))  # add round total panel
        for t in r["turns"]:  # add a panel for each turn
            a = f"[green]{t['player_id']}[/green]" if tot == t["call"] else f"[white]{t['player_id']}[/white]"  # set colour of player name if they guessed correctly
            b = f"Throw: {str(t['throw'])} Call: {str(t['call'])}"  # set throw and call text
            c = a + "\n" + b  # set panel text
            panels.append(Panel(c, expand=True, width=30))  # add panel to list
        
        console.print(Columns(panels))  # print the panels
        return None

class Turn:
    """
    Defines a turn which is made up of a call (guess) and a throw (fingers).
    One turn corresponds to the play of a single player.
    init will start the turn and request the turn from the players api.
    """
    # @tracer.start_as_current_span("turn_init")
    def __init__(self, game_id, round_no, player) -> None:
        logger.debug("Initializing turn")
        self.game_id = game_id
        self.round_no = round_no
        self.player = player
        logger.debug("Generating Request Body")
        request_body = {"reqgameid": str(self.game_id),
                        "reqroundno": self.round_no,
                        "reqplayercount": 2}
        logger.debug("Request body: " + str(request_body))
        logger.debug("Requesting turn from player " + self.player.get_name() + " at " + self.player.get_url() + "/turn/")
        self._response = requests.post(player.get_url()+"/turn/", json=request_body).json()
        logger.debug("Request response: " + str(self._response))
        self.throw = self._response["resthrow"]
        self.call = self._response["rescall"]
        return None

    # @tracer.start_as_current_span("turn_get_turn_dict")
    def get_turn_dict(self) -> dict:
        turn_dict = {"player_id": self.player.player_name, 
                     "throw": self.throw,
                     "call": self.call}
        return turn_dict

    # @tracer.start_as_current_span("turn_get_player")
    def get_player(self) -> Player:
        logger.debug("Getting turn player")
        return self.player


# @tracer.start_as_current_span("main")
def main():
    """
    make a game object this will store the record of game
    a game is made up of a variable number of rounds
    a game continues until one player reaches three points
    a point is earned by winning a round
    """

    for i in range(0, args.num_rounds):
        game = Game()
        time.sleep(args.timeout)

    return None

if __name__ == "__main__":
    main()
