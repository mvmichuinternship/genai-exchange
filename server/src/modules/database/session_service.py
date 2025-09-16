from .database_manager import db_manager
from typing import List, Dict, Any

class SessionService:
    @staticmethod
    async def get_user_sessions(user_id: str) -> List[dict]:
        """Get all sessions for a user"""
        async with db_manager.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT
                    s.*,
                    COUNT(r.id) as requirements_count,
                    COUNT(tc.id) as test_cases_count
                FROM sessions s
                LEFT JOIN requirements r ON s.session_id = r.session_id AND r.status = 'active'
                LEFT JOIN test_cases tc ON s.session_id = tc.session_id AND tc.status = 'active'
                WHERE s.user_id = $1
                GROUP BY s.session_id
                ORDER BY s.created_at DESC
            ''', user_id)
            return [dict(row) for row in rows]

    @staticmethod
    async def get_session_summary(session_id: str) -> dict:
        """Get session with counts and status"""
        session = await db_manager.get_session(session_id)
        if not session:
            return {}

        async with db_manager.pool.acquire() as conn:
            # Get detailed counts
            summary = await conn.fetchrow('''
                SELECT
                    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'active') as requirements_count,
                    COUNT(DISTINCT r.id) FILTER (WHERE r.edited_content IS NOT NULL) as edited_requirements_count,
                    COUNT(DISTINCT tc.id) FILTER (WHERE tc.status = 'active') as test_cases_count,
                    COUNT(DISTINCT tcr.id) as requirement_test_links_count
                FROM sessions s
                LEFT JOIN requirements r ON s.session_id = r.session_id
                LEFT JOIN test_cases tc ON s.session_id = tc.session_id
                LEFT JOIN test_case_requirements tcr ON tc.id = tcr.test_case_id
                WHERE s.session_id = $1
            ''', session_id)

        return {
            **session,
            "requirements_count": summary['requirements_count'] or 0,
            "edited_requirements_count": summary['edited_requirements_count'] or 0,
            "test_cases_count": summary['test_cases_count'] or 0,
            "requirement_test_links_count": summary['requirement_test_links_count'] or 0
        }
