"""
CLAUDE.md file management for Claude Code Manager.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import Config


class ClaudeMdManager:
    """Manages CLAUDE.md files across projects."""

    CLAUDE_MD_NAMES = ['CLAUDE.md', 'claude.md', '.claude.md', 'CLAUDE.local.md']

    def __init__(self, config: Config):
        self.config = config
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    def find_claude_md_files(self, root_path: Optional[Path] = None, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Find all CLAUDE.md files in a directory tree."""
        if root_path is None:
            # Search in home directory and common project locations
            search_paths = [
                Path.home(),
                Path.home() / "projects",
                Path.home() / "code",
                Path.home() / "github",
                Path.home() / "repos",
            ]
            # Add Windows-specific paths
            if os.name == 'nt':
                search_paths.extend([
                    Path("D:/github-repos-personal"),
                    Path("D:/projects"),
                    Path("C:/Users") / os.environ.get('USERNAME', '') / "Documents",
                ])
        else:
            search_paths = [root_path]

        results = []

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for claude_file in self._find_files(search_path, max_depth):
                results.append(claude_file)

        # Remove duplicates based on path
        seen = set()
        unique_results = []
        for r in results:
            if r['path'] not in seen:
                seen.add(r['path'])
                unique_results.append(r)

        return sorted(unique_results, key=lambda x: x['modified'], reverse=True)

    def _find_files(self, root: Path, max_depth: int, current_depth: int = 0) -> List[Dict[str, Any]]:
        """Recursively find CLAUDE.md files."""
        results = []

        if current_depth > max_depth:
            return results

        try:
            for item in root.iterdir():
                if item.is_file() and item.name in self.CLAUDE_MD_NAMES:
                    stat = item.stat()
                    results.append({
                        'path': str(item),
                        'name': item.name,
                        'project': item.parent.name,
                        'project_path': str(item.parent),
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'is_local': '.local' in item.name
                    })
                elif item.is_dir() and not item.name.startswith('.') and item.name not in ['node_modules', 'venv', '.git', '__pycache__', 'dist', 'build']:
                    results.extend(self._find_files(item, max_depth, current_depth + 1))
        except PermissionError:
            pass

        return results

    def read_claude_md(self, file_path: str) -> Optional[str]:
        """Read content of a CLAUDE.md file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except IOError:
            return None

    def write_claude_md(self, file_path: str, content: str) -> bool:
        """Write content to a CLAUDE.md file."""
        try:
            # Create backup
            path = Path(file_path)
            if path.exists():
                backup_path = path.with_suffix('.md.backup')
                with open(path, 'r', encoding='utf-8') as f:
                    original = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except IOError:
            return False

    def create_claude_md(self, project_path: str, content: str = "", local: bool = False) -> Optional[str]:
        """Create a new CLAUDE.md file in a project."""
        filename = 'CLAUDE.local.md' if local else 'CLAUDE.md'
        file_path = Path(project_path) / filename

        if file_path.exists():
            return None  # Already exists

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content or self.get_template())
            return str(file_path)
        except IOError:
            return None

    def delete_claude_md(self, file_path: str) -> bool:
        """Delete a CLAUDE.md file (moves to backup)."""
        try:
            path = Path(file_path)
            if path.exists():
                backup_path = path.with_suffix('.md.deleted')
                path.rename(backup_path)
                return True
        except IOError:
            pass
        return False

    def get_template(self, template_name: str = "default") -> str:
        """Get a CLAUDE.md template."""
        templates = {
            "default": """# Project Guidelines

## Overview
Brief description of the project and its purpose.

## Tech Stack
- Language/Framework:
- Database:
- Key Libraries:

## Architecture
Describe the overall architecture and structure.

## Code Style
- Follow existing code style conventions
- Use meaningful variable and function names
- Add comments for complex logic

## Important Notes
- List any critical information Claude should know
- Mention any gotchas or edge cases

## Common Tasks
Describe how to perform common operations.
""",
            "python": """# Python Project Guidelines

## Overview
Brief description of the project.

## Setup
```bash
pip install -r requirements.txt
```

## Tech Stack
- Python 3.x
- Framework:
- Database:

## Code Style
- Follow PEP 8 guidelines
- Use type hints
- Document functions with docstrings

## Testing
```bash
pytest tests/
```

## Important Notes
- Virtual environment recommended
- Check .env.example for required environment variables
""",
            "javascript": """# JavaScript/Node.js Project Guidelines

## Overview
Brief description of the project.

## Setup
```bash
npm install
```

## Tech Stack
- Node.js
- Framework:
- Database:

## Code Style
- Use ESLint configuration
- Prefer async/await over callbacks
- Use TypeScript types where available

## Scripts
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests

## Important Notes
- Check .env.example for required environment variables
""",
            "react": """# React Project Guidelines

## Overview
Brief description of the application.

## Setup
```bash
npm install
npm run dev
```

## Tech Stack
- React 18+
- Build tool: Vite/Next.js
- State management:
- Styling:

## Component Structure
- Use functional components with hooks
- Place components in src/components
- Use named exports

## Code Style
- Follow React best practices
- Use custom hooks for reusable logic
- Prefer composition over inheritance

## Important Notes
- Components should be small and focused
- Use React.memo for performance when needed
""",
            "minimal": """# Project Guidelines

Key information for Claude to know about this project.
"""
        }
        return templates.get(template_name, templates["default"])

    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get list of available templates."""
        return [
            {"name": "default", "description": "General purpose template"},
            {"name": "python", "description": "Python project template"},
            {"name": "javascript", "description": "JavaScript/Node.js template"},
            {"name": "react", "description": "React application template"},
            {"name": "minimal", "description": "Minimal template"}
        ]

    def analyze_claude_md(self, content: str) -> Dict[str, Any]:
        """Analyze a CLAUDE.md file content."""
        lines = content.split('\n')

        analysis = {
            'total_lines': len(lines),
            'word_count': len(content.split()),
            'sections': [],
            'has_code_blocks': '```' in content,
            'has_links': 'http' in content.lower() or '[' in content,
            'headings': []
        }

        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                heading = line.lstrip('#').strip()
                analysis['headings'].append({
                    'level': level,
                    'text': heading
                })
                if level == 2:
                    analysis['sections'].append(heading)

        return analysis

    def merge_claude_md_files(self, file_paths: List[str]) -> str:
        """Merge multiple CLAUDE.md files into one."""
        merged_content = []

        for path in file_paths:
            content = self.read_claude_md(path)
            if content:
                project_name = Path(path).parent.name
                merged_content.append(f"# From: {project_name}\n\n{content}\n\n---\n")

        return '\n'.join(merged_content)

    def search_in_claude_md(self, query: str, files: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Search for text in CLAUDE.md files."""
        if files is None:
            files = self.find_claude_md_files()

        results = []
        query_lower = query.lower()

        for file_info in files:
            content = self.read_claude_md(file_info['path'])
            if content and query_lower in content.lower():
                # Find matching lines
                matches = []
                for i, line in enumerate(content.split('\n'), 1):
                    if query_lower in line.lower():
                        matches.append({
                            'line_number': i,
                            'content': line.strip()[:200]
                        })

                results.append({
                    **file_info,
                    'matches': matches[:5]  # Limit to 5 matches per file
                })

        return results
