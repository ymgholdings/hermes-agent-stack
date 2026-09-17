-- Agentic OS Database Schema
-- PostgreSQL 16

-- Tasks table: stores coding tasks and their execution state
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    spec TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    code TEXT,
    test_output TEXT,
    error_trace TEXT,
    iteration_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);

-- Comments
COMMENT ON TABLE tasks IS 'Coding tasks in the Karpathy validation loop';
COMMENT ON COLUMN tasks.spec IS 'Plain-language specification of the coding task';
COMMENT ON COLUMN tasks.status IS 'Task status: pending, decomposed, implemented, reviewed, testing_failed, completed, failed';
COMMENT ON COLUMN tasks.code IS 'Final generated code (solution.py)';
COMMENT ON COLUMN tasks.test_output IS 'Output from pytest execution';
COMMENT ON COLUMN tasks.error_trace IS 'Error feedback for next iteration';
COMMENT ON COLUMN tasks.iteration_count IS 'Number of Karpathy loop iterations (max 3)';
