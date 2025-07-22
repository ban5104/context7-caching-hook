# ~/projects/cc-rag/src/prediction/cache_warmer.py
import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import sys

# Add project components to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from analyzers.pattern_analyzer import OperationPatternAnalyzer

class PredictiveCacheWarmer:
    """Predictively warms the cache based on operation sequences and patterns."""
    
    def __init__(self, db_manager, pattern_analyzer: OperationPatternAnalyzer):
        self.db = db_manager
        self.pattern_analyzer = pattern_analyzer
        self.preload_queue = []
        self.preload_status = {}
    
    def predict_next_documentation(self, current_framework: str, current_operation: str) -> List[Dict]:
        """Predict what documentation should be preloaded based on current operation."""
        
        predictions = []
        
        # Get prediction from pattern analysis
        prediction = self.pattern_analyzer.get_prediction_for_operation(current_operation, current_framework)
        
        if prediction and prediction["confidence"] > 0.2:  # 20% minimum confidence
            predictions.append({
                "framework": current_framework,
                "operation": prediction["predicted_operation"],
                "confidence": prediction["confidence"],
                "priority": prediction["preload_priority"],
                "reason": "sequence_pattern",
                "cache_key": f"{current_framework}:{prediction['predicted_operation']}"
            })
        
        # Add framework-specific common next operations
        common_sequences = self._get_framework_common_sequences(current_framework)
        for seq in common_sequences.get(current_operation, []):
            if seq["confidence"] > 0.15:  # Lower threshold for common patterns
                predictions.append({
                    "framework": current_framework,
                    "operation": seq["next_operation"],
                    "confidence": seq["confidence"],
                    "priority": "medium",
                    "reason": "framework_pattern",
                    "cache_key": f"{current_framework}:{seq['next_operation']}"
                })
        
        # Sort by confidence and priority
        predictions.sort(key=lambda x: (
            1 if x["priority"] == "high" else 0.5 if x["priority"] == "medium" else 0.3,
            x["confidence"]
        ), reverse=True)
        
        return predictions[:3]  # Top 3 predictions
    
    def _get_framework_common_sequences(self, framework: str) -> Dict:
        """Get common operation sequences for a specific framework."""
        
        # This could be loaded from analysis or hardcoded common patterns
        common_patterns = {
            "react": {
                "create": [
                    {"next_operation": "style", "confidence": 0.4},
                    {"next_operation": "api", "confidence": 0.3}
                ],
                "style": [
                    {"next_operation": "test", "confidence": 0.25}
                ],
                "api": [
                    {"next_operation": "auth", "confidence": 0.3},
                    {"next_operation": "test", "confidence": 0.2}
                ]
            },
            "fastapi": {
                "create": [
                    {"next_operation": "api", "confidence": 0.5},
                    {"next_operation": "auth", "confidence": 0.3}
                ],
                "api": [
                    {"next_operation": "test", "confidence": 0.4}
                ]
            },
            "supabase": {
                "create": [
                    {"next_operation": "auth", "confidence": 0.4},
                    {"next_operation": "api", "confidence": 0.35}
                ],
                "auth": [
                    {"next_operation": "api", "confidence": 0.3}
                ]
            }
        }
        
        return common_patterns.get(framework, {})
    
    def should_preload(self, cache_key: str) -> bool:
        """Check if a cache key should be preloaded."""
        
        # Check if already cached
        cached_data = self.db.get_cache_data(cache_key)
        if cached_data:
            return False  # Already cached
        
        # Check if currently being preloaded
        if cache_key in self.preload_status:
            status = self.preload_status[cache_key]
            if status["status"] == "loading":
                return False  # Already being loaded
        
        return True
    
    def queue_preload(self, cache_key: str, priority: str = "medium", reason: str = "prediction") -> None:
        """Queue a cache key for preloading."""
        
        if not self.should_preload(cache_key):
            return
        
        preload_item = {
            "cache_key": cache_key,
            "framework": cache_key.split(':')[0],
            "operation": cache_key.split(':')[1] if ':' in cache_key else "general",
            "priority": priority,
            "reason": reason,
            "queued_at": datetime.now().isoformat()
        }
        
        # Insert based on priority
        if priority == "high":
            self.preload_queue.insert(0, preload_item)
        else:
            self.preload_queue.append(preload_item)
        
        # Mark as queued
        self.preload_status[cache_key] = {
            "status": "queued",
            "queued_at": datetime.now().isoformat()
        }
    
    def process_preload_queue(self, max_items: int = 3) -> Dict:
        """Process items in the preload queue."""
        
        processed = 0
        successful = 0
        errors = []
        
        while self.preload_queue and processed < max_items:
            item = self.preload_queue.pop(0)
            cache_key = item["cache_key"]
            
            try:
                # Mark as loading
                self.preload_status[cache_key] = {
                    "status": "loading",
                    "started_at": datetime.now().isoformat()
                }
                
                # Simulate preloading (in real implementation, this would call Context7 API)
                success = self._simulate_documentation_fetch(item)
                
                if success:
                    successful += 1
                    self.preload_status[cache_key] = {
                        "status": "completed",
                        "completed_at": datetime.now().isoformat()
                    }
                else:
                    errors.append(f"Failed to preload {cache_key}")
                    self.preload_status[cache_key] = {
                        "status": "error",
                        "error_at": datetime.now().isoformat()
                    }
                
                processed += 1
                
            except Exception as e:
                errors.append(f"Error preloading {cache_key}: {str(e)}")
                self.preload_status[cache_key] = {
                    "status": "error",
                    "error_at": datetime.now().isoformat(),
                    "error": str(e)
                }
                processed += 1
        
        return {
            "processed": processed,
            "successful": successful,
            "errors": errors,
            "queue_remaining": len(self.preload_queue)
        }
    
    def _simulate_documentation_fetch(self, item: Dict) -> bool:
        """
        Simulate fetching documentation for preloading.
        In real implementation, this would:
        1. Call Context7 API to get documentation
        2. Extract relevant sections
        3. Store in cache database
        """
        
        # For simulation, we'll create mock documentation data
        framework = item["framework"]
        operation = item["operation"]
        
        mock_sections = {
            "overview": f"Mock overview for {framework} {operation} operations",
            "example": f"Mock example code for {framework} {operation}",
            "usage": f"Mock usage instructions for {framework} {operation}",
            "api": f"Mock API reference for {framework} {operation}"
        }
        
        mock_content = f"Mock documentation content for {framework} {operation}"
        
        try:
            # Store in cache
            self.db.store_context(
                cache_key=item["cache_key"],
                framework=framework,
                content=mock_content,
                sections=mock_sections
            )
            return True
        except Exception:
            return False
    
    def get_preload_stats(self) -> Dict:
        """Get statistics about preloading activities."""
        
        status_counts = {}
        for status_info in self.preload_status.values():
            status = status_info["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "queue_length": len(self.preload_queue),
            "total_tracked": len(self.preload_status),
            "status_breakdown": status_counts,
            "queue_items": [
                {
                    "cache_key": item["cache_key"],
                    "priority": item["priority"],
                    "reason": item["reason"]
                }
                for item in self.preload_queue[:5]  # Top 5 items
            ]
        }
    
    def cleanup_old_status(self, hours_old: int = 24) -> int:
        """Clean up old preload status entries."""
        
        cutoff_time = datetime.now().timestamp() - (hours_old * 3600)
        cleaned = 0
        
        keys_to_remove = []
        for cache_key, status_info in self.preload_status.items():
            # Check various timestamp fields
            for time_field in ["queued_at", "started_at", "completed_at", "error_at"]:
                if time_field in status_info:
                    try:
                        entry_time = datetime.fromisoformat(status_info[time_field]).timestamp()
                        if entry_time < cutoff_time:
                            keys_to_remove.append(cache_key)
                            break
                    except (ValueError, KeyError):
                        keys_to_remove.append(cache_key)
                        break
        
        for key in keys_to_remove:
            del self.preload_status[key]
            cleaned += 1
        
        return cleaned
    
    def trigger_predictive_preload(self, current_framework: str, current_operation: str) -> Dict:
        """Trigger predictive preloading based on current operation."""
        
        predictions = self.predict_next_documentation(current_framework, current_operation)
        queued = 0
        
        for prediction in predictions:
            cache_key = prediction["cache_key"]
            if self.should_preload(cache_key):
                self.queue_preload(
                    cache_key=cache_key,
                    priority=prediction["priority"],
                    reason=f"predicted_{prediction['reason']}"
                )
                queued += 1
        
        # Process some items immediately
        process_result = self.process_preload_queue(max_items=2)
        
        return {
            "predictions_made": len(predictions),
            "items_queued": queued,
            "process_result": process_result,
            "predictions": predictions
        }