# src/modules/database/database_manager.py
import asyncpg
import os
import json
import uuid
from typing import List, Dict, Any, Optional
from config import settings

class DatabaseManager:
    def __init__(self):
        self.pool = None

    async def initialize(self):
        database_url = settings.database_url
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
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
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
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
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

    # ===============================
    # SESSION MANAGEMENT METHODS
    # ===============================

    async def create_session(self, session_id: str, user_id: str, project_name: str, user_prompt: str):
        """Create a new session"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO sessions (session_id, user_id, project_name, user_prompt, status)
                VALUES ($1, $2, $3, $4, 'in_progress')
            ''', session_id, user_id, project_name, user_prompt)

    async def update_session_status(self, session_id: str, status: str):
        """Update session status"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE sessions
                SET status = $1, updated_at = NOW()
                WHERE session_id = $2
            ''', status, session_id)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT session_id, user_id, project_name, user_prompt, status, created_at, updated_at
                FROM sessions WHERE session_id = $1
            ''', session_id)

            if row:
                return dict(row)
            return None

    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT s.session_id, s.project_name, s.status, s.created_at, s.updated_at,
                       COUNT(DISTINCT r.id) as requirements_count,
                       COUNT(DISTINCT t.id) as test_cases_count
                FROM sessions s
                LEFT JOIN requirements r ON s.session_id = r.session_id AND r.status = 'active'
                LEFT JOIN test_cases t ON s.session_id = t.session_id AND t.status = 'active'
                WHERE s.user_id = $1
                GROUP BY s.session_id, s.project_name, s.status, s.created_at, s.updated_at
                ORDER BY s.created_at DESC
            ''', user_id)

            return [dict(row) for row in rows]

    # ===============================
    # REQUIREMENTS MANAGEMENT METHODS
    # ===============================

    async def save_requirements(self, session_id: str, requirements: List[str]):
        """Save requirements extracted from workflow"""
        async with self.pool.acquire() as conn:
            for i, req_text in enumerate(requirements):
                req_id = f"{session_id}_req_{uuid.uuid4().hex[:8]}"
                await conn.execute('''
                    INSERT INTO requirements (id, session_id, original_content, requirement_type)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO NOTHING
                ''', req_id, session_id, req_text, 'functional')

    async def get_requirements(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all requirements for a session"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT id, session_id, original_content, edited_content,
                       requirement_type, priority, status, version, created_at, updated_at
                FROM requirements
                WHERE session_id = $1 AND status != 'deleted'
                ORDER BY created_at ASC
            ''', session_id)

            return [dict(row) for row in rows]

    async def update_requirements(self, session_id: str, requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update existing requirements with user edits"""
        updated_count = 0
        async with self.pool.acquire() as conn:
            for req in requirements:
                req_id = req.get('id')
                edited_content = req.get('content') or req.get('edited_content')

                if req_id and edited_content:
                    await conn.execute('''
                        UPDATE requirements
                        SET edited_content = $1, updated_at = NOW(), version = version + 1
                        WHERE id = $2 AND session_id = $3
                    ''', edited_content, req_id, session_id)
                    updated_count += 1

        return {"updated_count": updated_count, "session_id": session_id}

    async def add_requirement(self, session_id: str, content: str, req_type: str = 'functional') -> Dict[str, Any]:
        """Add a new user-created requirement"""
        req_id = f"{session_id}_req_user_{uuid.uuid4().hex[:8]}"
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO requirements (id, session_id, original_content, requirement_type, status)
                VALUES ($1, $2, $3, $4, 'user_created')
            ''', req_id, session_id, content, req_type)

        return {"requirement_id": req_id, "status": "created"}

    # ===============================
    # TEST CASES MANAGEMENT METHODS
    # ===============================

    async def save_test_cases(self, session_id: str, test_cases: List[Dict[str, Any]]):
        """Save test cases and link to requirements"""
        async with self.pool.acquire() as conn:
            for i, test_case in enumerate(test_cases):
                tc_id = f"{session_id}_tc_{uuid.uuid4().hex[:8]}"

                # Save test case
                await conn.execute('''
                    INSERT INTO test_cases
                    (id, session_id, test_name, test_description, test_steps,
                     expected_results, test_type, priority, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active')
                    ON CONFLICT (id) DO NOTHING
                ''', tc_id, session_id,
                test_case.get('test_name', f'Test Case {i+1}'),
                test_case.get('test_description', ''),
                json.dumps(test_case.get('test_steps', [])),
                test_case.get('expected_results', ''),
                test_case.get('test_type', 'functional'),
                test_case.get('priority', 'medium'))

                # Link to requirements (if provided)
                req_ids = test_case.get('requirement_ids', [])
                for req_id in req_ids:
                    await conn.execute('''
                        INSERT INTO test_case_requirements (test_case_id, requirement_id)
                        VALUES ($1, $2)
                        ON CONFLICT (test_case_id, requirement_id) DO NOTHING
                    ''', tc_id, req_id)

    async def get_test_cases(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all test cases for a session with requirement links"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT t.id, t.session_id, t.test_name, t.test_description,
                       t.test_steps, t.expected_results, t.test_type, t.priority,
                       t.status, t.created_at, t.updated_at,
                       COALESCE(
                           json_agg(
                               DISTINCT jsonb_build_object('requirement_id', tcr.requirement_id)
                           ) FILTER (WHERE tcr.requirement_id IS NOT NULL),
                           '[]'::json
                       ) as linked_requirements
                FROM test_cases t
                LEFT JOIN test_case_requirements tcr ON t.id = tcr.test_case_id
                WHERE t.session_id = $1 AND t.status = 'active'
                GROUP BY t.id, t.session_id, t.test_name, t.test_description,
                         t.test_steps, t.expected_results, t.test_type, t.priority,
                         t.status, t.created_at, t.updated_at
                ORDER BY t.created_at ASC
            ''', session_id)

            result = []
            for row in rows:
                row_dict = dict(row)
                # Parse JSON test_steps if it's a string
                if isinstance(row_dict.get('test_steps'), str):
                    try:
                        row_dict['test_steps'] = json.loads(row_dict['test_steps'])
                    except:
                        row_dict['test_steps'] = []
                result.append(row_dict)

            return result

    # ===============================
    # ANALYTICS AND REPORTING METHODS
    # ===============================

    async def get_coverage_report(self, session_id: str) -> Dict[str, Any]:
        """Generate requirements coverage report"""
        async with self.pool.acquire() as conn:
            # Get total requirements
            total_req_row = await conn.fetchrow('''
                SELECT COUNT(*) as total FROM requirements
                WHERE session_id = $1 AND status != 'deleted'
            ''', session_id)
            total_requirements = total_req_row['total']

            # Get covered requirements
            covered_req_row = await conn.fetchrow('''
                SELECT COUNT(DISTINCT r.id) as covered
                FROM requirements r
                JOIN test_case_requirements tcr ON r.id = tcr.requirement_id
                JOIN test_cases t ON tcr.test_case_id = t.id
                WHERE r.session_id = $1 AND r.status != 'deleted' AND t.status = 'active'
            ''', session_id)
            covered_requirements = covered_req_row['covered']

            # Calculate coverage percentage
            coverage_percentage = (covered_requirements / total_requirements * 100) if total_requirements > 0 else 0

            # Get detailed coverage info
            coverage_details = await conn.fetch('''
                SELECT r.id, r.original_content, r.edited_content, r.requirement_type,
                       COUNT(DISTINCT t.id) as test_cases_count,
                       CASE WHEN COUNT(DISTINCT t.id) > 0 THEN 'covered' ELSE 'uncovered' END as coverage_status
                FROM requirements r
                LEFT JOIN test_case_requirements tcr ON r.id = tcr.requirement_id
                LEFT JOIN test_cases t ON tcr.test_case_id = t.id AND t.status = 'active'
                WHERE r.session_id = $1 AND r.status != 'deleted'
                GROUP BY r.id, r.original_content, r.edited_content, r.requirement_type
                ORDER BY r.created_at ASC
            ''', session_id)

            return {
                "session_id": session_id,
                "total_requirements": total_requirements,
                "covered_requirements": covered_requirements,
                "uncovered_requirements": total_requirements - covered_requirements,
                "coverage_percentage": round(coverage_percentage, 2),
                "coverage_details": [dict(row) for row in coverage_details]
            }

    # ===============================
    # LEGACY METHODS (for backward compatibility)
    # ===============================

    async def save_simple_workflow_result(self, session_id: str, user_id: str,
                                         project_name: str, user_prompt: str):
        """Save just the essential session info (legacy method)"""
        await self.create_session(session_id, user_id, project_name, user_prompt)

    async def extract_and_save_requirements(self, session_id: str, requirements_list: list):
        """Save requirements extracted from your agent (legacy method)"""
        await self.save_requirements(session_id, requirements_list)

    async def extract_and_save_test_cases(self, session_id: str, test_cases_list: list):
        """Save test cases and link to requirements (legacy method)"""
        await self.save_test_cases(session_id, test_cases_list)

    async def close(self):
        """Close database pool"""
        if self.pool:
            await self.pool.close()


# Global instance
db_manager = DatabaseManager()
