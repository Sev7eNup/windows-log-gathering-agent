from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional
import yaml
from pathlib import Path


class CredentialConfig(BaseModel):
    username: str
    password: str
    domain: str


class ClientConfig(BaseModel):
    name: str
    hostname: str
    ip: str
    credentials: str
    log_paths: Dict[str, List[str]]
    powershell_commands: List[str]


class LLMConfig(BaseModel):
    endpoint: str
    model: str
    max_tokens: int = 4000
    temperature: float = 0.1
    system_prompt: str


class MachinesConfig(BaseModel):
    credentials: Dict[str, CredentialConfig]
    clients: List[ClientConfig]
    llm_config: LLMConfig


class Settings(BaseSettings):
    config_file: str = Field(default="src/loggatheringagent/config/machines.yaml")
    log_tail_lines: int = Field(default=2000)
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    debug: bool = Field(default=False)
    
    # MCP Server configurations
    powershell_mcp_port: int = Field(default=8001)
    smb_mcp_port: int = Field(default=8002)

    class Config:
        env_prefix = "LGA_"
        env_file = ".env"

    def load_machines_config(self) -> MachinesConfig:
        """Load machines configuration from YAML file."""
        config_path = Path(self.config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return MachinesConfig(**data)


# Global settings instance
settings = Settings()