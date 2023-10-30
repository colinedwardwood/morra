#!/bin/bash
apt update
apt install -y curl
status=$(curl -s localhost:12345/-/ready)
if [[ "$status" == "Agent is Ready." ]]; then
  exit 0
else
  exit 1
fi
