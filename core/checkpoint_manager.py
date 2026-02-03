"""
Checkpoint management for Claude Code Manager.
"""

import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import difflib

from .config import Config
from .models import Checkpoint, Message


class CheckpointManager:
    """Manages session checkpoints and timeline."""

    def __init__(self, config: Config):
        self.config = config
        self.checkpoints_dir = config.claude_dir / "claude-code-manager-py" / "checkpoints"
        self.checkpoints_file = self.checkpoints_dir / "index.json"
        self._checkpoints: Optional[List[Checkpoint]] = None

    def _ensure_dir_exists(self) -> None:
        """Ensure checkpoints directory exists."""
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        if not self.checkpoints_file.exists():
            self._save_checkpoints([])

    def get_checkpoints(self, session_id: Optional[str] = None, force_refresh: bool = False) -> List[Checkpoint]:
        """Get all checkpoints, optionally filtered by session."""
        if self._checkpoints is None or force_refresh:
            self._ensure_dir_exists()
            try:
                with open(self.checkpoints_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._checkpoints = [Checkpoint.from_dict(c) for c in data]
            except (json.JSONDecodeError, IOError):
                self._checkpoints = []

        if session_id:
            return [c for c in self._checkpoints if c.session_id == session_id]
        return self._checkpoints

    def _save_checkpoints(self, checkpoints: List[Checkpoint]) -> None:
        """Save checkpoints to file."""
        self._ensure_dir_exists()
        with open(self.checkpoints_file, 'w', encoding='utf-8') as f:
            json.dump([c.to_dict() for c in checkpoints], f, indent=2)
        self._checkpoints = checkpoints

    def create_checkpoint(
        self,
        session_id: str,
        session_path: str,
        message_uuid: str,
        name: str,
        description: str = "",
        parent_checkpoint_id: Optional[str] = None,
        branch_name: Optional[str] = None
    ) -> Checkpoint:
        """Create a new checkpoint."""
        checkpoint = Checkpoint(
            checkpoint_id=str(uuid.uuid4()),
            session_id=session_id,
            name=name,
            description=description,
            timestamp=datetime.now(),
            message_uuid=message_uuid,
            parent_checkpoint_id=parent_checkpoint_id,
            branch_name=branch_name
        )

        # Store the session state at this checkpoint
        checkpoint_data_dir = self.checkpoints_dir / checkpoint.checkpoint_id
        checkpoint_data_dir.mkdir(parents=True, exist_ok=True)

        # Copy session file up to the checkpoint message
        session_file = Path(session_path)
        if session_file.exists():
            messages_up_to_checkpoint = []
            with open(session_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        messages_up_to_checkpoint.append(data)
                        if data.get('uuid') == message_uuid:
                            break
                    except json.JSONDecodeError:
                        continue

            # Save checkpoint session data
            with open(checkpoint_data_dir / "session.jsonl", 'w', encoding='utf-8') as f:
                for msg in messages_up_to_checkpoint:
                    f.write(json.dumps(msg) + '\n')

        # Add to index
        checkpoints = self.get_checkpoints()
        checkpoints.append(checkpoint)
        self._save_checkpoints(checkpoints)

        return checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get checkpoint by ID."""
        checkpoints = self.get_checkpoints()
        for cp in checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                return cp
        return None

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        checkpoints = self.get_checkpoints()

        # Find and remove checkpoint
        checkpoint = None
        for cp in checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                checkpoint = cp
                break

        if not checkpoint:
            return False

        # Remove checkpoint data
        checkpoint_data_dir = self.checkpoints_dir / checkpoint_id
        if checkpoint_data_dir.exists():
            shutil.rmtree(checkpoint_data_dir)

        # Update children to point to parent
        for cp in checkpoints:
            if cp.parent_checkpoint_id == checkpoint_id:
                cp.parent_checkpoint_id = checkpoint.parent_checkpoint_id

        # Remove from index
        checkpoints = [c for c in checkpoints if c.checkpoint_id != checkpoint_id]
        self._save_checkpoints(checkpoints)

        return True

    def restore_checkpoint(self, checkpoint_id: str, session_path: str) -> bool:
        """Restore session to a checkpoint state."""
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return False

        checkpoint_data_dir = self.checkpoints_dir / checkpoint_id
        checkpoint_session = checkpoint_data_dir / "session.jsonl"

        if not checkpoint_session.exists():
            return False

        # Backup current session
        session_file = Path(session_path)
        if session_file.exists():
            backup_path = session_file.with_suffix('.jsonl.backup')
            shutil.copy2(session_file, backup_path)

        # Restore from checkpoint
        shutil.copy2(checkpoint_session, session_file)

        return True

    def fork_session(
        self,
        checkpoint_id: str,
        new_session_id: str,
        project_path: Path,
        branch_name: str = "fork"
    ) -> Optional[str]:
        """Create a new session from a checkpoint."""
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return None

        checkpoint_data_dir = self.checkpoints_dir / checkpoint_id
        checkpoint_session = checkpoint_data_dir / "session.jsonl"

        if not checkpoint_session.exists():
            return None

        # Create new session file
        new_session_path = project_path / f"{new_session_id}.jsonl"

        # Copy checkpoint data and update session ID
        with open(checkpoint_session, 'r', encoding='utf-8') as src:
            with open(new_session_path, 'w', encoding='utf-8') as dst:
                for line in src:
                    try:
                        data = json.loads(line.strip())
                        data['sessionId'] = new_session_id
                        dst.write(json.dumps(data) + '\n')
                    except json.JSONDecodeError:
                        continue

        # Create checkpoint for the fork
        self.create_checkpoint(
            session_id=new_session_id,
            session_path=str(new_session_path),
            message_uuid=checkpoint.message_uuid,
            name=f"Fork from {checkpoint.name}",
            description=f"Forked from checkpoint: {checkpoint.name}",
            parent_checkpoint_id=checkpoint_id,
            branch_name=branch_name
        )

        return str(new_session_path)

    def get_checkpoint_messages(self, checkpoint_id: str) -> List[Dict[str, Any]]:
        """Get messages from a checkpoint."""
        checkpoint_data_dir = self.checkpoints_dir / checkpoint_id
        checkpoint_session = checkpoint_data_dir / "session.jsonl"

        messages = []
        if checkpoint_session.exists():
            with open(checkpoint_session, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get('type') in ['user', 'assistant']:
                            messages.append(data)
                    except json.JSONDecodeError:
                        continue

        return messages

    def get_diff_between_checkpoints(self, checkpoint_id_1: str, checkpoint_id_2: str) -> List[str]:
        """Get diff between two checkpoints."""
        messages1 = self.get_checkpoint_messages(checkpoint_id_1)
        messages2 = self.get_checkpoint_messages(checkpoint_id_2)

        # Extract content for comparison
        content1 = []
        for msg in messages1:
            message = msg.get('message', {})
            role = message.get('role', '')
            text = message.get('content', '')
            if isinstance(text, str):
                content1.append(f"[{role}]: {text[:200]}...")

        content2 = []
        for msg in messages2:
            message = msg.get('message', {})
            role = message.get('role', '')
            text = message.get('content', '')
            if isinstance(text, str):
                content2.append(f"[{role}]: {text[:200]}...")

        # Generate diff
        diff = list(difflib.unified_diff(
            content1, content2,
            fromfile=f"Checkpoint {checkpoint_id_1[:8]}",
            tofile=f"Checkpoint {checkpoint_id_2[:8]}",
            lineterm=""
        ))

        return diff

    def get_timeline(self, session_id: str) -> Dict[str, Any]:
        """Get checkpoint timeline for a session."""
        checkpoints = self.get_checkpoints(session_id)

        # Build tree structure
        root_checkpoints = [c for c in checkpoints if c.parent_checkpoint_id is None]

        def build_tree(cp: Checkpoint) -> Dict[str, Any]:
            children = [c for c in checkpoints if c.parent_checkpoint_id == cp.checkpoint_id]
            return {
                'checkpoint': cp.to_dict(),
                'children': [build_tree(child) for child in children]
            }

        return {
            'session_id': session_id,
            'total_checkpoints': len(checkpoints),
            'branches': [c.branch_name for c in checkpoints if c.branch_name],
            'tree': [build_tree(cp) for cp in root_checkpoints]
        }
