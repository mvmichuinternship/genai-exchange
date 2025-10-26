from pydantic import BaseModel
from typing import Literal

class ADOConfig(BaseModel):
    organization: str
    project: str
    personal_access_token: str
    base_url: str = "https://dev.azure.com"

class JiraConfig(BaseModel):
    base_url: str  # e.g., "https://yourcompany.atlassian.net"
    email: str
    api_token: str
    project_key: str  # e.g., "HEALTH"

class MCPConfig(BaseModel):
    alm_type: Literal["azure_devops", "jira"]
    ado_config: ADOConfig | None = None
    jira_config: JiraConfig | None = None
