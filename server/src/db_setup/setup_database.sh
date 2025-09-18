#!/bin/bash
# setup_database.sh

echo "🚀 Setting up Test Case Generator Database..."

# Create database and user (adjust credentials as needed)
psql -c "CREATE DATABASE testgen_db;"
psql -c "CREATE USER testgen_user WITH PASSWORD 'testgen_pass';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE testgen_db TO testgen_user;"

# Create tables
psql -d testgen_db -f create_tables.sql

echo "✅ Database schema created!"

# Run data population
python populate_test_data.py

echo "🎉 Database setup complete!"
