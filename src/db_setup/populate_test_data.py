# populate_test_data.py
import asyncio
import asyncpg
import uuid
import json
from datetime import datetime, timedelta
import random

class TestDataPopulator:
    def __init__(self, database_url):
        self.database_url = database_url
        self.pool = None

    async def initialize(self):
        self.pool = await asyncpg.create_pool(self.database_url)

    async def populate_all_data(self):
        """Populate all tables with comprehensive test data"""
        await self.populate_users()
        await self.populate_projects()
        await self.populate_sessions()
        await self.populate_requirements()
        await self.populate_test_cases()
        await self.populate_test_case_requirements()

        print("✅ All test data populated successfully!")

    async def populate_users(self):
        """Create test users"""
        users_data = [
            ("alice_johnson", "alice.johnson@testgen.com", "Alice Johnson", "lead_tester"),
            ("bob_smith", "bob.smith@testgen.com", "Bob Smith", "tester"),
            ("carol_white", "carol.white@testgen.com", "Carol White", "test_manager"),
            ("david_brown", "david.brown@testgen.com", "David Brown", "developer"),
            ("emma_davis", "emma.davis@testgen.com", "Emma Davis", "qa_analyst"),
            ("frank_miller", "frank.miller@testgen.com", "Frank Miller", "tester"),
            ("grace_wilson", "grace.wilson@testgen.com", "Grace Wilson", "automation_engineer"),
            ("henry_taylor", "henry.taylor@testgen.com", "Henry Taylor", "security_tester")
        ]

        async with self.pool.acquire() as conn:
            for username, email, full_name, role in users_data:
                user_id = f"user_{username}"
                await conn.execute('''
                    INSERT INTO users (user_id, username, email, full_name, role, last_login)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id) DO NOTHING
                ''', user_id, username, email, full_name, role,
                datetime.now() - timedelta(days=random.randint(1, 30)))

        print("✅ Users populated")

    async def populate_projects(self):
        """Create test projects"""
        projects_data = [
            ("E-Commerce Authentication System", "Complete user authentication and authorization for online shopping platform"),
            ("Mobile Banking Security Module", "Security features for mobile banking application including biometric auth"),
            ("Healthcare Patient Portal", "Patient management and appointment system for healthcare providers"),
            ("Social Media Content Management", "Content creation and moderation system for social platform"),
            ("Enterprise CRM Integration", "Customer relationship management system with third-party integrations"),
            ("IoT Device Management Platform", "Device monitoring and control system for IoT deployments"),
            ("Real-time Analytics Dashboard", "Business intelligence dashboard with real-time data visualization"),
            ("Supply Chain Management System", "End-to-end supply chain tracking and management solution")
        ]

        async with self.pool.acquire() as conn:
            for i, (name, description) in enumerate(projects_data):
                project_id = f"proj_{i+1:03d}"
                owner_user_id = f"user_{['alice_johnson', 'carol_white', 'emma_davis'][i % 3]}"
                await conn.execute('''
                    INSERT INTO projects (project_id, project_name, description, owner_user_id)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (project_id) DO NOTHING
                ''', project_id, name, description, owner_user_id)

        print("✅ Projects populated")

    async def populate_sessions(self):
        """Create test sessions"""
        session_prompts = [
            "Analyze user authentication requirements for login system",
            "Generate test cases for password reset functionality",
            "Create security tests for two-factor authentication",
            "Test payment processing workflow for e-commerce",
            "Validate user registration and profile management",
            "Test API security and rate limiting features",
            "Analyze mobile app performance requirements",
            "Generate integration tests for third-party services",
            "Test data encryption and privacy compliance",
            "Validate user interface accessibility requirements",
            "Test microservices communication patterns",
            "Generate load testing scenarios for high traffic",
            "Test database backup and recovery procedures",
            "Validate real-time notification systems",
            "Test file upload and content management features"
        ]

        users = ["user_alice_johnson", "user_bob_smith", "user_carol_white",
                "user_david_brown", "user_emma_davis", "user_frank_miller",
                "user_grace_wilson", "user_henry_taylor"]

        projects = [f"proj_{i:03d}" for i in range(1, 9)]

        statuses = ["completed", "in_progress", "failed", "requirements_analyzed", "test_cases_generated"]

        async with self.pool.acquire() as conn:
            for i in range(50):  # Create 50 sessions
                session_id = f"session_{uuid.uuid4().hex[:12]}"
                user_id = random.choice(users)
                project_name = f"Project {random.choice(projects).split('_')[1]}"
                prompt = random.choice(session_prompts)
                status = random.choice(statuses)
                rag_enabled = random.choice([True, False])
                rag_context_loaded = 1 if rag_enabled and random.choice([True, False]) else 0
                agent_used = random.choice(["sequential_workflow", "requirement_analyzer", "test_case_generator"])

                created_at = datetime.now() - timedelta(days=random.randint(1, 90))

                await conn.execute('''
                    INSERT INTO sessions
                    (session_id, user_id, project_name, user_prompt, status,
                     rag_context_loaded, rag_enabled, agent_used, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ''', session_id, user_id, project_name, prompt, status,
                rag_context_loaded, rag_enabled, agent_used, created_at, created_at)

        print("✅ Sessions populated")

    async def populate_requirements(self):
        """Create test requirements"""
        requirement_templates = {
            'functional': [
                "System must authenticate users using email and password",
                "Application must support password reset via email",
                "Users must be able to update their profile information",
                "System must validate input data before processing",
                "Application must support file upload with size limits",
                "Users must receive email notifications for important events",
                "System must maintain session timeout for security",
                "Application must support multiple payment methods",
                "Users must be able to search and filter content",
                "System must generate audit logs for all transactions"
            ],
            'security': [
                "System must encrypt all sensitive data in transit and at rest",
                "Application must implement proper access control mechanisms",
                "System must prevent SQL injection and XSS attacks",
                "Application must enforce strong password policies",
                "System must implement rate limiting to prevent abuse",
                "Application must validate all user inputs",
                "System must support secure session management",
                "Application must implement proper error handling without information disclosure"
            ],
            'performance': [
                "System must respond to user requests within 2 seconds",
                "Application must support concurrent users without degradation",
                "System must handle peak loads of 10,000 requests per minute",
                "Application must have 99.9% uptime availability",
                "System must efficiently manage database connections",
                "Application must implement proper caching mechanisms"
            ],
            'rag_context': [
                "Retrieved context: User authentication patterns from industry standards",
                "Retrieved context: Security best practices for web applications",
                "Retrieved context: Performance benchmarks for similar systems",
                "Retrieved context: Compliance requirements for data protection",
                "Retrieved context: Integration patterns for third-party services"
            ]
        }

        async with self.pool.acquire() as conn:
            # Get all sessions
            sessions = await conn.fetch("SELECT session_id FROM sessions")

            for session in sessions:
                session_id = session['session_id']

                # Generate 3-8 requirements per session
                num_requirements = random.randint(3, 8)

                for i in range(num_requirements):
                    req_id = f"{session_id}_req_{i+1}"
                    req_type = random.choice(['functional', 'security', 'performance', 'rag_context'])
                    content = random.choice(requirement_templates[req_type])
                    priority = random.choice(['low', 'medium', 'high', 'critical'])

                    # Some requirements have edits
                    edited_content = None
                    if random.random() < 0.3:  # 30% chance of being edited
                        edited_content = f"EDITED: {content} with additional constraints"

                    source = 'rag_context' if req_type == 'rag_context' else random.choice(['agent_generated', 'user_created'])
                    tags = json.dumps(random.sample(['authentication', 'security', 'performance', 'ui', 'api', 'database'], k=random.randint(1, 3)))

                    await conn.execute('''
                        INSERT INTO requirements
                        (id, session_id, original_content, edited_content, requirement_type,
                         priority, source, tags, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ''', req_id, session_id, content, edited_content, req_type,
                    priority, source, tags, datetime.now() - timedelta(minutes=random.randint(1, 1440)))

        print("✅ Requirements populated")

    async def populate_test_cases(self):
        """Create test cases"""
        test_case_templates = [
            {
                'name': 'Valid User Login Test',
                'description': 'Test successful login with valid credentials',
                'steps': ['Navigate to login page', 'Enter valid email', 'Enter valid password', 'Click login button'],
                'expected': 'User should be redirected to dashboard',
                'type': 'functional',
                'preconditions': 'User account exists and is active'
            },
            {
                'name': 'Invalid Password Test',
                'description': 'Test login failure with incorrect password',
                'steps': ['Navigate to login page', 'Enter valid email', 'Enter invalid password', 'Click login button'],
                'expected': 'Error message should be displayed',
                'type': 'negative',
                'preconditions': 'User account exists'
            },
            {
                'name': 'Account Lockout Test',
                'description': 'Test account lockout after multiple failed attempts',
                'steps': ['Attempt login with wrong password 5 times', 'Verify account is locked', 'Wait for lockout period'],
                'expected': 'Account should be locked and unlock after specified time',
                'type': 'security',
                'preconditions': 'Account lockout policy is configured'
            },
            {
                'name': 'Password Reset Flow Test',
                'description': 'Test complete password reset workflow',
                'steps': ['Click forgot password', 'Enter email', 'Check email for reset link', 'Follow link and set new password'],
                'expected': 'User should be able to login with new password',
                'type': 'functional',
                'preconditions': 'Email service is configured'
            },
            {
                'name': 'Session Timeout Test',
                'description': 'Test automatic session timeout functionality',
                'steps': ['Login to application', 'Leave idle for configured timeout period', 'Attempt to access protected resource'],
                'expected': 'User should be redirected to login page',
                'type': 'security',
                'preconditions': 'Session timeout is configured'
            }
        ]

        async with self.pool.acquire() as conn:
            # Get all sessions
            sessions = await conn.fetch("SELECT session_id FROM sessions")

            for session in sessions:
                session_id = session['session_id']

                # Generate 2-6 test cases per session
                num_test_cases = random.randint(2, 6)

                for i in range(num_test_cases):
                    tc_id = f"{session_id}_tc_{i+1}"
                    template = random.choice(test_case_templates)

                    test_name = f"{template['name']} #{i+1}"
                    test_description = template['description']
                    test_steps = json.dumps(template['steps'])
                    expected_results = template['expected']
                    test_type = template['type']
                    preconditions = template['preconditions']
                    priority = random.choice(['low', 'medium', 'high', 'critical'])

                    test_data = json.dumps({
                        'test_email': 'test.user@example.com',
                        'valid_password': 'Test@123',
                        'invalid_password': 'wrong_password',
                        'timeout_minutes': 30
                    })

                    tags = json.dumps(random.sample(['login', 'security', 'validation', 'ui', 'api'], k=random.randint(1, 3)))

                    await conn.execute('''
                        INSERT INTO test_cases
                        (id, session_id, test_name, test_description, test_steps,
                         expected_results, test_type, priority, test_data,
                         preconditions, estimated_duration, tags, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ''', tc_id, session_id, test_name, test_description, test_steps,
                    expected_results, test_type, priority, test_data,
                    preconditions, random.randint(15, 120), tags,
                    datetime.now() - timedelta(minutes=random.randint(1, 1440)))

        print("✅ Test cases populated")

    async def populate_test_case_requirements(self):
        """Create test case to requirement mappings"""
        async with self.pool.acquire() as conn:
            # Get all sessions with their requirements and test cases
            sessions_data = await conn.fetch('''
                SELECT DISTINCT session_id FROM sessions
            ''')

            for session_data in sessions_data:
                session_id = session_data['session_id']

                # Get requirements and test cases for this session
                requirements = await conn.fetch('''
                    SELECT id FROM requirements WHERE session_id = $1 AND status = 'active'
                ''', session_id)

                test_cases = await conn.fetch('''
                    SELECT id FROM test_cases WHERE session_id = $1 AND status = 'active'
                ''', session_id)

                # Create mappings (each test case covers 1-3 requirements)
                for test_case in test_cases:
                    num_requirements = min(random.randint(1, 3), len(requirements))
                    selected_requirements = random.sample(requirements, num_requirements)

                    for requirement in selected_requirements:
                        coverage_type = random.choice(['direct', 'indirect', 'partial'])
                        confidence_score = random.uniform(0.7, 1.0)

                        await conn.execute('''
                            INSERT INTO test_case_requirements
                            (test_case_id, requirement_id, coverage_type, confidence_score)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (test_case_id, requirement_id) DO NOTHING
                        ''', test_case['id'], requirement['id'], coverage_type, confidence_score)

        print("✅ Test case requirements mappings populated")

    async def get_summary_stats(self):
        """Get summary statistics of populated data"""
        async with self.pool.acquire() as conn:
            stats = {}

            stats['users'] = await conn.fetchval("SELECT COUNT(*) FROM users")
            stats['projects'] = await conn.fetchval("SELECT COUNT(*) FROM projects")
            stats['sessions'] = await conn.fetchval("SELECT COUNT(*) FROM sessions")
            stats['requirements'] = await conn.fetchval("SELECT COUNT(*) FROM requirements")
            stats['test_cases'] = await conn.fetchval("SELECT COUNT(*) FROM test_cases")
            stats['mappings'] = await conn.fetchval("SELECT COUNT(*) FROM test_case_requirements")

            # Coverage statistics
            coverage_stats = await conn.fetchrow('''
                SELECT
                    COUNT(DISTINCT r.id) as total_requirements,
                    COUNT(DISTINCT tcr.requirement_id) as covered_requirements
                FROM requirements r
                LEFT JOIN test_case_requirements tcr ON r.id = tcr.requirement_id
                WHERE r.status = 'active'
            ''')

            if coverage_stats['total_requirements'] > 0:
                stats['coverage_percentage'] = round(
                    (coverage_stats['covered_requirements'] / coverage_stats['total_requirements']) * 100, 2
                )
            else:
                stats['coverage_percentage'] = 0

            return stats

    async def close(self):
        if self.pool:
            await self.pool.close()

# Main execution script
async def main():
    # Update with your database URL
    DATABASE_URL = "postgresql://testgen_user:testgen_pass@localhost:5432/testgen_db"

    populator = TestDataPopulator(DATABASE_URL)

    try:
        await populator.initialize()
        print("🚀 Starting data population...")

        await populator.populate_all_data()

        # Get and display summary
        stats = await populator.get_summary_stats()

        print("\n📊 DATA POPULATION SUMMARY:")
        print(f"👥 Users: {stats['users']}")
        print(f"📁 Projects: {stats['projects']}")
        print(f"🎯 Sessions: {stats['sessions']}")
        print(f"📋 Requirements: {stats['requirements']}")
        print(f"🧪 Test Cases: {stats['test_cases']}")
        print(f"🔗 Requirement-Test Mappings: {stats['mappings']}")
        print(f"📈 Requirements Coverage: {stats['coverage_percentage']}%")

        print("\n✅ Database population completed successfully!")

    except Exception as e:
        print(f"❌ Error during data population: {e}")
    finally:
        await populator.close()

if __name__ == "__main__":
    asyncio.run(main())
