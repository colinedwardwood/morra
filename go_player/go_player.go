package main

import (
	"context"
	"flag"
	"log"
	"math/rand"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// Simple method to avoid committing mongodb password to github
var portFlag = flag.Int("port", 8888, "Port to listen on, default is 8888")
var uriFlag = flag.String("uri", "null", "MongoDB Atlas connection string, if unspecified, no record of games will be written.")

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
	if *uriFlag == "null" {
		log.Println("No MongoDB connection string specified, not recording game history.")
		c.String(http.StatusForbidden, "No MongoDB connection string specified, not recording game history.")

	} else {
		log.Println("MongoDB connection string specified, attempting to record game history.")

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
		client, err := mongo.NewClient(options.Client().ApplyURI(*uriFlag)) // get mongo client object
		if err != nil {
			log.Println("Error creating MongoDB client.")
			return
		}
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second) // get connection context object
		defer cancel()                                                           // cancel context when function completes
		err = client.Connect(ctx)                                                // connect to database using our context
		if err != nil {
			log.Println("Error connecting to MongoDB")
			return
		} else {
			log.Println("Connected to MongoDB")
		}
		roundCol := client.Database("gamehistory").Collection("rounds") // get connection handle to round database and collection

		// Finally, we write the record to mongodb
		_, err = roundCol.InsertOne(ctx, record_post) // write the record
		if err != nil {
			c.Status(http.StatusInternalServerError) // return status 500 internal service
			log.Println("Error writing record to MongoDB: ", err)
		} else {
			c.Status(http.StatusCreated) // return only status 201 record created
			log.Println("Record written to MongoDB")
		}

		defer func() {
			client.Disconnect(ctx) // defer disconnect until function completes, needed since it's asynchronous connect to mongo
			log.Println("Disconnected from MongoDB")
		}()
	}
}

func main() {
	flag.Parse()
	if *portFlag == 8888 {
		log.Println("Application starting with default port 8888")
	} else {
		log.Println("Application starting with port flag(s): ", *portFlag)
	}
	if *uriFlag == "null" {
		log.Println("Application starting without MongoDB")
	} else {
		log.Println("Application starting with MongoDB URI provided")
	}
	router := gin.Default() // initialises a router with the default functions.
	// gin.SetMode(gin.ReleaseMode)
	router.POST("/turn", turn)     // initialize the POST endpoint for turn requests
	router.POST("/record", record) // initialize the POST endpoint for receiving and recording the round record
	router.Run(":8888")            // run the service
}
