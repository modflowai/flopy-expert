"""
Checkpoint Manager for V02 Pipeline
Handles saving and resuming pipeline state for long-running processes
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib

logger = logging.getLogger(__name__)

class CheckpointManager:
    """Manages checkpoints for resumable pipeline processing"""
    
    def __init__(self, checkpoint_dir: Path, pipeline_name: str, stage: str):
        """
        Initialize checkpoint manager
        
        Args:
            checkpoint_dir: Directory to store checkpoints
            pipeline_name: Name of the pipeline (e.g., 'flopy_v02', 'pyemu_v02')
            stage: Current stage (e.g., 'analysis_generation', 'embedding_creation')
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True, parents=True)
        self.pipeline_name = pipeline_name
        self.stage = stage
        self.checkpoint_file = self.checkpoint_dir / f"{pipeline_name}_{stage}_checkpoint.json"
        self.backup_file = self.checkpoint_dir / f"{pipeline_name}_{stage}_checkpoint.backup.json"
        self.state = self._load_checkpoint()
    
    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load existing checkpoint or create new one"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    state = json.load(f)
                    logger.info(f"Loaded checkpoint: {len(state.get('completed_items', []))} items completed")
                    return state
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupted checkpoint file, trying backup: {e}")
                if self.backup_file.exists():
                    with open(self.backup_file, 'r') as f:
                        state = json.load(f)
                        logger.info(f"Loaded backup checkpoint: {len(state.get('completed_items', []))} items completed")
                        return state
        
        # Create new checkpoint
        return {
            "pipeline_name": self.pipeline_name,
            "stage": self.stage,
            "started_at": datetime.now().isoformat(),
            "completed_items": [],
            "failed_items": [],
            "metadata": {},
            "statistics": {
                "total_processed": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0
            }
        }
    
    def save_checkpoint(self):
        """Save current state to checkpoint file"""
        # Backup existing checkpoint
        if self.checkpoint_file.exists():
            import shutil
            shutil.copy2(self.checkpoint_file, self.backup_file)
        
        # Save new checkpoint
        self.state["last_updated"] = datetime.now().isoformat()
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
        
        logger.debug(f"Checkpoint saved: {self.state['statistics']}")
    
    def is_completed(self, item_id: str) -> bool:
        """Check if an item has already been processed"""
        return item_id in self.state["completed_items"]
    
    def is_failed(self, item_id: str) -> bool:
        """Check if an item previously failed"""
        return any(f['id'] == item_id for f in self.state.get("failed_items", []))
    
    def mark_completed(self, item_id: str, metadata: Optional[Dict] = None):
        """Mark an item as successfully completed"""
        if item_id not in self.state["completed_items"]:
            self.state["completed_items"].append(item_id)
            self.state["statistics"]["successful"] += 1
            self.state["statistics"]["total_processed"] += 1
            
            if metadata:
                self.state["metadata"][item_id] = metadata
            
            # Auto-save every N items (configurable)
            if len(self.state["completed_items"]) % 5 == 0:
                self.save_checkpoint()
    
    def mark_failed(self, item_id: str, error: str, can_retry: bool = True):
        """Mark an item as failed"""
        failure_record = {
            "id": item_id,
            "error": str(error),
            "timestamp": datetime.now().isoformat(),
            "can_retry": can_retry
        }
        
        # Remove from failed list if already there (for retry tracking)
        self.state["failed_items"] = [
            f for f in self.state.get("failed_items", []) 
            if f["id"] != item_id
        ]
        
        self.state["failed_items"].append(failure_record)
        self.state["statistics"]["failed"] += 1
        self.state["statistics"]["total_processed"] += 1
        
        self.save_checkpoint()
    
    def mark_skipped(self, item_id: str, reason: str = "Already processed"):
        """Mark an item as skipped"""
        self.state["statistics"]["skipped"] += 1
        logger.debug(f"Skipped {item_id}: {reason}")
    
    def get_pending_items(self, all_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter items to only those that haven't been completed
        
        Args:
            all_items: List of all items to process
            
        Returns:
            List of items that still need processing
        """
        completed_ids = set(self.state["completed_items"])
        pending = []
        
        for item in all_items:
            # Assume items have an 'id' field
            item_id = item.get('id') or item.get('file') or self._generate_item_id(item)
            if item_id not in completed_ids:
                pending.append(item)
        
        logger.info(f"Items: {len(all_items)} total, {len(completed_ids)} completed, {len(pending)} pending")
        return pending
    
    def _generate_item_id(self, item: Dict) -> str:
        """Generate a unique ID for an item if it doesn't have one"""
        # Create ID from item content
        content = json.dumps(item, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        return self.state["statistics"].copy()
    
    def reset(self):
        """Reset checkpoint (use with caution!)"""
        if self.checkpoint_file.exists():
            # Backup before reset
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_file = self.checkpoint_dir / f"{self.pipeline_name}_{self.stage}_checkpoint_{timestamp}.json"
            import shutil
            shutil.move(self.checkpoint_file, archive_file)
            logger.info(f"Checkpoint reset. Previous checkpoint archived to: {archive_file}")
        
        self.state = self._load_checkpoint()  # Creates new empty state
    
    def should_process(self, item_id: str, retry_failed: bool = False) -> bool:
        """
        Determine if an item should be processed
        
        Args:
            item_id: ID of the item
            retry_failed: Whether to retry previously failed items
            
        Returns:
            True if item should be processed
        """
        if self.is_completed(item_id):
            return False
        
        if self.is_failed(item_id) and not retry_failed:
            return False
        
        return True
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the checkpoint state"""
        stats = self.state["statistics"]
        failed_count = len(self.state.get("failed_items", []))
        
        summary = [
            f"Pipeline: {self.pipeline_name}",
            f"Stage: {self.stage}",
            f"Started: {self.state.get('started_at', 'Unknown')}",
            f"Last Updated: {self.state.get('last_updated', 'Never')}",
            "",
            "Statistics:",
            f"  Total Processed: {stats['total_processed']}",
            f"  Successful: {stats['successful']}",
            f"  Failed: {stats['failed']} ({failed_count} unique items)",
            f"  Skipped: {stats['skipped']}"
        ]
        
        if failed_count > 0:
            summary.append("")
            summary.append("Recent Failures:")
            for failure in self.state["failed_items"][-5:]:  # Show last 5 failures
                summary.append(f"  - {failure['id']}: {failure['error'][:50]}...")
        
        return "\n".join(summary)