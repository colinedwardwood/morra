package main

import (
	"context"
	"encoding/json"
	"flag"      // for handling the parsing of the command line flags
	"fmt"       // for formatting errors
	"log"       // for logging
	"math/rand" // for generating the random calls and throws
	"net/http"  // for the http statuses
	"os"        // for handling cancel signal from user
	"os/signal" // for handling cancel signal from user
	"strconv"   // for converting integers to strings
	"time"      // for handling the timeouts

	"google.golang.org/grpc"                      // for grpc calls to the otel collector endpoint
	"google.golang.org/grpc/credentials/insecure" // for grpc calls to the otel collector endpoint

	"github.com/gin-gonic/gin"                  // HTTP web framework we use for the endpoints
	"go.mongodb.org/mongo-driver/mongo"         // for writing results to MongoDB Atlas
	"go.mongodb.org/mongo-driver/mongo/options" // for writing results to MongoDB Atlas

	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"            // for tracing the gin endpoints
	"go.opentelemetry.io/contrib/instrumentation/go.mongodb.org/mongo-driver/mongo/otelmongo" // for tracing the mongo calls
	"go.opentelemetry.io/otel"                                                                // for general tracing
	"go.opentelemetry.io/otel/attribute"                                                      // for adding attributes to the traces
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"                         // for exporting traces to the otel collector endpoint
	"go.opentelemetry.io/otel/propagation"                                                    // for propagating the trace context
	"go.opentelemetry.io/otel/sdk/resource"                                                   // for adding resource attributes to the traces
	sdktrace "go.opentelemetry.io/otel/sdk/trace"                                             // for tracing
	semconv "go.opentelemetry.io/otel/semconv/v1.17.0"                                        // for exporting traces to stdout

	"github.com/prometheus/client_golang/prometheus/promhttp" // for exposing http gin metrics in prometheus format
)

// Telemetry configuration
var tracer = otel.Tracer("gin-server")

// application flags
var portFlag = flag.Int("port", 80, "Port to listen on, default is 80")
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

func initProvider() (func(context.Context) error, error) {
	ctx := context.Background()
	res, err := resource.New(ctx,
		resource.WithOS(),
		resource.WithProcess(),
		resource.WithAttributes(semconv.ServiceName("go_player.bot")),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create resource: %w", err)
	}

	ctx, cancel := context.WithTimeout(ctx, time.Second)
	defer cancel()
	conn, err := grpc.DialContext(ctx, "agent:4317",
		// Note the use of insecure transport here. TLS is recommended in production.
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create gRPC connection to collector: %w", err)
	}

	// Set up a trace exporter
	traceExporter, err := otlptracegrpc.New(ctx, otlptracegrpc.WithGRPCConn(conn))
	if err != nil {
		return nil, fmt.Errorf("failed to create trace exporter: %w", err)
	}

	// Register the trace exporter with a TracerProvider, using a batch
	// span processor to aggregate spans before export.
	bsp := sdktrace.NewBatchSpanProcessor(traceExporter)
	tracerProvider := sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
		sdktrace.WithResource(res),
		sdktrace.WithSpanProcessor(bsp),
	)
	otel.SetTracerProvider(tracerProvider)

	// set global propagator to tracecontext (the default is no-op).
	otel.SetTextMapPropagator(propagation.TraceContext{})

	// Shutdown will flush any remaining spans and shut down the exporter.
	return tracerProvider.Shutdown, nil
}

func make_throw(c *gin.Context) int {
	_, span := tracer.Start(c.Request.Context(), "make_throw")
	defer span.End()
	log.Println("Making throw")
	var throw = rand.Intn(5) + 1                 // generate a random throw value
	log.Println("Throw: " + strconv.Itoa(throw)) // log the throw value
	span.SetAttributes(attribute.Int("throw", throw))
	return throw
}

func make_call(c *gin.Context, throw_value int, player_count int) int {
	_, span := tracer.Start(c.Request.Context(), "make_call")
	defer span.End()
	log.Println("Making call")
	log.Println("Player count: " + strconv.Itoa(player_count)) // log the player count
	log.Println("Throw value: " + strconv.Itoa(throw_value))   // log the throw value
	var call = throw_value
	for i := 0; i < player_count-1; i++ {
		call += rand.Intn(5) + 1 // generate a random guess for each player in the game and add it to your throw
	}
	span.SetAttributes(attribute.Int("call", call))
	log.Println("Call: " + strconv.Itoa(call)) // log the call value
	return call
}

func turn(c *gin.Context) {
	_, span := tracer.Start(c.Request.Context(), "turn")
	defer span.End()
	log.Println("Turn request received")
	var turn_request Turn_Request                     // variable to store json request
	if err := c.BindJSON(&turn_request); err != nil { // Call BindJSON to bind the received JSON to turn_request
		log.Println("Error binding JSON")
		return
	}

	request_json, err := json.Marshal(turn_request) // convert request body to json
	if err != nil {
		log.Println("Error marshalling request to JSON")
	}
	log.Println("Request: " + string(request_json)) // log the request body

	throw := make_throw(c)                                     // generate a random throw value
	call := make_call(c, throw, turn_request.Req_Player_Count) // generate a call value based on number of players

	var response = Turn_Response{ // build a response body
		Res_Game_ID:  turn_request.Req_Game_ID,
		Res_Round_No: turn_request.Req_Player_Count,
		Res_Throw:    throw,
		Res_Call:     call}

	response_json, err := json.Marshal(response) // convert response body to json
	if err != nil {
		log.Println("Error marshalling response to JSON")
	}
	log.Println("Response: " + string(response_json)) // log the response body
	c.IndentedJSON(http.StatusOK, response)           // serializes the given struct as pretty JSON (indented + endlines) into the response body
}

func record(c *gin.Context) {
	_, span := tracer.Start(c.Request.Context(), "record")
	defer span.End()
	if *uriFlag == "null" {
		log.Println("No MongoDB connection string specified, not recording game history.")
		c.String(http.StatusForbidden, "No MongoDB connection string specified, not recording game history.")
		span.SetAttributes(attribute.String("Record", "No mongodb connection string provided, round will not be recorded."))
	} else {
		log.Println("MongoDB connection string specified, attempting to record game history.")
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
		log.Println("Creating MongoDB context:", *uriFlag)
		opts := options.Client()                                                // create mongodb clientoptions instance
		opts.Monitor = otelmongo.NewMonitor()                                   // add otel monitor to clientoptions instance
		opts.ApplyURI(*uriFlag)                                                 // apply mongodb connection string to clientoptions instance
		ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second) // get connection context object
		defer cancel()                                                          // defer the cancel of the context until function completes, needed since it's asynchronous connect to mongo
		client, err := mongo.Connect(ctx, opts)                                 // connect to mongodb using our clientoptions instance
		if err != nil {
			log.Println("Error creating MongoDB client", err)
			return
		}
		roundCol := client.Database("gamehistory").Collection("rounds") // get connection handle to round database and collection

		// Finally, we write the record to mongodb
		_, err = roundCol.InsertOne(c.Request.Context(), record_post) // write the record
		if err != nil {
			c.Status(http.StatusInternalServerError) // return status 500 internal service
			log.Println("Error writing record to MongoDB: ", err)
			span.SetAttributes(attribute.String("Record", "Error, round not successfully written to database."))
		} else {
			c.Status(http.StatusCreated) // return only status 201 record created
			log.Println("Record written to MongoDB")
			span.SetAttributes(attribute.String("Record", "Round successfully written to database."))
		}

		// defer disconnect until function completes, needed since it's asynchronous connect to mongo
		defer func() {
			client.Disconnect(ctx)
			log.Println("Disconnected from MongoDB")
		}()
	}
}

func main() {
	// Handle cancel signal from user
	ctx, cancel := signal.NotifyContext(context.Background(), os.Kill)
	defer cancel()

	// Log startup of the application
	log.Println("Starting application as", os.Args[0:])

	// Initialise the tracer provider and defer a shutdown till main completes
	shutdown, err := initProvider() // initialize the otel provider
	if err != nil {
		log.Fatal(err)
	}
	defer func() {
		if err := shutdown(ctx); err != nil {
			log.Fatal("failed to shutdown TracerProvider: %w", err)
		}
	}()

	// App has two flags, one for connecting to a mongodb backend, where the record of games can be written
	// and one for changing the default port of the application
	flag.Parse()
	if *portFlag == 80 {
		log.Println("Application starting with default port 80")
	} else {
		log.Println("Application starting with port flag(s): ", *portFlag)
	}
	if *uriFlag == "null" {
		log.Println("Application starting without MongoDB")
	} else {
		log.Println("Application starting with MongoDB URI provided")
	}

	// Run the Gin server
	gin.SetMode(gin.ReleaseMode)                          // set this flag once you are ready to deploy the application in production
	router := gin.Default()                               // initialises a router with default middleware
	router.Use(otelgin.Middleware("go_player.bot"))       // add otel middleware to the router
	router.POST("/turn", turn)                            // initialize the POST endpoint for turn requests
	router.POST("/record", record)                        // initialize the POST endpoint for receiving and recording the round record
	router.GET("/metrics", gin.WrapH(promhttp.Handler())) // initialize the GET endpoint for prometheus metrics
	_ = router.Run(":" + strconv.Itoa(*portFlag))         // run the service
}
