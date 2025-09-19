-- Initialize the database with any required setup
-- This file is executed when the PostgreSQL container starts for the first time

-- Create extension for UUID generation (if needed in future)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create any initial data or additional setup here
-- For now, the tables will be created by Alembic migrations

-- You can add initial seed data here if needed
-- INSERT INTO tasks (title, description, status, priority) VALUES 
-- ('Welcome Task', 'This is your first task!', 'pending', 'medium');