#!/usr/bin/env python3
"""Fix dataclass issues by adding default values to required fields."""

import os
import re
from pathlib import Path

def fix_dataclass_files():
    """Fix all dataclass files to have proper default values."""
    
    models_dir = Path("claude_code_builder/models")
    
    fixes = {
        # research.py fixes
        "research.py": [
            ('query: str', 'query: str = ""'),
            ('task_type: ResearchTaskType', 'task_type: ResearchTaskType = ResearchTaskType.DOCUMENTATION'),
            ('agent_id: str', 'agent_id: str = ""'),
            ('status: ResearchStatus', 'status: ResearchStatus = ResearchStatus.PENDING'),
            ('task_id: str', 'task_id: str = ""'),
            ('findings: List[ResearchFinding]', 'findings: List[ResearchFinding] = field(default_factory=list)'),
        ],
        
        # monitoring.py fixes
        "monitoring.py": [
            ('metric_name: str', 'metric_name: str = ""'),
            ('value: float', 'value: float = 0.0'),
            ('alert_type: AlertType', 'alert_type: AlertType = AlertType.INFO'),
            ('message: str', 'message: str = ""'),
            ('event_type: str', 'event_type: str = ""'),
            ('data: Dict[str, Any]', 'data: Dict[str, Any] = field(default_factory=dict)'),
            ('component: str', 'component: str = ""'),
            ('error_message: str', 'error_message: str = ""'),
            ('category: PerformanceCategory', 'category: PerformanceCategory = PerformanceCategory.EXECUTION'),
        ],
        
        # project.py fixes
        "project.py": [
            ('name: str', 'name: str = ""'),
            ('description: str', 'description: str = ""'),
            ('feature_type: str', 'feature_type: str = ""'),
            ('technology_type: str', 'technology_type: str = ""'),
            ('version: str', 'version: str = ""'),
            ('method: str', 'method: str = ""'),
            ('path: str', 'path: str = ""'),
            ('language: str', 'language: str = ""'),
            ('framework: str', 'framework: str = ""'),
        ],
        
        # testing.py fixes
        "testing.py": [
            ('test_id: str', 'test_id: str = ""'),
            ('test_name: str', 'test_name: str = ""'),
            ('test_type: TestType', 'test_type: TestType = TestType.UNIT'),
            ('status: TestStatus', 'status: TestStatus = TestStatus.PENDING'),
            ('execution_time: float', 'execution_time: float = 0.0'),
            ('cpu_usage: float', 'cpu_usage: float = 0.0'),
            ('memory_usage: float', 'memory_usage: float = 0.0'),
            ('stage: TestStage', 'stage: TestStage = TestStage.SETUP'),
            ('result: TestResult', 'result: TestResult = field(default_factory=lambda: TestResult())'),
        ]
    }
    
    for filename, replacements in fixes.items():
        file_path = models_dir / filename
        if file_path.exists():
            print(f"Fixing {file_path}")
            
            content = file_path.read_text()
            
            for old, new in replacements:
                if old in content and new not in content:
                    content = content.replace(old, new)
                    print(f"  Replaced: {old} -> {new}")
            
            file_path.write_text(content)
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    fix_dataclass_files()
    print("Dataclass fixes completed!")