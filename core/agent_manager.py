"""
Agent management for Claude Code Manager.
"""

import json
import uuid
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from .config import Config
from .models import Agent, AgentRun


class AgentManager:
    """Manages custom Claude Code agents."""

    def __init__(self, config: Config):
        self.config = config
        self.agents_file = config.claude_dir / "claude-code-manager-py" / "agents.json"
        self.runs_file = config.claude_dir / "claude-code-manager-py" / "agent_runs.json"
        self._agents: Optional[List[Agent]] = None
        self._runs: Optional[List[AgentRun]] = None
        self._running_processes: Dict[str, subprocess.Popen] = {}

    def _ensure_files_exist(self) -> None:
        """Ensure agent files exist."""
        self.agents_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.agents_file.exists():
            with open(self.agents_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
        if not self.runs_file.exists():
            with open(self.runs_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def get_agents(self, force_refresh: bool = False) -> List[Agent]:
        """Get all agents."""
        if self._agents is not None and not force_refresh:
            return self._agents

        self._ensure_files_exist()

        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._agents = [Agent.from_dict(a) for a in data]
        except (json.JSONDecodeError, IOError):
            self._agents = []

        return self._agents

    def _save_agents(self, agents: List[Agent]) -> None:
        """Save agents to file."""
        self.agents_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.agents_file, 'w', encoding='utf-8') as f:
            json.dump([a.to_dict() for a in agents], f, indent=2)
        self._agents = agents

    def create_agent(self, agent: Agent) -> bool:
        """Create a new agent."""
        agents = self.get_agents()

        # Check for duplicate name
        if any(a.name == agent.name for a in agents):
            return False

        agents.append(agent)
        self._save_agents(agents)
        return True

    def update_agent(self, name: str, updated_agent: Agent) -> bool:
        """Update an existing agent."""
        agents = self.get_agents()

        for i, agent in enumerate(agents):
            if agent.name == name:
                agents[i] = updated_agent
                self._save_agents(agents)
                return True

        return False

    def delete_agent(self, name: str) -> bool:
        """Delete an agent."""
        agents = self.get_agents()
        original_count = len(agents)
        agents = [a for a in agents if a.name != name]

        if len(agents) < original_count:
            self._save_agents(agents)
            return True

        return False

    def get_agent(self, name: str) -> Optional[Agent]:
        """Get agent by name."""
        agents = self.get_agents()
        for agent in agents:
            if agent.name == name:
                return agent
        return None

    def get_runs(self, force_refresh: bool = False) -> List[AgentRun]:
        """Get all agent runs."""
        if self._runs is not None and not force_refresh:
            return self._runs

        self._ensure_files_exist()

        try:
            with open(self.runs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._runs = [AgentRun.from_dict(r) for r in data]
        except (json.JSONDecodeError, IOError):
            self._runs = []

        return self._runs

    def _save_runs(self, runs: List[AgentRun]) -> None:
        """Save runs to file."""
        self.runs_file.parent.mkdir(parents=True, exist_ok=True)
        # Keep only last 100 runs
        runs = sorted(runs, key=lambda r: r.started, reverse=True)[:100]
        with open(self.runs_file, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in runs], f, indent=2)
        self._runs = runs

    def run_agent(
        self,
        agent: Agent,
        prompt: str,
        callback: Optional[Callable[[AgentRun], None]] = None,
        background: bool = False
    ) -> AgentRun:
        """Run an agent with a prompt."""
        run = AgentRun(
            run_id=str(uuid.uuid4()),
            agent_name=agent.name,
            prompt=prompt,
            response="",
            started=datetime.now(),
            status="running"
        )

        # Add to runs
        runs = self.get_runs()
        runs.append(run)
        self._save_runs(runs)

        # Update agent usage
        agent.run_count += 1
        agent.last_used = datetime.now()
        self.update_agent(agent.name, agent)

        if background:
            thread = threading.Thread(
                target=self._execute_agent,
                args=(agent, prompt, run, callback)
            )
            thread.daemon = True
            thread.start()
        else:
            self._execute_agent(agent, prompt, run, callback)

        return run

    def _execute_agent(
        self,
        agent: Agent,
        prompt: str,
        run: AgentRun,
        callback: Optional[Callable[[AgentRun], None]] = None
    ) -> None:
        """Execute agent in subprocess."""
        try:
            # Build claude command
            cmd = [
                "claude",
                "--model", agent.model,
                "--system-prompt", agent.system_prompt,
                "--print",
                prompt
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )

            self._running_processes[run.run_id] = process

            stdout, stderr = process.communicate()

            if process.returncode == 0:
                run.response = stdout
                run.status = "completed"
            else:
                run.response = stdout
                run.error = stderr
                run.status = "failed"

            run.completed = datetime.now()

        except Exception as e:
            run.error = str(e)
            run.status = "failed"
            run.completed = datetime.now()

        finally:
            if run.run_id in self._running_processes:
                del self._running_processes[run.run_id]

            # Update run in storage
            runs = self.get_runs(force_refresh=True)
            for i, r in enumerate(runs):
                if r.run_id == run.run_id:
                    runs[i] = run
                    break
            self._save_runs(runs)

            if callback:
                callback(run)

    def stop_run(self, run_id: str) -> bool:
        """Stop a running agent."""
        if run_id in self._running_processes:
            process = self._running_processes[run_id]
            process.terminate()
            return True
        return False

    def get_agent_stats(self, agent_name: str) -> Dict[str, Any]:
        """Get statistics for an agent."""
        runs = [r for r in self.get_runs() if r.agent_name == agent_name]

        if not runs:
            return {
                'total_runs': 0,
                'successful_runs': 0,
                'failed_runs': 0,
                'avg_duration': 0,
                'total_tokens': 0
            }

        successful = [r for r in runs if r.status == 'completed']
        failed = [r for r in runs if r.status == 'failed']

        durations = []
        for r in runs:
            if r.completed:
                duration = (r.completed - r.started).total_seconds()
                durations.append(duration)

        return {
            'total_runs': len(runs),
            'successful_runs': len(successful),
            'failed_runs': len(failed),
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'total_tokens': sum(r.tokens_used for r in runs)
        }

    def get_default_agents(self) -> List[Agent]:
        """Get list of default agent templates."""
        return [
            Agent(
                name="Code Reviewer",
                description="Reviews code for bugs, security issues, and best practices",
                system_prompt="""You are an expert code reviewer. Analyze the provided code for:
1. Bugs and potential errors
2. Security vulnerabilities
3. Performance issues
4. Code style and best practices
5. Suggestions for improvement

Provide clear, actionable feedback.""",
                model="claude-sonnet-4-20250514"
            ),
            Agent(
                name="Documentation Writer",
                description="Generates documentation for code and APIs",
                system_prompt="""You are a technical documentation expert. Generate clear, comprehensive documentation including:
1. Overview and purpose
2. Installation/setup instructions
3. API reference with examples
4. Usage examples
5. Troubleshooting guide

Use markdown formatting for clarity.""",
                model="claude-sonnet-4-20250514"
            ),
            Agent(
                name="Test Generator",
                description="Creates unit tests for provided code",
                system_prompt="""You are a testing expert. Generate comprehensive unit tests for the provided code:
1. Test all public methods/functions
2. Include edge cases and error conditions
3. Use appropriate testing framework
4. Add clear test descriptions
5. Aim for high code coverage

Follow testing best practices.""",
                model="claude-sonnet-4-20250514"
            ),
            Agent(
                name="Refactoring Assistant",
                description="Suggests code refactoring and improvements",
                system_prompt="""You are a software architect specializing in code refactoring. Analyze and improve code by:
1. Identifying code smells
2. Suggesting design pattern applications
3. Improving readability and maintainability
4. Reducing complexity
5. Enhancing modularity

Provide before/after examples.""",
                model="claude-sonnet-4-20250514"
            ),
            Agent(
                name="Bug Fixer",
                description="Analyzes and fixes bugs in code",
                system_prompt="""You are an expert debugger. When given code with bugs:
1. Identify the root cause
2. Explain why the bug occurs
3. Provide a fix with explanation
4. Suggest preventive measures
5. Test the fix mentally

Be thorough and precise.""",
                model="claude-sonnet-4-20250514"
            )
        ]
