"""
MCP Server management for Claude Code Manager.
"""

import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import Config
from .models import MCPServer


class MCPManager:
    """Manages MCP (Model Context Protocol) servers."""

    def __init__(self, config: Config):
        self.config = config
        self.mcp_config_file = config.claude_dir / ".mcp.json"
        self._servers: Optional[List[MCPServer]] = None

    def get_servers(self, force_refresh: bool = False) -> List[MCPServer]:
        """Get all configured MCP servers."""
        if self._servers is not None and not force_refresh:
            return self._servers

        servers = []

        # Load from local .mcp.json
        if self.mcp_config_file.exists():
            try:
                with open(self.mcp_config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    mcp_servers = data.get('mcpServers', {})
                    for name, server_data in mcp_servers.items():
                        servers.append(MCPServer.from_dict(name, server_data))
            except (json.JSONDecodeError, IOError):
                pass

        self._servers = servers
        return servers

    def _save_servers(self, servers: List[MCPServer]) -> None:
        """Save servers to config file."""
        mcp_servers = {}
        for server in servers:
            mcp_servers[server.name] = server.to_dict()

        with open(self.mcp_config_file, 'w', encoding='utf-8') as f:
            json.dump({'mcpServers': mcp_servers}, f, indent=2)

        self._servers = servers

    def add_server(self, server: MCPServer) -> bool:
        """Add a new MCP server."""
        servers = self.get_servers()

        # Check for duplicate name
        if any(s.name == server.name for s in servers):
            return False

        servers.append(server)
        self._save_servers(servers)
        return True

    def update_server(self, name: str, updated_server: MCPServer) -> bool:
        """Update an existing server."""
        servers = self.get_servers()

        for i, server in enumerate(servers):
            if server.name == name:
                servers[i] = updated_server
                self._save_servers(servers)
                return True

        return False

    def delete_server(self, name: str) -> bool:
        """Delete a server."""
        servers = self.get_servers()
        original_count = len(servers)
        servers = [s for s in servers if s.name != name]

        if len(servers) < original_count:
            self._save_servers(servers)
            return True

        return False

    def get_server(self, name: str) -> Optional[MCPServer]:
        """Get server by name."""
        servers = self.get_servers()
        for server in servers:
            if server.name == name:
                return server
        return None

    def test_server_connection(self, server: MCPServer) -> Dict[str, Any]:
        """Test connection to an MCP server."""
        result = {
            'success': False,
            'message': '',
            'details': {}
        }

        try:
            # Try to run the server command with a timeout
            cmd = [server.command] + server.args

            # Add environment variables
            env = None
            if server.env:
                import os
                env = os.environ.copy()
                env.update(server.env)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                shell=True
            )

            try:
                stdout, stderr = process.communicate(timeout=5)

                # If process exits quickly without error, consider it valid
                if process.returncode == 0 or 'listening' in stdout.lower():
                    result['success'] = True
                    result['message'] = 'Server started successfully'
                else:
                    result['message'] = f'Server exited with code {process.returncode}'
                    result['details']['stderr'] = stderr[:500]

            except subprocess.TimeoutExpired:
                # Server is still running, which is good for MCP servers
                process.terminate()
                result['success'] = True
                result['message'] = 'Server is running'

        except FileNotFoundError:
            result['message'] = f'Command not found: {server.command}'
        except Exception as e:
            result['message'] = f'Error: {str(e)}'

        return result

    def import_from_claude_desktop(self) -> List[MCPServer]:
        """Import MCP servers from Claude Desktop configuration."""
        imported = []

        try:
            desktop_config = self.config.get_claude_desktop_mcp_config()
            mcp_servers = desktop_config.get('mcpServers', {})

            for name, server_data in mcp_servers.items():
                server = MCPServer.from_dict(name, server_data)
                if self.add_server(server):
                    imported.append(server)

        except Exception:
            pass

        return imported

    def get_available_mcp_templates(self) -> List[Dict[str, Any]]:
        """Get list of available MCP server templates."""
        return [
            {
                'name': 'filesystem',
                'description': 'File system access server',
                'command': 'npx',
                'args': ['-y', '@modelcontextprotocol/server-filesystem', '/path/to/directory']
            },
            {
                'name': 'git',
                'description': 'Git repository server',
                'command': 'uvx',
                'args': ['mcp-server-git', '--repository', '/path/to/repo']
            },
            {
                'name': 'sqlite',
                'description': 'SQLite database server',
                'command': 'uvx',
                'args': ['mcp-server-sqlite', '--db-path', '/path/to/db.sqlite']
            },
            {
                'name': 'postgres',
                'description': 'PostgreSQL database server',
                'command': 'npx',
                'args': ['-y', '@modelcontextprotocol/server-postgres', 'postgresql://user:pass@host/db']
            },
            {
                'name': 'brave-search',
                'description': 'Brave Search API server',
                'command': 'npx',
                'args': ['-y', '@modelcontextprotocol/server-brave-search'],
                'env': {'BRAVE_API_KEY': 'your-api-key'}
            },
            {
                'name': 'github',
                'description': 'GitHub API server',
                'command': 'npx',
                'args': ['-y', '@modelcontextprotocol/server-github'],
                'env': {'GITHUB_PERSONAL_ACCESS_TOKEN': 'your-token'}
            },
            {
                'name': 'slack',
                'description': 'Slack API server',
                'command': 'npx',
                'args': ['-y', '@modelcontextprotocol/server-slack'],
                'env': {'SLACK_BOT_TOKEN': 'your-token'}
            },
            {
                'name': 'memory',
                'description': 'Persistent memory server',
                'command': 'npx',
                'args': ['-y', '@modelcontextprotocol/server-memory']
            },
            {
                'name': 'puppeteer',
                'description': 'Browser automation server',
                'command': 'npx',
                'args': ['-y', '@modelcontextprotocol/server-puppeteer']
            },
            {
                'name': 'fetch',
                'description': 'HTTP fetch server',
                'command': 'uvx',
                'args': ['mcp-server-fetch']
            }
        ]

    def discover_plugin_mcp_servers(self) -> List[Dict[str, Any]]:
        """Discover MCP servers from installed plugins."""
        discovered = []

        plugins_dir = self.config.plugins_dir / "marketplaces"
        if plugins_dir.exists():
            for mcp_file in plugins_dir.rglob('.mcp.json'):
                try:
                    with open(mcp_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        plugin_name = mcp_file.parent.name
                        discovered.append({
                            'plugin': plugin_name,
                            'path': str(mcp_file),
                            'config': data
                        })
                except (json.JSONDecodeError, IOError):
                    continue

        return discovered
