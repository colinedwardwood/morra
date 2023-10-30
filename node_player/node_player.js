// This is the simplest player, simply generates throws and calls and doesn't 
// record the record of play to a database at this time
// Metrics are generated using the prom-client library and exposed on the /metrics endpoint
// Logging is done using the winston library
// Traceability is done using automatic instrumentation of the express framework using the opentelemetry library

// Global Variables
const app_name = "node_player.bot" // This is the name of the application, used in logging and metrics

// Logging Setup
// We will use the winston logging library to log to the console
const { createLogger, format, transports, log } = require("winston"); // import winston
const logLevels = {  // set our own custom log levels
  fatal: 0,
  error: 1,
  warn: 2,
  info: 3,
  debug: 4,
  trace: 5,
};
const logger = createLogger({ // create our logger instance
    levels: logLevels, // use our own log levels
    format: format.combine(format.timestamp(), format.json()), // include a timestamp in each entry and format each entry as json
    defaultMeta: { // default meta data to include in every log entry
        service: app_name,
      },
    transports: [new transports.Console()], // log to the console
  });


// Metrics Setup
// We will use the prom-client library to record metrics
const promBundle = require("express-prom-bundle");
const express = require("express");
const app = express();
const metricsMiddleware = promBundle({includeMethod: true});




// helper function to generate a random integer between 0 and max
function getRandomInt(max) { // helper function
    return Math.floor(Math.random() * max);
}

// This section defines our middleware
app.use(metricsMiddleware); // use the metrics middleware
app.use(express.json()); // use the json middlewware

// This section defines our routes
// handle the post to the turn endpoint, then return the throw and call
app.post("/turn", function(request, response) {

    // Generate a random throw, log it and record it in the histogram
    logger.info("Turn request received"); // log the request
    var thrw = getRandomInt(4) + 1 // generate a random throw
    logger.info("Throw: " + thrw); // log the throw

    // Generate a random call (based on the number of players), log it and return it
    var call = thrw
    for (let i = 0; i < request.body.reqplayercount - 1; i++) {
        call += getRandomInt(4) + 1;
    }
    logger.info("Call: " + call);

    // Build the response, send it and log it
    const res = {resgameid:request.body.reqgameid, resroundno:request.body.reqroundno, resthrow:thrw, rescall:call}
    response.status(200).json(res);
    logger.child({response: res}).info("Turn response sent");
});

// Main entry point
logger.info("Starting " + app_name); // handle the call to the record end point, discard the post and return 200 OK
app.listen(80); // run the server
