"""
Data models for Claude Code Manager.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class Session:
    """Represents a Claude Code session."""
    session_id: str
    full_path: str
    first_prompt: str
    summary: str
    message_count: int
    created: datetime
    modified: datetime
    git_branch: Optional[str] = None
    project_path: Optional[str] = None
    is_sidechain: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create Session from dictionary."""
        return cls(
            session_id=data.get('sessionId', ''),
            full_path=data.get('fullPath', ''),
            first_prompt=data.get('firstPrompt', 'No prompt'),
            summary=data.get('summary', ''),
            message_count=data.get('messageCount', 0),
            created=datetime.fromisoformat(data.get('created', '').replace('Z', '+00:00')) if data.get('created') else datetime.now(timezone.utc),
            modified=datetime.fromisoformat(data.get('modified', '').replace('Z', '+00:00')) if data.get('modified') else datetime.now(timezone.utc),
            git_branch=data.get('gitBranch'),
            project_path=data.get('projectPath'),
            is_sidechain=data.get('isSidechain', False)
        )


@dataclass
class Project:
    """Represents a Claude Code project."""
    name: str
    path: Path
    original_path: str
    sessions: List[Session] = field(default_factory=list)

    def load_sessions(self) -> None:
        """Load sessions from sessions-index.json."""
        index_file = self.path / "sessions-index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.original_path = data.get('originalPath', self.original_path)
                    self.sessions = [
                        Session.from_dict(entry)
                        for entry in data.get('entries', [])
                    ]
            except (json.JSONDecodeError, IOError):
                pass


@dataclass
class Message:
    """Represents a message in a session."""
    uuid: str
    role: str
    content: str
    timestamp: datetime
    type: str
    parent_uuid: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['Message']:
        """Create Message from dictionary."""
        if data.get('type') not in ['user', 'assistant']:
            return None

        message_data = data.get('message', {})
        return cls(
            uuid=data.get('uuid', ''),
            role=message_data.get('role', ''),
            content=message_data.get('content', '') if isinstance(message_data.get('content'), str) else str(message_data.get('content', '')),
            timestamp=datetime.fromisoformat(data.get('timestamp', '').replace('Z', '+00:00')) if data.get('timestamp') else datetime.now(timezone.utc),
            type=data.get('type', ''),
            parent_uuid=data.get('parentUuid')
        )


@dataclass
class Agent:
    """Represents a custom Claude Code agent."""
    name: str
    description: str
    system_prompt: str
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 1.0
    created: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    run_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'system_prompt': self.system_prompt,
            'model': self.model,
            'temperature': self.temperature,
            'created': self.created.isoformat(),
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'run_count': self.run_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Agent':
        """Create Agent from dictionary."""
        return cls(
            name=data.get('name', ''),
            description=data.get('description', ''),
            system_prompt=data.get('system_prompt', ''),
            model=data.get('model', 'claude-sonnet-4-20250514'),
            temperature=data.get('temperature', 1.0),
            created=datetime.fromisoformat(data.get('created', datetime.now().isoformat())),
            last_used=datetime.fromisoformat(data['last_used']) if data.get('last_used') else None,
            run_count=data.get('run_count', 0)
        )


@dataclass
class AgentRun:
    """Represents an agent execution run."""
    run_id: str
    agent_name: str
    prompt: str
    response: str
    started: datetime
    completed: Optional[datetime] = None
    status: str = "running"  # running, completed, failed
    tokens_used: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'run_id': self.run_id,
            'agent_name': self.agent_name,
            'prompt': self.prompt,
            'response': self.response,
            'started': self.started.isoformat(),
            'completed': self.completed.isoformat() if self.completed else None,
            'status': self.status,
            'tokens_used': self.tokens_used,
            'error': self.error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentRun':
        """Create AgentRun from dictionary."""
        return cls(
            run_id=data.get('run_id', ''),
            agent_name=data.get('agent_name', ''),
            prompt=data.get('prompt', ''),
            response=data.get('response', ''),
            started=datetime.fromisoformat(data.get('started', datetime.now().isoformat())),
            completed=datetime.fromisoformat(data['completed']) if data.get('completed') else None,
            status=data.get('status', 'running'),
            tokens_used=data.get('tokens_used', 0),
            error=data.get('error')
        )


@dataclass
class MCPServer:
    """Represents an MCP server configuration."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'command': self.command,
            'args': self.args
        }
        if self.env:
            result['env'] = self.env
        return result

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'MCPServer':
        """Create MCPServer from dictionary."""
        return cls(
            name=name,
            command=data.get('command', ''),
            args=data.get('args', []),
            env=data.get('env', {}),
            enabled=data.get('enabled', True)
        )


@dataclass
class Checkpoint:
    """Represents a session checkpoint."""
    checkpoint_id: str
    session_id: str
    name: str
    description: str
    timestamp: datetime
    message_uuid: str
    parent_checkpoint_id: Optional[str] = None
    branch_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'checkpoint_id': self.checkpoint_id,
            'session_id': self.session_id,
            'name': self.name,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'message_uuid': self.message_uuid,
            'parent_checkpoint_id': self.parent_checkpoint_id,
            'branch_name': self.branch_name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """Create Checkpoint from dictionary."""
        return cls(
            checkpoint_id=data.get('checkpoint_id', ''),
            session_id=data.get('session_id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            message_uuid=data.get('message_uuid', ''),
            parent_checkpoint_id=data.get('parent_checkpoint_id'),
            branch_name=data.get('branch_name')
        )


@dataclass
class DailyActivity:
    """Represents daily activity statistics."""
    date: str
    message_count: int = 0
    session_count: int = 0
    tool_call_count: int = 0


@dataclass
class ModelUsage:
    """Represents model usage statistics."""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    web_search_requests: int = 0
    cost_usd: float = 0.0
