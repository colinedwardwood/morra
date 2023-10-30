# This is the second simplest player, simply generates throws and calls and doesn't 
# record the record of play to a database at this time but is manually instrumented for tracing
# Metrics are generated 
# Logging is done using the logging library
# Traceability is done using manual instrumentation and the FastAPIInstrumentor

# IMPORTS
from fastapi import FastAPI
from pydantic import BaseModel
from random import randint
import logging
from prometheus_client import Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

# CONSTANTS
PLAYER_ID = "python_player"  # set player name/id here

# TRACING SETUP
resource = Resource(attributes={ SERVICE_NAME: PLAYER_ID + ".bot" })
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="agent:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("player_turn.tracer")

# LOGGING SETUP
logging.basicConfig(
    format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)

# METRICS SETUP
morra_throw_value = Histogram('morra_throw_value', 'Throws made by node_player.bot', buckets=[1, 2, 3, 4, 5,])

# DATA MODELS
class Turn_Request(BaseModel):
    reqgameid: str
    reqroundno: int
    reqplayercount: int

class Turn_Response(BaseModel):
    resgameid: str
    resroundno: int
    resthrow: int
    rescall: int

# HELPER FUNCTIONS
def make_call(throw_value, player_count) -> int:
    """Generates an integer (call) based on the throw value and player count

    Args:
        throw_value (_type_): the value of the players throw
        player_count (_type_): how many players are in the game

    Returns:
        int: the players throw value, which is their guess at what the total of all throws will be
    """
    # call must: be greater than throw_value + player_count
    with tracer.start_as_current_span("make_call") as call_span:
        logger.debug("Generating call")

        call = throw_value + ((player_count - 1) * randint(1, 5))
        
        logger.debug("Call generated")
        call_span.set_attribute("player.id", PLAYER_ID)
        call_span.set_attribute("call.value", call)
        return call


def make_throw() -> int:
    """Generates a random integer between 1 and 5

    This is the players throw. The throw is simply a random integer between 1 and 5 representing the number of fingers the player is holding out.

    Returns:
        int: the players throw value
    """    
    with tracer.start_as_current_span("make_throw") as throw_span:
        logger.debug("Generating throw")

        throw = randint(1, 5)

        logger.debug("Throw generated")
        throw_span.set_attribute("player.id", PLAYER_ID)
        throw_span.set_attribute("throw.value", throw)
        return throw


# Initialize the FastAPI app and instrument it with Prometheus
app = FastAPI()
Instrumentator().instrument(app).expose(app) # Expose metrics for /metrics endpoint


@app.get("/ready")  # the ready endpoint used to check if the player is running
async def ready() -> bool:
    """Returns true if the player is running

    This is used by the game to check if the player is running and ready to receive turn requests.

    Returns:
        bool: True
    """    
    logger.debug("Ready check received")
    return True

@app.post("/turn")  # the turn endpoint used to receive turn requests and respond with turn: call and throw
async def create_turn(turn_request: Turn_Request) -> Turn_Response:
    """Respond to the turn request with a turn response

    This is the main function of the player. It receives a turn request, generates a throw and call and returns a turn response.

    Args:
        turn_request (Turn_Request): the request from the game for a turn from the player, see DATA_MODELS above for structure of request

    Returns:
        Turn_Response: The response to the turn request, see DATA_MODELS above for structure of response
    """ 

    logger.debug("Turn request received")
    logger.debug("Trying throw")
    throw_value = make_throw()

    logger.debug("Trying call")
    call_value = make_call(throw_value, turn_request.reqplayercount)

    # tracing
    current_span = trace.get_current_span()
    current_span.set_attribute("game.id", turn_request.reqgameid)
    current_span.set_attribute("player.id", PLAYER_ID)
    current_span.set_attribute("throw.value", throw_value)
    current_span.set_attribute("call.value", call_value)

    # metrics
    morra_throw_value.observe(throw_value)
    logger.debug("Returning Turn_Reponse object")

    return Turn_Response(resgameid=turn_request.reqgameid,
                          resroundno=turn_request.reqroundno,
                          resplayerid=PLAYER_ID,
                          resthrow=throw_value,
                          rescall=call_value)

FastAPIInstrumentor.instrument_app(app)
