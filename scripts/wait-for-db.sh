#!/bin/bash

host="$1"
port="$2"

echo "Waiting for $host:$port to be available..."

while ! python -c "import socket; socket.create_connection(('$host', $port))" 2>/dev/null; do
  sleep 1
done

echo "$host:$port is available, continuing..."