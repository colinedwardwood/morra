# READ ME
## How to build docker container
From this directory run:
`docker build -t colinedwardwood/go_player .`  

## How to run the docker container  
### Without MongoDB Atlas support  
`docker run -p 8888:8888 go_player`  
  
### With MongoDB Atlas support  
`docker run -p 8888:8888 go_player --uri='<uri>'`  
Where `<uri>` is the MongoDB Atlas connection string.

## How to run the go binary
### Without MongoDB Atlas support  
`./go_player` will run on port 8888 by default

### With MongoDB Atlas support  
`./go_player --uri='<uri>'`  
Where `<uri>` is the MongoDB Atlas connection string.

### With alternate port
`./go_player --port=8080`  
Where `8080` is the port you want to run the service on.    

