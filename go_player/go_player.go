package main

import (
	"context"
	"log"
	"math/rand"
	"net/http"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

var password = os.Args[1]
var uri = "mongodb+srv://admin:" + password + "@cluster0.b1ho5nl.mongodb.net/?retryWrites=true&w=majority"

type Turn_Request struct {
	Req_Game_ID      string `json:"reqgameid"`
	Req_Round_No     int    `json:"reqroundno"`
	Req_Player_Count int    `json:"reqplayercount"`
	/* Sample Data
	{
		"reqgameid":"123-456-789",
		"reqroundno":1,
		"reqplayercount":2
	}
	*/
}

type Turn_Response struct {
	Res_Game_ID  string `json:"resgameid"`
	Res_Round_No int    `json:"resroundno"`
	Res_Throw    int    `json:"resthrow"`
	Res_Call     int    `json:"rescall"`
}

type Record_Post struct {
	Rec_Game_ID  string `json:"recgameid" bson:"recgameid"`
	Rec_Round_No int    `json:"recroundno" bson:"recroundno"`
	Rec_Round    []struct {
		Rec_Player_ID string `json:"recplayerid" bson:"recplayerid"`
		Rec_Call      int    `json:"reccall" bson:"reccall"`
		Rec_Turn      int    `json:"recturn" bson:"recturn"`
	} `json:"recround" bson:"recround"`
	/*  Sample structure
	{
		"recgameid": "123-456-789",
		"recroundno": 1,
		"recround": [{
				"recplayerid": "987-654-321",
				"reccall": 4,
				"recturn": 3
			},
			{
				"recplayerid": "987-654-322",
				"reccall": 1,
				"recturn": 2
			}
		]
	}
	*/
}

func make_throw() int {
	var throw = rand.Intn(5) + 1 // generate a random throw value
	return throw
}

func make_call(throw_value int, player_count int) int {
	var call = throw_value
	for i := 0; i < player_count; i++ {
		call += rand.Intn(5) + 1 // generate a random guess for each player in the game and add it to your throw
	}
	return call
}

func turn(c *gin.Context) {
	var turn_request Turn_Request                     // variable to store json request
	if err := c.BindJSON(&turn_request); err != nil { // Call BindJSON to bind the received JSON to turn_request
		return
	}

	throw := make_throw()                                   // generate a random throw value
	call := make_call(throw, turn_request.Req_Player_Count) // generate a call value based on number of players

	var response = Turn_Response{ // build a response body
		Res_Game_ID:  turn_request.Req_Game_ID,
		Res_Round_No: turn_request.Req_Player_Count,
		Res_Throw:    throw,
		Res_Call:     call}

	c.IndentedJSON(http.StatusOK, response) // serializes the given struct as pretty JSON (indented + endlines) into the response body
}

func record(c *gin.Context) {
	// The post method will send a json object which will be in the gin.Context
	// Context is the most important part of gin. It allows us to pass variables
	// between middleware, manage the flow, validate the JSON of a request and render a JSON response for example.
	log.Println("Bind received JSON to gin context")
	var record_post Record_Post                      // variable to store json post data received
	if err := c.BindJSON(&record_post); err != nil { // Call BindJSON to bind the received JSON to record_post
		log.Println("Error binding JSON")
		return
	}

	// We're going to write the posted data to mongodb, we need a mongoclient object that points to our mongo atlas db (saas)
	// The MongoDB Go Driver uses the context package from Go's standard library to allow applications to signal timeouts and
	// cancellations for any blocking method call. A blocking method relies on an external event, such as a network input or output,
	// to proceed with its task. We want to perform an insert operation on on mongodb within 10 seconds, so we use a Context with
	// a timeout. If the operation doesn't complete within the timeout, the method returns an error.
	log.Println("Create MongoDB context")
	client, err := mongo.NewClient(options.Client().ApplyURI(uri)) // get mongo client object
	if err != nil {
		log.Println("Error creating MongoDB client.")
		return
	}
	ctx, _ := context.WithTimeout(context.Background(), 10*time.Second) // get connection context object
	err = client.Connect(ctx)                                           // connect to database using our context
	if err != nil {
		log.Println("Error connecting to MongoDB")
		return
	}
	roundCol := client.Database("gamehistory").Collection("rounds") // get connection handle to round database and collection

	log.Println("Write the record to MongoDB")
	log.Println(record_post)
	_, err = roundCol.InsertOne(ctx, record_post) // write the record
	if err != nil {
		c.Status(http.StatusInternalServerError) // return status 500 internal service
	} else {
		c.Status(http.StatusCreated) // return only status 201 record created
	}

	defer client.Disconnect(ctx) // defer disconnect until function completes, needed since it's asynchronous connect to mongo
}

func main() {
	router := gin.Default()        // initialises a router with the default functions.
	router.POST("/turn", turn)     // initialize the POST endpoint for turn requests
	router.POST("/record", record) // initialize the POST endpoint for receiving and recording the round record
	router.Run(":8888")            // run the service
}
