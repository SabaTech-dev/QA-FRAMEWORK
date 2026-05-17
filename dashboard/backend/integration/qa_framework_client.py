"""
QA Framework Integration Client

This module provides integration between the dashboard and the existing QA-FRAMEWORK.
It allows the dashboard to execute tests defined in the QA-FRAMEWORK and retrieve results.
"""
import asyncio
import subprocess
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import tempfile
import json

# QA-FRAMEWORK path from environment or default for container
QA_FRAMEWORK_PATH = os.environ.get("QA_FRAMEWORK_PATH", "/app/QA-FRAMEWORK")

class QAFrameworkClient:
    """
    Client to integrate with the existing QA-FRAMEWORK
    """
    
    def __init__(self, framework_path: str = QA_FRAMEWORK_PATH):
        self.framework_path = Path(framework_path)
        if not self.framework_path.exists():
            raise FileNotFoundError(f"QA-FRAMEWORK not found at {self.framework_path}")
    
    async def execute_test_suite(self, suite_name: str, test_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a test suite from the QA-FRAMEWORK
        """
        # Create temporary test file with the test parameters
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            # Write a test execution script
            script_content = f"""
import sys
sys.path.insert(0, '{self.framework_path}')

# Import the QA-FRAMEWORK test execution module
from src.core.use_cases.test_runner import TestRunner
from src.adapters.http.httpx_client import HttpxClient
from src.adapters.ui.playwright_page import PlaywrightPage

def run_test_suite():
    runner = TestRunner()
    # Execute the specified test suite with parameters
    result = runner.execute_suite('{suite_name}', params={test_params or {}})
    return result

if __name__ == '__main__':
    result = run_test_suite()
    print(f"RESULT: {{result}}")
"""
            temp_file.write(script_content)
            temp_file.flush()
            
            try:
                # Execute the test suite in a subprocess
                process = await asyncio.create_subprocess_exec(
                    'python3', temp_file.name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.framework_path
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    return {
                        "status": "error",
                        "error": stderr.decode(),
                        "stdout": stdout.decode()
                    }
                
                # Parse the result
                output = stdout.decode()
                if "RESULT:" in output:
                    result_str = output.split("RESULT:")[-1].strip()
                    try:
                        result = json.loads(result_str)
                        return {
                            "status": "success",
                            "result": result
                        }
                    except json.JSONDecodeError:
                        return {
                            "status": "success",
                            "result": result_str
                        }
                else:
                    return {
                        "status": "success",
                        "result": output
                    }
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_file.name)
    
    async def get_available_suites(self) -> List[Dict[str, Any]]:
        """
        Get list of available test suites from QA-FRAMEWORK
        """
        # Look for test suite definitions in the QA-FRAMEWORK
        suites = []
        
        # Example: look for test suite files
        test_dirs = [
            self.framework_path / "tests",
            self.framework_path / "examples"
        ]
        
        for test_dir in test_dirs:
            if test_dir.exists():
                for file_path in test_dir.rglob("*.py"):
                    if "test_" in file_path.name or "_test" in file_path.name:
                        suite_info = {
                            "name": file_path.stem,
                            "path": str(file_path.relative_to(self.framework_path)),
                            "framework_type": "pytest"
                        }
                        suites.append(suite_info)
        
        # Also look for suites defined in the core framework
        core_suites = [
            {"name": "api_tests", "path": "api_testing", "framework_type": "pytest"},
            {"name": "ui_tests", "path": "ui_testing", "framework_type": "pytest"},
            {"name": "db_tests", "path": "database_testing", "framework_type": "pytest"},
            {"name": "security_tests", "path": "security_testing", "framework_type": "pytest"},
            {"name": "performance_tests", "path": "performance_testing", "framework_type": "pytest"},
            {"name": "mobile_tests", "path": "mobile_testing", "framework_type": "pytest"}
        ]
        
        suites.extend(core_suites)
        
        return suites
    
    async def get_test_results(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve test results for a specific execution
        """
        # Look for test results in the QA-FRAMEWORK output directory
        results_dir = self.framework_path / "output" / "results"
        
        if results_dir.exists():
            result_file = results_dir / f"{execution_id}_results.json"
            if result_file.exists():
                with open(result_file, 'r') as f:
                    return json.load(f)
        
        return None


# Singleton instance
# qa_client = QAFrameworkClient()  # Commented for Railway deployment


async def execute_qa_test_suite(suite_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convenience function to execute a QA-FRAMEWORK test suite
    """
    client = QAFrameworkClient()
    return await client.execute_test_suite(suite_name, params)


async def get_qa_test_suites() -> List[Dict[str, Any]]:
    """
    Convenience function to get available QA-FRAMEWORK test suites
    """
    client = QAFrameworkClient()
    return await client.get_available_suites()