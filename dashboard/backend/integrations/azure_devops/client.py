"""
Azure DevOps API Client

Implements IntegrationBase for Microsoft Azure DevOps.
Supports both Azure DevOps Services (cloud) and Azure DevOps Server (on-premise).

API Reference: https://docs.microsoft.com/en-us/rest/api/azure/devops/
"""

import base64
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import httpx

from integrations.base import IntegrationBase, TestResult, SyncResult, TestStatus
from integrations.azure_devops.config import AzureDevOpsConfig


def _wiql_escape(value: str) -> str:
    """Escape single quotes for inline WIQL literals (WIQL has no parameterized queries)."""
    return str(value).replace("'", "''")


class AzureDevOpsIntegration(IntegrationBase):
    """
    Azure DevOps integration for work item and test management.

    Features:
    - Work items (stories, tasks, bugs)
    - Test plans and test suites
    - Test results
    - CI/CD integration

    Free Tier: Up to 5 users
    """

    provider_name = "azure_devops"
    provider_display_name = "Azure DevOps"
    provider_description = "Microsoft Azure DevOps work item and test management"
    requires_auth = True
    supports_sync = True
    supports_test_cases = True
    supports_bugs = True
    supports_cycles = True

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        self.ado_config = AzureDevOpsConfig(**config) if isinstance(config, dict) else config

        self.organization_url = self.ado_config.organization_url
        self.project_name = self.ado_config.project_name
        self.personal_access_token = self.ado_config.personal_access_token
        self.area_path = self.ado_config.area_path
        self.iteration_path = self.ado_config.iteration_path

        # API base URL
        self.api_base = f"{self.organization_url}/{self.project_name}/_apis"

        # Authentication header
        auth_string = f":{self.personal_access_token}"
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.organization_url,
                headers=self.headers,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    # ==================== Connection Methods ====================

    async def connect(self) -> bool:
        """Connect to Azure DevOps and validate credentials"""
        try:
            client = await self._get_client()

            # Test connection by getting project info
            response = await client.get(
                f"/{self.project_name}/_apis/projects/{self.project_name}",
                params={"api-version": "7.0"},
            )

            if response.status_code == 200:
                self.is_connected = True
                return True
            else:
                self._set_error(f"Authentication failed: {response.status_code}")
                return False

        except Exception as e:
            self._set_error(f"Connection error: {str(e)}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Azure DevOps"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.is_connected = False
        return True

    async def health_check(self) -> Dict[str, Any]:
        """Check Azure DevOps connection health"""
        start_time = time.time()

        if not self.is_connected:
            await self.connect()

        try:
            client = await self._get_client()

            response = await client.get(
                f"/{self.project_name}/_apis/projects/{self.project_name}",
                params={"api-version": "7.0"},
            )

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                project = response.json()
                return {
                    "status": "healthy",
                    "connected": True,
                    "latency_ms": latency_ms,
                    "server": self.organization_url,
                    "project": project.get("name"),
                    "error": None,
                }
            else:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "latency_ms": latency_ms,
                    "error": f"HTTP {response.status_code}",
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "latency_ms": int((time.time() - start_time) * 1000),
                "error": str(e),
            }

    # ==================== Synchronization Methods ====================

    async def sync_test_results(
        self,
        results: List[TestResult],
        project_key: Optional[str] = None,
        cycle_name: Optional[str] = None,
        **kwargs,
    ) -> SyncResult:
        """Sync test results to Azure DevOps test runs"""
        if not self.is_connected:
            await self.connect()

        project = project_key or self.project_name

        synced = 0
        failed = 0
        errors = []

        # Create a test run if cycle_name is provided
        test_run_id = None
        if cycle_name:
            try:
                test_run = await self._create_test_run(cycle_name, project)
                test_run_id = test_run.get("id")
            except Exception as e:
                errors.append(f"Failed to create test run: {str(e)}")

        for result in results:
            try:
                # Create or update test result
                if result.status == TestStatus.FAILED:
                    # Create bug for failed test
                    if result.test_id:
                        await self.create_bug(
                            title=f"[QA] Test Failed: {result.test_name}",
                            description=self._format_test_result_for_bug(result),
                            project_key=project,
                            test_result=result,
                        )

                # Associate with test run if applicable
                if test_run_id:
                    await self._add_test_result_to_run(test_run_id, result)

                synced += 1

            except Exception as e:
                failed += 1
                errors.append(f"{result.test_name}: {str(e)}")

        return SyncResult(
            provider=self.provider_name,
            success=(failed == 0),
            synced_count=synced,
            failed_count=failed,
            errors=errors,
        )

    async def _create_test_run(self, name: str, project: str) -> Dict[str, Any]:
        """Create a test run in Azure DevOps"""
        client = await self._get_client()

        payload = {
            "name": name,
            "project": {"id": await self._get_project_id(project)},
            "state": "InProgress",
        }

        response = await client.post(
            f"/{project}/_apis/test/runs", params={"api-version": "7.0"}, json=payload
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to create test run: {response.text}")

    async def _add_test_result_to_run(self, run_id: str, result: TestResult):
        """Add a test result to a test run"""
        client = await self._get_client()

        # Map test status to Azure DevOps status
        ado_status = {
            TestStatus.PASSED: "Passed",
            TestStatus.FAILED: "Failed",
            TestStatus.SKIPPED: "NotExecuted",
            TestStatus.BLOCKED: "Blocked",
            TestStatus.UNTESTED: "NotExecuted",
        }.get(result.status, "Failed")

        payload = {
            "testCaseTitle": result.test_name,
            "outcome": ado_status,
            "comment": f"Duration: {result.duration}s",
            "errorMessage": result.error,
        }

        response = await client.patch(
            f"/{self.project_name}/_apis/test/runs/{run_id}/results",
            params={"api-version": "7.0"},
            json=[payload],
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to add test result: {response.text}")

    async def _get_project_id(self, project_name: str) -> str:
        """Get project ID by name"""
        client = await self._get_client()

        response = await client.get(
            f"/_apis/projects/{project_name}", params={"api-version": "7.0"}
        )

        if response.status_code == 200:
            return response.json()["id"]
        else:
            raise Exception(f"Project not found: {project_name}")

    # ==================== Test Case Methods ====================

    async def create_test_case(
        self,
        name: str,
        description: str,
        project_key: str,
        folder: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a test case as a work item in Azure DevOps"""
        if not self.is_connected:
            await self.connect()

        client = await self._get_client()

        # Build work item payload
        work_item_fields = {
            "System.Title": name,
            "System.Description": description,
            "System.WorkItemType": "Test Case",
        }

        if self.area_path:
            work_item_fields["System.AreaPath"] = self.area_path
        if self.iteration_path:
            work_item_fields["System.IterationPath"] = self.iteration_path

        if labels:
            work_item_fields["System.Tags"] = "; ".join(labels)

        # Format for Azure DevOps PATCH API
        patch_document = []
        for field, value in work_item_fields.items():
            patch_document.append({"op": "add", "path": f"/fields/{field}", "value": value})

        response = await client.patch(
            f"/{project_key or self.project_name}/_apis/wit/workitems/$Test Case",
            params={"api-version": "7.0"},
            json=patch_document,
        )

        if response.status_code == 200:
            work_item = response.json()
            return {
                "id": work_item.get("id"),
                "key": str(work_item.get("id")),
                "name": name,
                "url": work_item.get("_links", {}).get("html", {}).get("href"),
            }
        else:
            raise Exception(f"Failed to create test case: {response.text}")

    async def get_test_cases(
        self,
        project_key: str,
        folder: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get test cases from Azure DevOps"""
        if not self.is_connected:
            await self.connect()

        client = await self._get_client()

        # Build WiQL query
        wiql_query = f"""
        SELECT [System.Id], [System.Title], [System.State], [System.Tags]
        FROM WorkItems
        WHERE [System.TeamProject] = '{_wiql_escape(project_key or self.project_name)}'
        AND [System.WorkItemType] = 'Test Case'
        """  # nosec B608 — WIQL has no parameterized queries; values escaped via _wiql_escape()

        if filters:
            if filters.get("status"):
                wiql_query += f" AND [System.State] = '{_wiql_escape(filters['status'])}'"
            if filters.get("tags"):
                for tag in filters["tags"]:
                    wiql_query += f" AND [System.Tags] CONTAINS '{_wiql_escape(tag)}'"

        payload = {"query": wiql_query}

        response = await client.post(
            f"/{project_key or self.project_name}/_apis/wit/wiql",
            params={"api-version": "7.0"},
            json=payload,
        )

        if response.status_code == 200:
            data = response.json()
            work_items = []

            for item in data.get("workItems", []):
                # Get full details for each work item
                detail_response = await client.get(
                    f"/{project_key or self.project_name}/_apis/wit/workitems/{item['id']}",
                    params={"api-version": "7.0"},
                )

                if detail_response.status_code == 200:
                    details = detail_response.json()
                    work_items.append(
                        {
                            "id": details.get("id"),
                            "key": str(details.get("id")),
                            "name": next(
                                (
                                    f["value"]
                                    for f in details.get("fields", [])
                                    if f["fieldName"] == "Title"
                                ),
                                "",
                            ),
                            "status": next(
                                (
                                    f["value"]
                                    for f in details.get("fields", [])
                                    if f["fieldName"] == "State"
                                ),
                                "",
                            ),
                            "tags": next(
                                (
                                    f["value"]
                                    for f in details.get("fields", [])
                                    if f["fieldName"] == "Tags"
                                ),
                                "",
                            ),
                            "url": details.get("_links", {}).get("html", {}).get("href"),
                        }
                    )

            return work_items

        return []

    async def update_test_case(self, test_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a test case in Azure DevOps"""
        if not self.is_connected:
            await self.connect()

        client = await self._get_client()

        patch_document = []

        if updates.get("name"):
            patch_document.append(
                {"op": "replace", "path": "/fields/System.Title", "value": updates["name"]}
            )

        if updates.get("description"):
            patch_document.append(
                {
                    "op": "replace",
                    "path": "/fields/System.Description",
                    "value": updates["description"],
                }
            )

        if updates.get("labels"):
            patch_document.append(
                {
                    "op": "replace",
                    "path": "/fields/System.Tags",
                    "value": "; ".join(updates["labels"]),
                }
            )

        response = await client.patch(
            f"/{self.project_name}/_apis/wit/workitems/{test_id}",
            params={"api-version": "7.0"},
            json=patch_document,
        )

        if response.status_code == 200:
            return {"id": test_id, "updated": True}
        else:
            raise Exception(f"Failed to update test case: {response.text}")

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
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a bug as a work item in Azure DevOps"""
        if not self.is_connected:
            await self.connect()

        client = await self._get_client()

        work_item_fields = {
            "System.Title": title,
            "System.Description": description,
            "System.WorkItemType": "Bug",
            "Microsoft.VSTS.Common.Priority": priority or 2,
            "Microsoft.VSTS.Common.Severity": severity or "3 - Medium",
        }

        if self.area_path:
            work_item_fields["System.AreaPath"] = self.area_path
        if self.iteration_path:
            work_item_fields["System.IterationPath"] = self.iteration_path

        if labels:
            work_item_fields["System.Tags"] = "; ".join(labels)

        if test_result:
            work_item_fields["System.Tags"] = (
                work_item_fields.get("System.Tags", "") + f"; test-{test_result.test_id}"
            )

        # Format for Azure DevOps PATCH API
        patch_document = []
        for field, value in work_item_fields.items():
            patch_document.append({"op": "add", "path": f"/fields/{field}", "value": value})

        response = await client.patch(
            f"/{project_key or self.project_name}/_apis/wit/workitems/$Bug",
            params={"api-version": "7.0"},
            json=patch_document,
        )

        if response.status_code == 200:
            work_item = response.json()
            return {
                "id": work_item.get("id"),
                "key": str(work_item.get("id")),
                "url": work_item.get("_links", {}).get("html", {}).get("href"),
            }
        else:
            raise Exception(f"Failed to create bug: {response.text}")

    async def get_bugs(
        self,
        project_key: str,
        status: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get bugs from Azure DevOps"""
        if not self.is_connected:
            await self.connect()

        client = await self._get_client()

        # Build WiQL query
        wiql_query = f"""
        SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo], [System.CreatedDate]
        FROM WorkItems
        WHERE [System.TeamProject] = '{_wiql_escape(project_key or self.project_name)}'
        AND [System.WorkItemType] = 'Bug'
        """  # nosec B608 — WIQL has no parameterized queries; values escaped via _wiql_escape()

        if status:
            wiql_query += f" AND [System.State] = '{_wiql_escape(status)}'"

        if filters:
            if filters.get("tags"):
                for tag in filters["tags"]:
                    wiql_query += f" AND [System.Tags] CONTAINS '{_wiql_escape(tag)}'"

        payload = {"query": wiql_query}

        response = await client.post(
            f"/{project_key or self.project_name}/_apis/wit/wiql",
            params={"api-version": "7.0"},
            json=payload,
        )

        if response.status_code == 200:
            data = response.json()
            bugs = []

            for item in data.get("workItems", []):
                # Get full details for each work item
                detail_response = await client.get(
                    f"/{project_key or self.project_name}/_apis/wit/workitems/{item['id']}",
                    params={"api-version": "7.0"},
                )

                if detail_response.status_code == 200:
                    details = detail_response.json()
                    bugs.append(
                        {
                            "id": details.get("id"),
                            "key": str(details.get("id")),
                            "title": next(
                                (
                                    f["value"]
                                    for f in details.get("fields", [])
                                    if f["fieldName"] == "Title"
                                ),
                                "",
                            ),
                            "status": next(
                                (
                                    f["value"]
                                    for f in details.get("fields", [])
                                    if f["fieldName"] == "State"
                                ),
                                "",
                            ),
                            "assigned_to": next(
                                (
                                    f["value"]
                                    for f in details.get("fields", [])
                                    if f["fieldName"] == "Assigned To"
                                ),
                                "",
                            ),
                            "url": details.get("_links", {}).get("html", {}).get("href"),
                        }
                    )

            return bugs

        return []

    # ==================== Project Methods ====================

    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get list of Azure DevOps projects"""
        if not self.is_connected:
            await self.connect()

        client = await self._get_client()

        response = await client.get("/_apis/projects", params={"api-version": "7.0"})

        if response.status_code == 200:
            projects = response.json()
            return [
                {"key": p.get("id"), "name": p.get("name"), "id": p.get("id")}
                for p in projects.get("value", [])
            ]

        return []

    # ==================== Configuration ====================

    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate Azure DevOps configuration"""
        errors = []

        try:
            config = AzureDevOpsConfig(**self.config)
        except Exception as e:
            errors.append(str(e))
            return False, errors

        if not config.organization_url:
            errors.append("organization_url is required")
        elif not config.organization_url.startswith("https://dev.azure.com/"):
            errors.append("organization_url must be in format https://dev.azure.com/organization")

        if not config.project_name:
            errors.append("project_name is required")

        if not config.personal_access_token:
            errors.append("personal_access_token is required")

        return len(errors) == 0, errors

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for UI"""
        return {
            "type": "object",
            "title": "Azure DevOps Configuration",
            "properties": {
                "organization_url": {
                    "type": "string",
                    "title": "Organization URL",
                    "description": "Azure DevOps organization URL (e.g., https://dev.azure.com/yourorganization)",
                    "format": "uri",
                },
                "project_name": {
                    "type": "string",
                    "title": "Project Name",
                    "description": "Azure DevOps project name",
                },
                "personal_access_token": {
                    "type": "string",
                    "title": "Personal Access Token",
                    "description": "Generate in Azure DevOps: User Settings > Personal Access Tokens",
                    "secret": True,
                },
                "area_path": {
                    "type": "string",
                    "title": "Area Path (Optional)",
                    "description": "Area path for work items (e.g., Project\\Area1)",
                },
                "iteration_path": {
                    "type": "string",
                    "title": "Iteration Path (Optional)",
                    "description": "Iteration path for work items (e.g., Project\\Iteration1)",
                },
            },
            "required": ["organization_url", "project_name", "personal_access_token"],
        }
