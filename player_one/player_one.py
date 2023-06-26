# player_one.py

from fastapi import FastAPI
from pydantic import BaseModel
from random import randint
import logging
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

# CONSTANTS
PLAYER_ID = "snake_random"                            # set player name/id here

# MANUAL TRACING SETUP
resource = Resource(attributes={
    SERVICE_NAME: PLAYER_ID + ".bot"
})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("player_turn.tracer")      # aquire tracer

# CONFIGURE TRADITIONAL LOGGING FORMAT
logging.basicConfig(
    format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Turn_Request(BaseModel):
    game_id: str
    round_no: int
    player_count: int


class Turn_Response(BaseModel):
    game_id: str
    round_no: int
    throw: int
    call: int


def make_call(throw_value, player_count) -> int:
    # call cannot be random
    # call must: be greater than throw_value + player_count
    with tracer.start_as_current_span("make_call") as call_span:
        logger.debug("Generating call")

        call = throw_value + player_count

        logger.debug("Call generated")
        call_span.set_attribute("player.id", PLAYER_ID)
        call_span.set_attribute("call.value", call)
        return call


def make_throw() -> int:
    # throw can be completely random
    with tracer.start_as_current_span("make_throw") as throw_span:
        logger.debug("Generating throw")

        throw = randint(1, 5)

        logger.debug("Throw generated")
        throw_span.set_attribute("player.id", PLAYER_ID)
        throw_span.set_attribute("throw.value", throw)
        return throw


app = FastAPI()


@app.post("/turn/")
async def create_turn(turn_request: Turn_Request):
    logger.debug("Turn request received")
    logger.debug("Trying throw")

    throw_value = make_throw()

    call_value = make_call(throw_value, turn_request.player_count)

    logger.debug("turn response sent")
    current_span = trace.get_current_span()
    current_span.set_attribute("game.id", turn_request.game_id)
    current_span.set_attribute("player.id", PLAYER_ID)
    current_span.set_attribute("throw.value", throw_value)
    current_span.set_attribute("call.value", call_value)

    return [Turn_Response(game_id=turn_request.game_id,
                          round_no=turn_request.round_no,
                          player_id=PLAYER_ID,
                          throw=throw_value,
                          call=call_value)]

FastAPIInstrumentor.instrument_app(app)
