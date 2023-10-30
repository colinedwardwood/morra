#!/bin/bash
docker build -t colinedwardwood/go_player ./go_player/.  
docker push colinedwardwood/go_player

docker build -t colinedwardwood/python_player ./python_player/.
docker push colinedwardwood/python_player

docker build -t colinedwardwood/node_player ./node_player/.
docker push colinedwardwood/node_player

docker build -t colinedwardwood/main ./main/.
docker push colinedwardwood/main