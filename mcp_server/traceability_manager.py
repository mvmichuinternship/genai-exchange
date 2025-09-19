"""
Traceability Manager Module
Maintains traceability matrix between user stories and test cases
"""

import json
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class TraceabilityEntry:
    user_story_id: int
    test_case_ids: List[int]
    status: str  # "active", "archived", "deprecated"
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]

@dataclass
class TestCaseInfo:
    test_case_id: int
    title: str
    status: str
    created_date: str
    linked_user_stories: List[int]
    generation_method: str  # "manual", "agent_generated", "imported"
    last_updated: str

class TraceabilityManager:
    def __init__(self):
        self.traceability_map: Dict[int, TraceabilityEntry] = {}
        self.test_case_registry: Dict[int, TestCaseInfo] = {}
        self.persistence_file = "traceability_matrix.json"
        self.is_initialized = False
    
    async def initialize(self, persistence_file: str = "traceability_matrix.json"):
        """Initialize traceability manager and load existing data"""
        self.persistence_file = persistence_file
        
        try:
            # Load existing traceability data
            await self._load_from_file()
            self.is_initialized = True
            logger.info(f"Traceability manager initialized with {len(self.traceability_map)} entries")
            
            return {
                "success": True,
                "loaded_entries": len(self.traceability_map),
                "loaded_test_cases": len(self.test_case_registry),
                "persistence_file": self.persistence_file
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize traceability manager: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def add_traceability_entry(self, user_story_id: int, test_case_ids: List[int], 
                                   metadata: Dict[str, Any] = None) -> Dict:
        """Add or update traceability entry"""
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            
            # Check if entry exists
            if user_story_id in self.traceability_map:
                # Update existing entry
                entry = self.traceability_map[user_story_id]
                
                # Merge test case IDs (avoid duplicates)
                existing_ids = set(entry.test_case_ids)
                new_ids = set(test_case_ids)
                merged_ids = list(existing_ids.union(new_ids))
                
                entry.test_case_ids = merged_ids
                entry.updated_at = current_time
                
                if metadata:
                    entry.metadata.update(metadata)
                
                action = "updated"
            else:
                # Create new entry
                entry = TraceabilityEntry(
                    user_story_id=user_story_id,
                    test_case_ids=test_case_ids,
                    status="active",
                    created_at=current_time,
                    updated_at=current_time,
                    metadata=metadata or {}
                )
                self.traceability_map[user_story_id] = entry
                action = "created"
            
            # Update test case registry
            for tc_id in test_case_ids:
                await self._update_test_case_registry(tc_id, user_story_id)
            
            # Persist changes
            await self._save_to_file()
            
            return {
                "success": True,
                "user_story_id": user_story_id,
                "test_case_ids": entry.test_case_ids,
                "action": action,
                "total_test_cases": len(entry.test_case_ids),
                "updated_at": current_time
            }
            
        except Exception as e:
            logger.error(f"Failed to add traceability entry: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id
            }
    
    async def get_traceability_map(self, user_story_id: int = None) -> Dict:
        """Get traceability map for specific user story or all entries"""
        try:
            if user_story_id is not None:
                # Get specific entry
                if user_story_id in self.traceability_map:
                    entry = self.traceability_map[user_story_id]
                    return {
                        "success": True,
                        "user_story_id": user_story_id,
                        "traceability_entry": asdict(entry),
                        "test_case_count": len(entry.test_case_ids)
                    }
                else:
                    return {
                        "success": True,
                        "user_story_id": user_story_id,
                        "traceability_entry": None,
                        "message": "No traceability entry found"
                    }
            else:
                # Get all entries
                all_entries = {}
                for story_id, entry in self.traceability_map.items():
                    all_entries[story_id] = asdict(entry)
                
                return {
                    "success": True,
                    "total_entries": len(all_entries),
                    "traceability_map": all_entries,
                    "summary": self._generate_summary()
                }
                
        except Exception as e:
            logger.error(f"Failed to get traceability map: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def register_test_case(self, test_case_id: int, title: str, status: str, 
                               linked_user_stories: List[int], generation_method: str = "unknown") -> Dict:
        """Register a test case in the registry"""
        try:
            current_time = datetime.now(timezone.utc).isoformat()
            
            test_case_info = TestCaseInfo(
                test_case_id=test_case_id,
                title=title,
                status=status,
                created_date=current_time,
                linked_user_stories=linked_user_stories,
                generation_method=generation_method,
                last_updated=current_time
            )
            
            self.test_case_registry[test_case_id] = test_case_info
            
            # Update traceability entries
            for story_id in linked_user_stories:
                await self.add_traceability_entry(story_id, [test_case_id], {
                    "test_case_title": title,
                    "generation_method": generation_method
                })
            
            # Persist changes
            await self._save_to_file()
            
            return {
                "success": True,
                "test_case_id": test_case_id,
                "title": title,
                "linked_user_stories": linked_user_stories,
                "generation_method": generation_method
            }
            
        except Exception as e:
            logger.error(f"Failed to register test case: {e}")
            return {
                "success": False,
                "error": str(e),
                "test_case_id": test_case_id
            }
    
    async def remove_traceability_link(self, user_story_id: int, test_case_id: int) -> Dict:
        """Remove a specific test case from user story traceability"""
        try:
            if user_story_id not in self.traceability_map:
                return {
                    "success": False,
                    "error": f"No traceability entry found for user story {user_story_id}"
                }
            
            entry = self.traceability_map[user_story_id]
            
            if test_case_id in entry.test_case_ids:
                entry.test_case_ids.remove(test_case_id)
                entry.updated_at = datetime.now(timezone.utc).isoformat()
                
                # If no test cases left, mark as deprecated
                if not entry.test_case_ids:
                    entry.status = "deprecated"
                
                # Update test case registry
                if test_case_id in self.test_case_registry:
                    tc_info = self.test_case_registry[test_case_id]
                    if user_story_id in tc_info.linked_user_stories:
                        tc_info.linked_user_stories.remove(user_story_id)
                        tc_info.last_updated = datetime.now(timezone.utc).isoformat()
                
                # Persist changes
                await self._save_to_file()
                
                return {
                    "success": True,
                    "user_story_id": user_story_id,
                    "test_case_id": test_case_id,
                    "remaining_test_cases": len(entry.test_case_ids),
                    "status": entry.status
                }
            else:
                return {
                    "success": False,
                    "error": f"Test case {test_case_id} not linked to user story {user_story_id}"
                }
                
        except Exception as e:
            logger.error(f"Failed to remove traceability link: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_test_cases_for_story(self, user_story_id: int) -> Dict:
        """Get all test cases linked to a specific user story"""
        try:
            if user_story_id not in self.traceability_map:
                return {
                    "success": True,
                    "user_story_id": user_story_id,
                    "test_cases": [],
                    "total_count": 0,
                    "message": "No test cases found for this user story"
                }
            
            entry = self.traceability_map[user_story_id]
            test_cases = []
            
            for tc_id in entry.test_case_ids:
                if tc_id in self.test_case_registry:
                    tc_info = self.test_case_registry[tc_id]
                    test_cases.append({
                        "test_case_id": tc_id,
                        "title": tc_info.title,
                        "status": tc_info.status,
                        "generation_method": tc_info.generation_method,
                        "created_date": tc_info.created_date,
                        "last_updated": tc_info.last_updated
                    })
                else:
                    # Test case not in registry, add minimal info
                    test_cases.append({
                        "test_case_id": tc_id,
                        "title": "Unknown",
                        "status": "unknown",
                        "generation_method": "unknown",
                        "note": "Not found in test case registry"
                    })
            
            return {
                "success": True,
                "user_story_id": user_story_id,
                "test_cases": test_cases,
                "total_count": len(test_cases),
                "traceability_status": entry.status,
                "last_updated": entry.updated_at
            }
            
        except Exception as e:
            logger.error(f"Failed to get test cases for story: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id
            }
    
    async def get_user_stories_for_test_case(self, test_case_id: int) -> Dict:
        """Get all user stories linked to a specific test case"""
        try:
            if test_case_id not in self.test_case_registry:
                return {
                    "success": True,
                    "test_case_id": test_case_id,
                    "user_stories": [],
                    "total_count": 0,
                    "message": "Test case not found in registry"
                }
            
            tc_info = self.test_case_registry[test_case_id]
            user_stories = []
            
            for story_id in tc_info.linked_user_stories:
                if story_id in self.traceability_map:
                    entry = self.traceability_map[story_id]
                    user_stories.append({
                        "user_story_id": story_id,
                        "status": entry.status,
                        "total_test_cases": len(entry.test_case_ids),
                        "last_updated": entry.updated_at
                    })
            
            return {
                "success": True,
                "test_case_id": test_case_id,
                "test_case_title": tc_info.title,
                "user_stories": user_stories,
                "total_count": len(user_stories),
                "generation_method": tc_info.generation_method
            }
            
        except Exception as e:
            logger.error(f"Failed to get user stories for test case: {e}")
            return {
                "success": False,
                "error": str(e),
                "test_case_id": test_case_id
            }
    
    async def generate_traceability_report(self, format_type: str = "summary") -> Dict:
        """Generate comprehensive traceability report"""
        try:
            if format_type == "summary":
                return await self._generate_summary_report()
            elif format_type == "detailed":
                return await self._generate_detailed_report()
            elif format_type == "matrix":
                return await self._generate_matrix_report()
            else:
                raise ValueError(f"Unsupported format type: {format_type}")
                
        except Exception as e:
            logger.error(f"Failed to generate traceability report: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_summary_report(self) -> Dict:
        """Generate summary traceability report"""
        total_user_stories = len(self.traceability_map)
        total_test_cases = len(self.test_case_registry)
        
        # Count by status
        status_counts = {"active": 0, "archived": 0, "deprecated": 0}
        for entry in self.traceability_map.values():
            status_counts[entry.status] = status_counts.get(entry.status, 0) + 1
        
        # Count by generation method
        generation_counts = {}
        for tc_info in self.test_case_registry.values():
            method = tc_info.generation_method
            generation_counts[method] = generation_counts.get(method, 0) + 1
        
        # Coverage analysis
        coverage_stats = {
            "stories_with_tests": len([e for e in self.traceability_map.values() if e.test_case_ids]),
            "stories_without_tests": len([e for e in self.traceability_map.values() if not e.test_case_ids]),
            "avg_tests_per_story": sum(len(e.test_case_ids) for e in self.traceability_map.values()) / max(total_user_stories, 1)
        }
        
        return {
            "success": True,
            "report_type": "summary",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "totals": {
                "user_stories": total_user_stories,
                "test_cases": total_test_cases
            },
            "status_breakdown": status_counts,
            "generation_breakdown": generation_counts,
            "coverage_statistics": coverage_stats
        }
    
    async def _generate_detailed_report(self) -> Dict:
        """Generate detailed traceability report"""
        detailed_entries = []
        
        for story_id, entry in self.traceability_map.items():
            test_case_details = []
            for tc_id in entry.test_case_ids:
                if tc_id in self.test_case_registry:
                    tc_info = self.test_case_registry[tc_id]
                    test_case_details.append({
                        "id": tc_id,
                        "title": tc_info.title,
                        "status": tc_info.status,
                        "generation_method": tc_info.generation_method
                    })
                else:
                    test_case_details.append({
                        "id": tc_id,
                        "title": "Unknown",
                        "status": "unknown",
                        "note": "Not in registry"
                    })
            
            detailed_entries.append({
                "user_story_id": story_id,
                "status": entry.status,
                "test_case_count": len(entry.test_case_ids),
                "test_cases": test_case_details,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
                "metadata": entry.metadata
            })
        
        return {
            "success": True,
            "report_type": "detailed",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entries": detailed_entries,
            "total_entries": len(detailed_entries)
        }
    
    async def _generate_matrix_report(self) -> Dict:
        """Generate matrix-style traceability report"""
        matrix_data = []
        
        for story_id, entry in self.traceability_map.items():
            matrix_data.append({
                "User_Story_ID": story_id,
                "Test_Case_IDs": entry.test_case_ids,
                "Test_Case_Count": len(entry.test_case_ids),
                "Status": entry.status,
                "Last_Updated": entry.updated_at
            })
        
        return {
            "success": True,
            "report_type": "matrix",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "matrix": matrix_data,
            "headers": ["User_Story_ID", "Test_Case_IDs", "Test_Case_Count", "Status", "Last_Updated"]
        }
    
    def _generate_summary(self) -> Dict:
        """Generate quick summary statistics"""
        return {
            "total_user_stories": len(self.traceability_map),
            "total_test_cases": len(self.test_case_registry),
            "active_entries": len([e for e in self.traceability_map.values() if e.status == "active"]),
            "deprecated_entries": len([e for e in self.traceability_map.values() if e.status == "deprecated"])
        }
    
    async def _update_test_case_registry(self, test_case_id: int, user_story_id: int):
        """Update test case registry with user story link"""
        if test_case_id in self.test_case_registry:
            tc_info = self.test_case_registry[test_case_id]
            if user_story_id not in tc_info.linked_user_stories:
                tc_info.linked_user_stories.append(user_story_id)
                tc_info.last_updated = datetime.now(timezone.utc).isoformat()
        else:
            # Create placeholder entry if test case not registered yet
            tc_info = TestCaseInfo(
                test_case_id=test_case_id,
                title="Pending Registration",
                status="unknown",
                created_date=datetime.now(timezone.utc).isoformat(),
                linked_user_stories=[user_story_id],
                generation_method="unknown",
                last_updated=datetime.now(timezone.utc).isoformat()
            )
            self.test_case_registry[test_case_id] = tc_info
    
    async def _load_from_file(self):
        """Load traceability data from persistence file"""
        if not Path(self.persistence_file).exists():
            logger.info("No existing traceability file found, starting fresh")
            return
        
        try:
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)
            
            # Load traceability map
            for story_id_str, entry_data in data.get('traceability_map', {}).items():
                story_id = int(story_id_str)
                entry = TraceabilityEntry(**entry_data)
                self.traceability_map[story_id] = entry
            
            # Load test case registry
            for tc_id_str, tc_data in data.get('test_case_registry', {}).items():
                tc_id = int(tc_id_str)
                tc_info = TestCaseInfo(**tc_data)
                self.test_case_registry[tc_id] = tc_info
            
            logger.info(f"Loaded {len(self.traceability_map)} traceability entries and {len(self.test_case_registry)} test cases")
            
        except Exception as e:
            logger.error(f"Failed to load traceability data: {e}")
            # Continue with empty data rather than failing
    
    async def _save_to_file(self):
        """Save traceability data to persistence file"""
        try:
            data = {
                'traceability_map': {
                    str(k): asdict(v) for k, v in self.traceability_map.items()
                },
                'test_case_registry': {
                    str(k): asdict(v) for k, v in self.test_case_registry.items()
                },
                'last_saved': datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Traceability data saved to {self.persistence_file}")
            
        except Exception as e:
            logger.error(f"Failed to save traceability data: {e}")
            # Don't raise exception, just log error