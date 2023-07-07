// this is the simplest player, simply generates throws and calls and doesn't 
// record the record of play to a database at this time

// Winston is used for logging
const { createLogger, format, transports, log } = require("winston"); // import winston
const logLevels = {  // set our own log levels
  fatal: 0,
  error: 1,
  warn: 2,
  info: 3,
  debug: 4,
  trace: 5,
};
const logger = createLogger({
    levels: logLevels, // use our own log levels
    format: format.combine(format.timestamp(), format.json()), // include a timestamp and format as json
    defaultMeta: {
        service: "node_player.bot",
      },
    transports: [new transports.Console()], // log to the console
  });

// Express web framework is used to handle the HTTP requests and responses
var express = require("express"); // use the express web framework
var app = express(); // create an express app

// helper function to generate a random integer between 0 and max
function getRandomInt(max) { // helper function
    return Math.floor(Math.random() * max);
}

app.use(express.json()); // this tells express which middleware to use

// handle the post to the turn endpoint, return the throw and call
app.post("/turn", function(request, response) {
    logger.info("Turn request received");

    var thrw = getRandomInt(4) + 1
    logger.info("Throw: " + thrw);

    var call = thrw
    for (let i = 0; i < request.body.reqplayercount - 1; i++) {
        call += getRandomInt(4) + 1;
    }
    logger.info("Call: " + call);
    const res = {resgameid:request.body.reqgameid, resroundno:request.body.reqroundno, resthrow:thrw, rescall:call}
    response.status(200).json(res);
    logger.child({response: res}).info("Turn response sent");
});

// handle the call to the record end point, discard the post and return 200 OK
// app.post("/record", function(request, response) {
//     response.status(200);
// })

//Start the server and make it listen for connections on port 8080
logger.info("Starting node_player");
app.listen(8889);
