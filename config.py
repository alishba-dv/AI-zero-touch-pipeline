import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    JIRA_URL: str = os.environ["JIRA_URL"]
    JIRA_EMAIL: str = os.environ["JIRA_EMAIL"]
    JIRA_API_TOKEN: str = os.environ["JIRA_API_TOKEN"]

    PROJECT_KEY: str = os.environ.get("PROJECT_KEY", "PROJ")
    BUILD_TOOL: str = os.environ.get("BUILD_TOOL", "maven")
    BUILD_MODULE: str = os.environ.get("BUILD_MODULE", ".")
    SRC_DIR: str = os.environ.get("SRC_DIR", "src/main/java")
    TEST_DIR: str = os.environ.get("TEST_DIR", "src/test/java")
    BASE_PACKAGE: str = os.environ.get("BASE_PACKAGE", "com.example.app")
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    WORKSPACE_DIR: str = os.path.join(os.getcwd(), "workspace")

    # GitHub
    GITHUB_TOKEN: str = os.environ["GITHUB_TOKEN"]
    GITHUB_USERNAME: str = os.environ["GITHUB_USERNAME"]
    GITHUB_REPO: str = os.environ.get("GITHUB_REPO", "AI-zero-touch-pipeline")

    # Maximum fix-and-retry cycles before giving up
    MAX_FIX_RETRIES: int = 3

    # Claude model used for code generation and analysis
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
