#!/bin/bash

# Wait for database to be ready
./scripts/wait-for-db.sh db 3306

# Apply database migrations
python manage.py migrate

# Load initial data if needed
if [ "$LOAD_INITIAL_DATA" = "true" ]; then
    ./scripts/load_initial_data.sh
fi

# Execute the command passed to the container
exec "$@"