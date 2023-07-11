// this is the simplest player, simply generates throws and calls and doesn't 
// record the record of play to a database at this time

// This is the name of the application, used in logging and metrics
const app_name = "node_player.bot"

// Metrics Setup
// We will use the prom-client library to record metrics
const Prometheus = require('prom-client'); // This creates an instance of prom-client for us to use
const register = new Prometheus.Registry(); // Defines a metrics registry, a list of metrics that prom-client is collecting.
register.setDefaultLabels({app: app_name}) // add a default label to all metrics, the app name
Prometheus.collectDefaultMetrics({register}) // collect the default metrics, and register them with our registry
const http_request_counter = new Prometheus.Counter({ // add new custom metric, a counter to count the number of HTTP requests
  name: 'morra_http_request_count',
  help: 'Count of HTTP requests made to my app',
  labelNames: ['method', 'route', 'statusCode'],
});
register.registerMetric(http_request_counter); // register our new metric http_request_counter
const morra_throw_value = new Prometheus.Histogram({ // add new custom metric, a histogram to record the distribution of throws
  name: 'morra_throw_value',
  help: 'Throws made by node_player.bot',
  labelNames: ['throw'],
  buckets: [1, 2, 3, 4, 5, ]
});
register.registerMetric(morra_throw_value); // register our new metric morra_throw_value


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

// Express web framework is used to handle the HTTP requests and responses
var express = require("express"); // use the express web framework
var app = express(); // create an express app instance

// helper function to generate a random integer between 0 and max
function getRandomInt(max) { // helper function
    return Math.floor(Math.random() * max);
}

// middleware to record the HTTP request count
app.use(function(req, res, next) {
  http_request_counter.labels({method: req.method, route: req.originalUrl, statusCode: res.statusCode}).inc();  // Increment the HTTP request counter
  next(); // call the next middleware function
});

// middleware to handle the JSON body of the HTTP request
app.use(express.json()); // this tells express which middleware to use

// This section defines our routes
// handle the post to the turn endpoint, then return the throw and call
app.post("/turn", function(request, response) {

    // Generate a random throw, log it and record it in the histogram
    logger.info("Turn request received"); // log the request
    var thrw = getRandomInt(4) + 1 // generate a random throw
    logger.info("Throw: " + thrw); // log the throw
    morra_throw_value.labels("throw").observe(thrw) // record the throw in the histogram

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

// expose an HTTP metrics endpoint so that we can get at the metrics
app.get('/metrics', function(req, res) {
    res.setHeader('Content-Type',register.contentType)
    register.metrics().then(data => res.status(200).send(data))
});

// Main entry point
logger.info("Starting " + app_name); // handle the call to the record end point, discard the post and return 200 OK
app.listen(8889); // run the server
