-- create_tables.sql
-- Complete database schema for Test Case Generator

-- Drop tables if they exist (in correct order due to foreign keys)
DROP TABLE IF EXISTS test_case_requirements CASCADE;
DROP TABLE IF EXISTS test_cases CASCADE;
DROP TABLE IF EXISTS requirements CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;

-- Sessions table - Core session management
CREATE TABLE sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_name VARCHAR(255),
    user_prompt TEXT,
    status VARCHAR(50) DEFAULT 'created',
    rag_context_loaded INTEGER DEFAULT 0,
    rag_enabled BOOLEAN DEFAULT true,
    agent_used VARCHAR(100) DEFAULT 'sequential_workflow',
    workflow_type VARCHAR(50) DEFAULT 'full',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Requirements table - All types of requirements
CREATE TABLE requirements (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
    original_content TEXT NOT NULL,
    edited_content TEXT,
    requirement_type VARCHAR(50) DEFAULT 'functional',
    priority VARCHAR(10) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'active',
    version INTEGER DEFAULT 1,
    source VARCHAR(20) DEFAULT 'agent_generated', -- 'agent_generated', 'user_created', 'rag_context'
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Test cases table - Generated and manual test cases
CREATE TABLE test_cases (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
    test_name VARCHAR(255) NOT NULL,
    test_description TEXT,
    test_steps JSONB,
    expected_results TEXT,
    test_type VARCHAR(50) DEFAULT 'functional',
    priority VARCHAR(10) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'active',
    test_data JSONB DEFAULT '{}',
    preconditions TEXT,
    postconditions TEXT,
    estimated_duration INTEGER DEFAULT 30, -- minutes
    automation_feasible BOOLEAN DEFAULT true,
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Test case to requirements mapping - Many-to-many relationship
CREATE TABLE test_case_requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_case_id VARCHAR(255) REFERENCES test_cases(id) ON DELETE CASCADE,
    requirement_id VARCHAR(255) REFERENCES requirements(id) ON DELETE CASCADE,
    coverage_type VARCHAR(50) DEFAULT 'direct',
    confidence_score DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(test_case_id, requirement_id)
);

-- Projects table - For organizing sessions by project
CREATE TABLE projects (
    project_id VARCHAR(255) PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_user_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Users table - Basic user management
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'tester',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);

CREATE INDEX IF NOT EXISTS idx_requirements_session ON requirements(session_id);
CREATE INDEX IF NOT EXISTS idx_requirements_type ON requirements(requirement_type);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status);

CREATE INDEX IF NOT EXISTS idx_test_cases_session ON test_cases(session_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_type ON test_cases(test_type);
CREATE INDEX IF NOT EXISTS idx_test_cases_status ON test_cases(status);

CREATE INDEX IF NOT EXISTS idx_tcr_test_case ON test_case_requirements(test_case_id);
CREATE INDEX IF NOT EXISTS idx_tcr_requirement ON test_case_requirements(requirement_id);
