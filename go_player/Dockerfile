# specify the base image to  be used for the application
FROM golang:1.20

# create a working directory inside the image
WORKDIR /app

# copy Go modules and dependencies to image
COPY go.mod go.sum ./

# download Go modules and dependencies
RUN go mod download

# copy directory files i.e all files ending with .go
COPY ./go_player.go ./

# compile application
RUN go build -o go_player .
# tells Docker that the container listens on specified network ports at runtime
EXPOSE 80

# command to be used to execute when the image is used to start a container
ENTRYPOINT [ "/app/go_player" ]