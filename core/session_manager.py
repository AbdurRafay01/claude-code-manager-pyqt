"""
Session management for Claude Code Manager.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from .config import Config
from .models import Project, Session, Message


class SessionManager:
    """Manages Claude Code sessions and projects."""

    def __init__(self, config: Config):
        self.config = config
        self._projects_cache: Optional[List[Project]] = None

    def get_projects(self, force_refresh: bool = False) -> List[Project]:
        """Get all projects with their sessions."""
        if self._projects_cache is not None and not force_refresh:
            return self._projects_cache

        projects = []
        if self.config.projects_dir.exists():
            for item in self.config.projects_dir.iterdir():
                if item.is_dir():
                    # Parse project name from directory name
                    name = self._parse_project_name(item.name)
                    project = Project(
                        name=name,
                        path=item,
                        original_path=name
                    )
                    project.load_sessions()
                    projects.append(project)

        # Sort by most recent session
        projects.sort(
            key=lambda p: max(
                (s.modified for s in p.sessions),
                default=datetime.min.replace(tzinfo=timezone.utc)
            ),
            reverse=True
        )

        self._projects_cache = projects
        return projects

    def _parse_project_name(self, dir_name: str) -> str:
        """Parse project name from directory name."""
        # Convert encoded path back to readable format
        # e.g., "D--github-repos-personal-my-portfolio" -> "D:/github-repos-personal/my-portfolio"
        if dir_name.startswith('-'):
            # Unix-style path
            return '/' + dir_name[1:].replace('-', '/')
        elif len(dir_name) > 2 and dir_name[1:3] == '--':
            # Windows-style path (e.g., "D--")
            return dir_name[0] + ':/' + dir_name[3:].replace('-', '/')
        return dir_name.replace('-', '/')

    def get_session_messages(self, session_path: str) -> List[Message]:
        """Load messages from a session file."""
        messages = []
        path = Path(session_path)

        if not path.exists():
            return messages

        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        msg = Message.from_dict(data)
                        if msg:
                            messages.append(msg)
                    except json.JSONDecodeError:
                        continue
        except IOError:
            pass

        return messages

    def search_sessions(self, query: str) -> List[Dict[str, Any]]:
        """Search sessions by query."""
        results = []
        query_lower = query.lower()

        for project in self.get_projects():
            for session in project.sessions:
                # Search in summary, first prompt, and session ID
                if (query_lower in session.summary.lower() or
                    query_lower in session.first_prompt.lower() or
                    query_lower in session.session_id.lower() or
                    query_lower in project.name.lower()):
                    results.append({
                        'project': project,
                        'session': session,
                        'match_type': 'summary' if query_lower in session.summary.lower() else 'prompt'
                    })

        return results

    def get_session_stats(self, session: Session) -> Dict[str, Any]:
        """Get statistics for a session."""
        messages = self.get_session_messages(session.full_path)

        user_messages = [m for m in messages if m.role == 'user']
        assistant_messages = [m for m in messages if m.role == 'assistant']

        # Calculate duration
        if messages:
            start = min(m.timestamp for m in messages)
            end = max(m.timestamp for m in messages)
            duration = (end - start).total_seconds()
        else:
            duration = 0

        return {
            'total_messages': len(messages),
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'duration_seconds': duration,
            'avg_response_length': sum(len(m.content) for m in assistant_messages) / max(len(assistant_messages), 1)
        }

    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent sessions across all projects."""
        all_sessions = []

        for project in self.get_projects():
            for session in project.sessions:
                all_sessions.append({
                    'project': project,
                    'session': session
                })

        # Sort by modified date
        all_sessions.sort(key=lambda x: x['session'].modified, reverse=True)

        return all_sessions[:limit]

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Load command history."""
        history = []

        if self.config.history_file.exists():
            try:
                with open(self.config.history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            history.append(data)
                        except json.JSONDecodeError:
                            continue
            except IOError:
                pass

        # Sort by timestamp descending
        history.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return history[:limit]

    def clear_cache(self) -> None:
        """Clear the projects cache."""
        self._projects_cache = None
