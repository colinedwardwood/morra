// this is the simplest player, simply generates throws and calls and doesn't 
// record the record of play
var express = require("express"); // use the express web framework
var app = express(); // create an express app

function getRandomInt(max) { // helper function
    return Math.floor(Math.random() * max);
}

app.use(express.json()); // this tells express which middleware to use

// handle the post to the turn endpoint, return the throw and call
app.post("/turn", function(request, response) {
    var thrw = getRandomInt(4) + 1
    var call = thrw
    for (let i = 0; i < request.body.reqplayercount - 1; i++) {
        call += getRandomInt(4) + 1;
    }

    response.status(200).json({resgameid:request.body.reqgameid, resroundno:request.body.reqroundno, resthrow:thrw, rescall:call});
});

// handle the call to the record end point, discard the post and return 200 OK
app.post("/record", function(request, response) {
    response.status(200);
})

//Start the server and make it listen for connections on port 8080
app.listen(8889);
