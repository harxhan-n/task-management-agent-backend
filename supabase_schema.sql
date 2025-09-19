-- Task Management Database Schema for Supabase
-- Run this SQL in your Supabase SQL Editor to create the necessary tables

-- Create the tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'done')),
    due_date TIMESTAMPTZ,
    priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create an index on status for faster filtering
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- Create an index on priority for faster filtering
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);

-- Create an index on due_date for faster date-based queries
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);

-- Create an index on created_at for ordering
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a trigger to automatically update updated_at when a row is modified
DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data (optional)
INSERT INTO tasks (title, description, status, priority, due_date) VALUES 
    ('Welcome to Task Management', 'This is your first task! You can create, update, and manage tasks using our AI assistant.', 'pending', 'medium', NOW() + INTERVAL '7 days'),
    ('Set up your workspace', 'Configure your development environment and get familiar with the API.', 'in_progress', 'high', NOW() + INTERVAL '3 days'),
    ('Explore AI features', 'Try chatting with the AI assistant to manage your tasks using natural language.', 'pending', 'low', NOW() + INTERVAL '14 days')
ON CONFLICT DO NOTHING;

-- Enable Row Level Security (RLS) - Optional but recommended for production
-- ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- Create a policy for authenticated users (uncomment if you want RLS)
-- CREATE POLICY "Users can view all tasks" ON tasks FOR SELECT USING (true);
-- CREATE POLICY "Users can insert tasks" ON tasks FOR INSERT WITH CHECK (true);
-- CREATE POLICY "Users can update tasks" ON tasks FOR UPDATE USING (true);
-- CREATE POLICY "Users can delete tasks" ON tasks FOR DELETE USING (true);

-- Grant necessary permissions (usually not needed in Supabase)
-- GRANT ALL ON tasks TO authenticated;
-- GRANT ALL ON tasks TO anon;