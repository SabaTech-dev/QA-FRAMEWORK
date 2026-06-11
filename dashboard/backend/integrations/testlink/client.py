"""
TestLink API Client

Implements IntegrationBase for TestLink - open source test management.
Uses XML-RPC API for communication.

API Reference: https://www.testlink.org/api/
"""
import xmlrpc.client
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from integrations.base import IntegrationBase, TestResult, SyncResult, TestStatus
from integrations.testlink.config import TestLinkConfig


class TestLinkIntegration(IntegrationBase):
    """
    TestLink integration for open source test management.
    
    Features:
    - Test case management
    - Test execution tracking
    - Requirements traceability
    - Custom fields support
    
    FREE and open source
    """
    
    provider_name = "testlink"
    provider_display_name = "TestLink"
    provider_description = "Open source test management tool"
    requires_auth = True
    supports_sync = True
    supports_test_cases = True
    supports_bugs = True
    supports_cycles = True
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        self.testlink_config = TestLinkConfig(**config) if isinstance(config, dict) else config
        
        self.server_url = self.testlink_config.server_url
        self.api_key = self.testlink_config.api_key
        self.dev_key = self.testlink_config.dev_key
        self.default_project = self.testlink_config.default_project
        
        # XML-RPC client
        self._client: Optional[xmlrpc.client.ServerProxy] = None
        self._project_cache: Dict[str, int] = {}
    
    def _get_client(self) -> xmlrpc.client.ServerProxy:
        """Get or create XML-RPC client"""
        if self._client is None:
            self._client = xmlrpc.client.ServerProxy(self.server_url)
        return self._client
    
    def _get_project_id(self, project_name: str) -> int:
        """Get project ID by name (cached)"""
        if project_name in self._project_cache:
            return self._project_cache[project_name]
        
        client = self._get_client()
        projects = client.tl.getProjects(self.api_key)
        
        for project in projects:
            if project['name'] == project_name:
                project_id = int(project['id'])
                self._project_cache[project_name] = project_id
                return project_id
        
        raise ValueError(f"Project not found: {project_name}")
    
    # ==================== Connection Methods ====================
    
    async def connect(self) -> bool:
        """Connect to TestLink and validate credentials"""
        try:
            client = self._get_client()
            
            # Test connection by getting projects
            projects = client.tl.getProjects(self.api_key)
            
            # If we get projects, connection is valid
            if isinstance(projects, list):
                self.is_connected = True
                return True
            else:
                self._set_error(f"Connection failed: {projects}")
                return False
                
        except Exception as e:
            self._set_error(f"Connection error: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from TestLink"""
        self._client = None
        self.is_connected = False
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Check TestLink connection health"""
        start_time = time.time()
        
        if not self.is_connected:
            await self.connect()
        
        try:
            client = self._get_client()
            
            # Get basic server info
            projects = client.tl.getProjects(self.api_key)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "status": "healthy",
                "connected": True,
                "latency_ms": latency_ms,
                "server": self.server_url,
                "project_count": len(projects) if isinstance(projects, list) else 0,
                "error": None
            }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "latency_ms": int((time.time() - start_time) * 1000),
                "error": str(e)
            }
    
    # ==================== Synchronization Methods ====================
    
    async def sync_test_results(
        self,
        results: List[TestResult],
        project_key: Optional[str] = None,
        cycle_name: Optional[str] = None,
        **kwargs
    ) -> SyncResult:
        """Sync test results to TestLink"""
        if not self.is_connected:
            await self.connect()
        
        project = project_key or self.default_project
        if not project:
            return SyncResult(
                provider=self.provider_name,
                success=False,
                errors=["No project specified"]
            )
        
        try:
            project_id = self._get_project_id(project)
        except ValueError:
            return SyncResult(
                provider=self.provider_name,
                success=False,
                errors=[f"Project not found: {project}"]
            )
        
        # Create test plan if needed
        plan_name = cycle_name or f"QA-Framework Plan {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        try:
            plan_response = self._client.tl.createTestPlan(
                self.api_key, plan_name, project
            )
            plan_id = plan_response['id']
        except Exception:
            # Plan might already exist, try to find it
            plans = self._client.tl.getProjectTestPlans(self.api_key, project_id)
            plan_id = None
            for plan in plans:
                if plan['name'] == plan_name:
                    plan_id = plan['id']
                    break
            if not plan_id:
                plan_id = plans[0]['id'] if plans else None
        
        if not plan_id:
            return SyncResult(
                provider=self.provider_name,
                success=False,
                errors=["Could not create or find test plan"]
            )
        
        synced = 0
        failed = 0
        errors = []
        
        for result in results:
            try:
                # Find or create test case
                test_case_id = None
                try:
                    # Try to find existing test case by name
                    search_result = self._client.tl.getTestCaseIDByName(
                        result.test_name, project
                    )
                    if search_result:
                        test_case_id = search_result[0]['id']
                except Exception:
                    pass
                
                if not test_case_id:
                    # Create new test case
                    tc_response = self._client.tl.createTestCase(
                        self.api_key,
                        result.test_name,
                        project_id,
                        "General",  # test suite
                        "Auto-generated by QA-Framework",
                        result.test_name,
                        "automated"
                    )
                    test_case_id = tc_response['id']
                
                # Report test result
                status_map = {
                    TestStatus.PASSED: 'p',
                    TestStatus.FAILED: 'f',
                    TestStatus.SKIPPED: 'b',
                    TestStatus.BLOCKED: 'b',
                    TestStatus.UNTESTED: 'n'
                }
                
                status = status_map.get(result.status, 'f')
                
                # Create test execution
                exec_response = self._client.tl.reportTCResult(
                    self.api_key,
                    test_case_id,
                    plan_id,
                    status,
                    notes=f"Duration: {result.duration}s\n{result.error or ''}",
                    guess='true'
                )
                
                if exec_response:
                    synced += 1
                else:
                    failed += 1
                    errors.append(f"{result.test_name}: Failed to report result")
                    
            except Exception as e:
                failed += 1
                errors.append(f"{result.test_name}: {str(e)}")
        
        return SyncResult(
            provider=self.provider_name,
            success=(failed == 0),
            synced_count=synced,
            failed_count=failed,
            errors=errors,
            details={
                "plan_id": plan_id,
                "plan_name": plan_name
            }
        )
    
    # ==================== Test Case Methods ====================
    
    async def create_test_case(
        self,
        name: str,
        description: str,
        project_key: str,
        folder: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a test case in TestLink"""
        if not self.is_connected:
            await self.connect()
        
        try:
            project_id = self._get_project_id(project_key)
        except ValueError:
            raise ValueError(f"Project not found: {project_key}")
        
        client = self._get_client()
        
        # Create test case
        response = client.tl.createTestCase(
            self.api_key,
            name,
            project_id,
            folder or "General",  # test suite
            description,
            name,  # summary
            "automated",
            **kwargs
        )
        
        if 'id' in response:
            return {
                "id": response['id'],
                "name": name,
                "url": f"{self.server_url.replace('/lib/api/xmlrpc/v1/xmlrpc.php', '')}/lib/testcases/index.php?itemAction=view&id={response['id']}"
            }
        else:
            raise Exception(f"Failed to create test case: {response}")
    
    async def get_test_cases(
        self,
        project_key: str,
        folder: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get test cases from TestLink"""
        if not self.is_connected:
            await self.connect()
        
        try:
            project_id = self._get_project_id(project_key)
        except ValueError:
            return []
        
        client = self._get_client()
        
        # Get test suites in project
        suites = client.tl.getFirstLevelTestSuitesForTestProject(self.api_key, project_id)
        
        test_cases = []
        for suite in suites:
            if folder and suite['name'] != folder:
                continue
            
            # Get test cases in suite
            tcs = client.tl.getTestCasesForTestSuite(
                self.api_key, suite['id'], True, 'full'
            )
            
            for tc in tcs:
                test_cases.append({
                    "id": tc['id'],
                    "key": tc['externalid'],
                    "name": tc['name'],
                    "status": tc.get('status', 'draft'),
                    "url": f"{self.server_url.replace('/lib/api/xmlrpc/v1/xmlrpc.php', '')}/lib/testcases/index.php?itemAction=view&id={tc['id']}"
                })
        
        return test_cases
    
    async def update_test_case(
        self,
        test_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a test case in TestLink"""
        if not self.is_connected:
            await self.connect()
        
        client = self._get_client()
        
        # Update test case
        response = client.tl.updateTestCase(
            self.api_key,
            test_id,
            summary=updates.get('name'),
            description=updates.get('description'),
            **updates
        )
        
        if response:
            return {"id": test_id, "updated": True}
        else:
            raise Exception(f"Failed to update test case: {response}")
    
    # ==================== Bug Methods ====================
    
    async def create_bug(
        self,
        title: str,
        description: str,
        project_key: str,
        test_result: Optional[TestResult] = None,
        severity: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a requirement or issue in TestLink"""
        if not self.is_connected:
            await self.connect()
        
        try:
            project_id = self._get_project_id(project_key)
        except ValueError:
            raise ValueError(f"Project not found: {project_key}")
        
        client = self._get_client()
        
        # Create requirement (TestLink's way of tracking issues)
        response = client.tl.createRequirement(
            self.api_key,
            title,
            project_id,
            "Functional",  # req type
            description,
            "high"  # priority
        )
        
        if 'id' in response:
            return {
                "id": response['id'],
                "url": f"{self.server_url.replace('/lib/api/xmlrpc/v1/xmlrpc.php', '')}/lib/requirements/index.php?itemAction=view&id={response['id']}"
            }
        else:
            raise Exception(f"Failed to create requirement: {response}")
    
    async def get_bugs(
        self,
        project_key: str,
        status: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get requirements from TestLink"""
        if not self.is_connected:
            await self.connect()
        
        try:
            project_id = self._get_project_id(project_key)
        except ValueError:
            return []
        
        client = self._get_client()
        
        # Get requirements
        response = client.tl.getReqSpecsForTestProject(self.api_key, project_id)
        
        bugs = []
        for req_spec in response:
            reqs = client.tl.getRequirements(self.api_key, req_spec['id'])
            for req in reqs:
                bugs.append({
                    "id": req['id'],
                    "key": req['req_doc_id'],
                    "title": req['title'],
                    "status": req.get('status', 'open'),
                    "url": f"{self.server_url.replace('/lib/api/xmlrpc/v1/xmlrpc.php', '')}/lib/requirements/index.php?itemAction=view&id={req['id']}"
                })
        
        return bugs
    
    # ==================== Project Methods ====================
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get list of TestLink projects"""
        if not self.is_connected:
            await self.connect()
        
        client = self._get_client()
        projects = client.tl.getProjects(self.api_key)
        
        return [
            {
                "key": str(p['id']),
                "name": p['name'],
                "id": p['id']
            }
            for p in projects
        ]
    
    # ==================== Configuration ====================
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate TestLink configuration"""
        errors = []
        
        try:
            config = TestLinkConfig(**self.config)
        except Exception as e:
            errors.append(str(e))
            return False, errors
        
        if not config.server_url:
            errors.append("server_url is required")
        elif not config.server_url.startswith(('http://', 'https://')):
            errors.append("server_url must use HTTP or HTTPS")
        
        if not config.api_key:
            errors.append("api_key is required")
        
        return len(errors) == 0, errors
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for UI"""
        return {
            "type": "object",
            "title": "TestLink Configuration",
            "properties": {
                "server_url": {
                    "type": "string",
                    "title": "TestLink Server URL",
                    "description": "URL to TestLink XML-RPC API (usually ends with /lib/api/xmlrpc/v1/xmlrpc.php)",
                    "format": "uri"
                },
                "api_key": {
                    "type": "string",
                    "title": "API Key",
                    "description": "Generate in TestLink under My Settings > API Key",
                    "secret": True
                },
                "default_project": {
                    "type": "string",
                    "title": "Default Project Name"
                },
                "dev_key": {
                    "type": "string",
                    "title": "Developer Key (Optional)",
                    "secret": True
                }
            },
            "required": ["server_url", "api_key"]
        }
