package main

import (
	"math/rand"
	"net/http"

	"github.com/gin-gonic/gin"
)

type Turn_Request struct {
	Req_Game_ID      string `json:"reqgameid"`
	Req_Round_No     int    `json:"reqroundno"`
	Req_Player_Count int    `json:"reqplayercount"`
}

type Turn_Response struct {
	Res_Game_ID  string `json:"resgameid"`
	Res_Round_No int    `json:"resroundno"`
	Res_Throw    int    `json:"resthrow"`
	Res_Call     int    `json:"rescall"`
}

func make_throw() int {
	var throw = rand.Intn(5) + 1
	return throw
}

func make_call(throw_value int, player_count int) int {
	var call = throw_value
	for i := 0; i < player_count; i++ {
		call += rand.Intn(5) + 1
	}
	return call
}

func create_turn(c *gin.Context) {
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

func main() {
	router := gin.Default()           // initialises a router with the default functions.
	router.POST("/turn", create_turn) // initialize the POST endpoint
	router.Run(":8888")               // run the service
}
