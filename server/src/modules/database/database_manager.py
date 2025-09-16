# src/modules/database/database_manager.py
import asyncpg
import os
import json
import uuid

class DatabaseManager:
    def __init__(self):
        self.pool = None

    async def initialize(self):
        database_url = os.getenv('DATABASE_URL')
        self.pool = await asyncpg.create_pool(database_url, min_size=5, max_size=20)
        await self.create_essential_tables()
        print("✅ Database initialized with minimal schema!")

    async def create_essential_tables(self):
        async with self.pool.acquire() as conn:
            # Just the 4 essential tables
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    project_name VARCHAR(255),
                    user_prompt TEXT,
                    status VARCHAR(50) DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS requirements (
                    id VARCHAR(255) PRIMARY KEY,
                    session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
                    original_content TEXT NOT NULL,
                    edited_content TEXT,
                    requirement_type VARCHAR(50) DEFAULT 'functional',
                    priority VARCHAR(10) DEFAULT 'medium',
                    status VARCHAR(20) DEFAULT 'active',
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS test_cases (
                    id VARCHAR(255) PRIMARY KEY,
                    session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
                    test_name VARCHAR(255) NOT NULL,
                    test_description TEXT,
                    test_steps JSONB,
                    expected_results TEXT,
                    test_type VARCHAR(50),
                    priority VARCHAR(10) DEFAULT 'medium',
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS test_case_requirements (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    test_case_id VARCHAR(255) REFERENCES test_cases(id) ON DELETE CASCADE,
                    requirement_id VARCHAR(255) REFERENCES requirements(id) ON DELETE CASCADE,
                    coverage_type VARCHAR(50) DEFAULT 'direct',
                    UNIQUE(test_case_id, requirement_id)
                );

                CREATE INDEX IF NOT EXISTS idx_requirements_session ON requirements(session_id);
                CREATE INDEX IF NOT EXISTS idx_test_cases_session ON test_cases(session_id);
            ''')

    async def save_simple_workflow_result(self, session_id: str, user_id: str,
                                         project_name: str, user_prompt: str):
        """Save just the essential session info"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO sessions (session_id, user_id, project_name, user_prompt)
                VALUES ($1, $2, $3, $4)
            ''', session_id, user_id, project_name, user_prompt)

    async def extract_and_save_requirements(self, session_id: str, requirements_list: list):
        """Save requirements extracted from your agent"""
        async with self.pool.acquire() as conn:
            for i, req_text in enumerate(requirements_list):
                req_id = f"{session_id}_req_{i}"
                await conn.execute('''
                    INSERT INTO requirements (id, session_id, original_content, requirement_type)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO NOTHING
                ''', req_id, session_id, req_text, 'functional')

    async def extract_and_save_test_cases(self, session_id: str, test_cases_list: list):
        """Save test cases and link to requirements"""
        async with self.pool.acquire() as conn:
            for i, test_case in enumerate(test_cases_list):
                tc_id = f"{session_id}_tc_{i}"

                # Save test case
                await conn.execute('''
                    INSERT INTO test_cases
                    (id, session_id, test_name, test_description, test_steps,
                     expected_results, test_type, priority)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO NOTHING
                ''', tc_id, session_id, test_case.get('test_name'),
                test_case.get('test_description'), json.dumps(test_case.get('test_steps', [])),
                test_case.get('expected_results'), test_case.get('test_type'),
                test_case.get('priority', 'medium'))

                # Link to requirements (if provided)
                req_ids = test_case.get('requirement_ids', [])
                for req_id in req_ids:
                    await conn.execute('''
                        INSERT INTO test_case_requirements (test_case_id, requirement_id)
                        VALUES ($1, $2)
                        ON CONFLICT (test_case_id, requirement_id) DO NOTHING
                    ''', tc_id, req_id)

# Global instance
db_manager = DatabaseManager()
