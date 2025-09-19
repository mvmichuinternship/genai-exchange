"""
Test Case Schema Validation Module
Enforces consistent schema for test case outputs across all ALM integrations
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError, validator
import logging

logger = logging.getLogger(__name__)

class TestStep(BaseModel):
    """Individual test step with action and expected result"""
    action: str = Field(..., min_length=1, description="Test action to perform")
    expected: str = Field(..., min_length=1, description="Expected result/outcome")
    
    @validator('action', 'expected')
    def validate_not_empty(cls, v):
        if not v or v.strip() == '':
            raise ValueError('Field cannot be empty or whitespace only')
        return v.strip()

class TestCase(BaseModel):
    """Complete test case with title, description, and steps"""
    title: str = Field(..., min_length=1, max_length=255, description="Test case title")
    description: str = Field(..., min_length=1, description="Test case description")
    steps: List[TestStep] = Field(..., min_items=1, description="List of test steps")
    priority: Optional[int] = Field(2, ge=1, le=4, description="Priority level (1-4)")
    
    @validator('title', 'description')
    def validate_not_empty(cls, v):
        if not v or v.strip() == '':
            raise ValueError('Field cannot be empty or whitespace only')
        return v.strip()
    
    @validator('steps')
    def validate_steps_not_empty(cls, v):
        if not v:
            raise ValueError('Test case must have at least one step')
        return v

class TestCaseBatch(BaseModel):
    """Batch of test cases for bulk operations"""
    test_cases: List[TestCase] = Field(..., min_items=1, description="List of test cases")
    user_story_id: int = Field(..., description="Related user story ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('test_cases')
    def validate_unique_titles(cls, v):
        titles = [tc.title for tc in v]
        if len(titles) != len(set(titles)):
            raise ValueError('Test case titles must be unique within a batch')
        return v

class ValidationResult(BaseModel):
    """Result of schema validation"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_data: Optional[Any] = None

class TestCaseValidator:
    """Handles test case schema validation with retry logic"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
    
    def validate_single_testcase(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate a single test case against schema"""
        try:
            validated_testcase = TestCase(**data)
            return ValidationResult(
                is_valid=True,
                validated_data=validated_testcase
            )
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error['loc'])
                message = error['msg']
                error_messages.append(f"Field '{field}': {message}")
            
            return ValidationResult(
                is_valid=False,
                errors=error_messages
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Unexpected validation error: {str(e)}"]
            )
    
    def validate_testcase_batch(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate a batch of test cases"""
        try:
            validated_batch = TestCaseBatch(**data)
            return ValidationResult(
                is_valid=True,
                validated_data=validated_batch
            )
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error['loc'])
                message = error['msg']
                error_messages.append(f"Field '{field}': {message}")
            
            return ValidationResult(
                is_valid=False,
                errors=error_messages
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Unexpected validation error: {str(e)}"]
            )
    
    async def validate_with_retry(self, data: Dict[str, Any], 
                                validation_type: str = "single") -> ValidationResult:
        """
        Validate with retry logic for agent generation workflows
        This is where the MCP would retry with the agent if validation fails
        """
        attempt = 0
        last_result = None
        
        while attempt < self.max_retries:
            attempt += 1
            
            if validation_type == "single":
                result = self.validate_single_testcase(data)
            elif validation_type == "batch":
                result = self.validate_testcase_batch(data)
            else:
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Unknown validation type: {validation_type}"]
                )
            
            if result.is_valid:
                logger.info(f"Test case validation successful on attempt {attempt}")
                return result
            
            last_result = result
            logger.warning(f"Test case validation failed on attempt {attempt}/{self.max_retries}")
            logger.warning(f"Validation errors: {result.errors}")
            
            # In a real implementation, this is where you would:
            # 1. Send validation errors back to the agent
            # 2. Request regeneration with specific feedback
            # 3. Wait for agent response
            # For now, we just log and continue
        
        logger.error(f"Test case validation failed after {self.max_retries} attempts")
        return last_result or ValidationResult(
            is_valid=False,
            errors=["Validation failed after maximum retries"]
        )
    
    def format_validation_errors(self, result: ValidationResult) -> str:
        """Format validation errors for user-friendly display"""
        if result.is_valid:
            return "Validation successful"
        
        error_text = "Test case validation failed:\n"
        for i, error in enumerate(result.errors, 1):
            error_text += f"{i}. {error}\n"
        
        if result.warnings:
            error_text += "\nWarnings:\n"
            for i, warning in enumerate(result.warnings, 1):
                error_text += f"{i}. {warning}\n"
        
        return error_text
    
    def get_schema_documentation(self) -> Dict[str, Any]:
        """Get schema documentation for agent reference"""
        return {
            "test_case_schema": {
                "title": "string (required, 1-255 chars)",
                "description": "string (required, min 1 char)", 
                "steps": "array (required, min 1 item)",
                "priority": "integer (optional, 1-4, default: 2)"
            },
            "test_step_schema": {
                "action": "string (required, min 1 char)",
                "expected": "string (required, min 1 char)"
            },
            "example": {
                "title": "Login with valid credentials",
                "description": "Verify that user can login with correct username and password",
                "steps": [
                    {
                        "action": "Navigate to login page",
                        "expected": "Login form is displayed"
                    },
                    {
                        "action": "Enter valid username and password",
                        "expected": "Credentials are accepted"
                    },
                    {
                        "action": "Click login button",
                        "expected": "User is redirected to dashboard"
                    }
                ],
                "priority": 2
            },
            "validation_rules": [
                "Title and description cannot be empty",
                "At least one test step is required", 
                "Test steps must have both action and expected fields",
                "Priority must be between 1 and 4",
                "All text fields are trimmed of whitespace"
            ]
        }

# Global validator instance
test_case_validator = TestCaseValidator()

def validate_testcase(data: Dict[str, Any]) -> ValidationResult:
    """Convenience function for single test case validation"""
    return test_case_validator.validate_single_testcase(data)

def validate_testcase_batch(data: Dict[str, Any]) -> ValidationResult:
    """Convenience function for batch validation"""
    return test_case_validator.validate_testcase_batch(data)

async def validate_with_retry(data: Dict[str, Any], validation_type: str = "single") -> ValidationResult:
    """Convenience function for validation with retry"""
    return await test_case_validator.validate_with_retry(data, validation_type)