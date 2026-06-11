"""
Integration Manager

Centralized manager for all integrations.
Handles registration, configuration, and orchestration of multiple providers.
"""
from typing import Dict, List, Optional, Type, Any, Union
from integrations.base import IntegrationBase, TestResult, SyncResult
from .jira.client import JiraIntegration
from .zephyr.client import ZephyrIntegration
from .alm.client import ALMIntegration
from .testlink.client import TestLinkIntegration
from .azure_devops.client import AzureDevOpsIntegration


class IntegrationManager:
    """
    Centralized manager for all integrations.
    
    Features:
    - Register/unregister integrations
    - Maintain active connections
    - Orchestrate multi-provider sync
    - Handle configuration validation
    - Provide unified interface
    """
    
    # Registry of available integration providers
    _registry: Dict[str, Type[IntegrationBase]] = {
        "jira": JiraIntegration,
        "zephyr": ZephyrIntegration,
        "alm": ALMIntegration,
        "testlink": TestLinkIntegration,
        "azure_devops": AzureDevOpsIntegration,
    }
    
    def __init__(self):
        """Initialize the integration manager"""
        self._instances: Dict[str, IntegrationBase] = {}
        self._active_providers: List[str] = []
    
    @classmethod
    def get_available_providers(cls) -> List[Dict[str, Any]]:
        """
        Get list of all available integration providers.
        
        Returns:
            List of provider metadata
        """
        providers = []
        
        for provider_name, provider_class in cls._registry.items():
            # Create a minimal valid config for each provider to instantiate it
            minimal_config = {}
            
            # For each provider type, provide minimal valid config to bypass validation
            if provider_name == "jira":
                minimal_config = {
                    "base_url": "https://example.atlassian.net",
                    "email": "test@example.com",
                    "api_token": "dummy_token"
                }
            elif provider_name == "zephyr":
                minimal_config = {
                    "jira_base_url": "https://example.atlassian.net",
                    "jira_email": "test@example.com",
                    "jira_api_token": "dummy_token"
                }
            elif provider_name == "alm":
                minimal_config = {
                    "base_url": "https://alm.example.com/qcbin",
                    "username": "test",
                    "password": "test",
                    "domain": "DEFAULT",
                    "project": "TEST"
                }
            elif provider_name == "testlink":
                minimal_config = {
                    "server_url": "http://testlink.example.com/lib/api/xmlrpc/v1/xmlrpc.php",
                    "api_key": "dummy_key"
                }
            elif provider_name == "azure_devops":
                minimal_config = {
                    "organization_url": "https://dev.azure.com/example",
                    "project_name": "test_project",
                    "personal_access_token": "dummy_token"
                }
            
            try:
                integration_instance = provider_class(minimal_config)
                providers.append({
                    "name": provider_name,
                    "display_name": integration_instance.provider_display_name,
                    "description": integration_instance.provider_description,
                    "requires_auth": integration_instance.requires_auth,
                    "supports_sync": integration_instance.supports_sync,
                    "supports_test_cases": integration_instance.supports_test_cases,
                    "supports_bugs": integration_instance.supports_bugs,
                    "supports_cycles": integration_instance.supports_cycles,
                    "config_schema": integration_instance.get_config_schema(),
                    "paid": getattr(integration_instance, 'IS_PAID', False) if hasattr(integration_instance, 'IS_PAID') else False,
                    "estimated_cost": getattr(integration_instance, 'ESTIMATED_COST', None) if hasattr(integration_instance, 'ESTIMATED_COST') else None
                })
            except Exception:
                # If instantiation fails, use default values
                providers.append({
                    "name": provider_name,
                    "display_name": f"{provider_name.title()} Integration",
                    "description": f"Integration for {provider_name}",
                    "requires_auth": True,
                    "supports_sync": True,
                    "supports_test_cases": True,
                    "supports_bugs": True,
                    "supports_cycles": False,
                    "config_schema": {},
                    "paid": False,
                    "estimated_cost": None
                })
        
        return providers
    
    def register_integration(
        self,
        provider: str,
        config: Dict[str, Any]
    ) -> bool:
        """
        Register and configure an integration.
        
        Args:
            provider: Provider name (e.g., 'jira', 'zephyr')
            config: Configuration dictionary for the provider
        
        Returns:
            True if registration successful, False otherwise
        """
        if provider not in self._registry:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Create instance of the integration
        integration_class = self._registry[provider]
        instance = integration_class(config)
        
        # Validate configuration
        is_valid, errors = instance.validate_config()
        if not is_valid:
            raise ValueError(f"Invalid configuration for {provider}: {', '.join(errors)}")
        
        # Store instance
        self._instances[provider] = instance
        if provider not in self._active_providers:
            self._active_providers.append(provider)
        
        return True
    
    def unregister_integration(self, provider: str) -> bool:
        """
        Unregister an integration.
        
        Args:
            provider: Provider name to unregister
        
        Returns:
            True if unregistration successful
        """
        if provider in self._instances:
            # Disconnect if connected
            try:
                if self._instances[provider].is_connected:
                    import asyncio
                    # We can't use await here in a sync method, so we'll skip disconnect for now
                    # In a real implementation, this would need to be async
                    pass
            except Exception:
                pass  # Ignore disconnect errors
            
            del self._instances[provider]
            if provider in self._active_providers:
                self._active_providers.remove(provider)
            return True
        
        return False
    
    async def connect_integration(self, provider: str) -> bool:
        """
        Connect to a specific integration.
        
        Args:
            provider: Provider name to connect to
        
        Returns:
            True if connection successful
        """
        if provider not in self._instances:
            raise ValueError(f"Integration not registered: {provider}")
        
        return await self._instances[provider].connect()
    
    async def disconnect_integration(self, provider: str) -> bool:
        """
        Disconnect from a specific integration.
        
        Args:
            provider: Provider name to disconnect from
        
        Returns:
            True if disconnection successful
        """
        if provider not in self._instances:
            return True  # Not registered, so considered disconnected
        
        return await self._instances[provider].disconnect()
    
    async def health_check(self, provider: str) -> Dict[str, Any]:
        """
        Check health status of a specific integration.
        
        Args:
            provider: Provider name to check
        
        Returns:
            Health status dictionary
        """
        if provider not in self._instances:
            return {
                "status": "not_configured",
                "connected": False,
                "error": f"Integration not registered: {provider}"
            }
        
        return await self._instances[provider].health_check()
    
    async def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status for all configured integrations.
        
        Returns:
            Dictionary with provider name as key and health status as value
        """
        health_status = {}
        
        for provider in self._active_providers:
            health_status[provider] = await self.health_check(provider)
        
        return health_status
    
    async def sync_test_results(
        self,
        results: List[TestResult],
        providers: Optional[List[str]] = None,
        project_key: Optional[str] = None,
        cycle_name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, SyncResult]:
        """
        Synchronize test results across multiple providers.
        
        Args:
            results: List of test results to sync
            providers: List of providers to sync to (None = all active)
            project_key: Project key for the sync
            cycle_name: Test cycle name
            **kwargs: Additional arguments passed to providers
        
        Returns:
            Dictionary with provider name as key and SyncResult as value
        """
        target_providers = providers or self._active_providers
        sync_results = {}
        
        for provider in target_providers:
            if provider not in self._instances:
                sync_results[provider] = SyncResult(
                    provider=provider,
                    success=False,
                    errors=[f"Integration not configured: {provider}"]
                )
                continue
            
            try:
                integration = self._instances[provider]
                
                # Connect if not already connected
                if not integration.is_connected:
                    await integration.connect()
                
                # Perform sync
                result = await integration.sync_test_results(
                    results=results,
                    project_key=project_key,
                    cycle_name=cycle_name,
                    **kwargs
                )
                
                sync_results[provider] = result
                
            except Exception as e:
                sync_results[provider] = SyncResult(
                    provider=provider,
                    success=False,
                    errors=[str(e)]
                )
        
        return sync_results
    
    async def create_test_case(
        self,
        provider: str,
        name: str,
        description: str,
        project_key: str,
        folder: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a test case in a specific provider.
        
        Args:
            provider: Provider name
            name: Test case name
            description: Test case description
            project_key: Project key
            folder: Folder/test suite
            labels: Labels/tags
            **kwargs: Provider-specific options
        
        Returns:
            Dictionary with created test case information
        """
        if provider not in self._instances:
            raise ValueError(f"Integration not configured: {provider}")
        
        integration = self._instances[provider]
        
        if not integration.is_connected:
            await integration.connect()
        
        return await integration.create_test_case(
            name=name,
            description=description,
            project_key=project_key,
            folder=folder,
            labels=labels,
            **kwargs
        )
    
    async def get_test_cases(
        self,
        provider: str,
        project_key: str,
        folder: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get test cases from a specific provider.
        
        Args:
            provider: Provider name
            project_key: Project key
            folder: Folder/test suite
            filters: Additional filters
        
        Returns:
            List of test case dictionaries
        """
        if provider not in self._instances:
            raise ValueError(f"Integration not configured: {provider}")
        
        integration = self._instances[provider]
        
        if not integration.is_connected:
            await integration.connect()
        
        return await integration.get_test_cases(
            project_key=project_key,
            folder=folder,
            filters=filters
        )
    
    async def create_bug(
        self,
        provider: str,
        title: str,
        description: str,
        project_key: str,
        test_result: Optional[TestResult] = None,
        severity: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a bug in a specific provider.
        
        Args:
            provider: Provider name
            title: Bug title
            description: Bug description
            project_key: Project key
            test_result: Associated test result
            severity: Bug severity
            priority: Bug priority
            labels: Labels/tags
            **kwargs: Provider-specific options
        
        Returns:
            Dictionary with created bug information
        """
        if provider not in self._instances:
            raise ValueError(f"Integration not configured: {provider}")
        
        integration = self._instances[provider]
        
        if not integration.is_connected:
            await integration.connect()
        
        return await integration.create_bug(
            title=title,
            description=description,
            project_key=project_key,
            test_result=test_result,
            severity=severity,
            priority=priority,
            labels=labels,
            **kwargs
        )
    
    async def get_bugs(
        self,
        provider: str,
        project_key: str,
        status: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get bugs from a specific provider.
        
        Args:
            provider: Provider name
            project_key: Project key
            status: Filter by status
            filters: Additional filters
        
        Returns:
            List of bug dictionaries
        """
        if provider not in self._instances:
            raise ValueError(f"Integration not configured: {provider}")
        
        integration = self._instances[provider]
        
        if not integration.is_connected:
            await integration.connect()
        
        return await integration.get_bugs(
            project_key=project_key,
            status=status,
            filters=filters
        )
    
    async def get_projects(self, provider: str) -> List[Dict[str, Any]]:
        """
        Get projects from a specific provider.
        
        Args:
            provider: Provider name
        
        Returns:
            List of project dictionaries
        """
        if provider not in self._instances:
            raise ValueError(f"Integration not configured: {provider}")
        
        integration = self._instances[provider]
        
        if not integration.is_connected:
            await integration.connect()
        
        return await integration.get_projects()
    
    def get_integration(self, provider: str) -> Optional[IntegrationBase]:
        """
        Get the integration instance for a provider.
        
        Args:
            provider: Provider name
        
        Returns:
            Integration instance or None if not configured
        """
        return self._instances.get(provider)
    
    def get_active_providers(self) -> List[str]:
        """
        Get list of currently active providers.
        
        Returns:
            List of provider names
        """
        return self._active_providers.copy()
    
    def get_configured_providers(self) -> List[Dict[str, Any]]:
        """
        Get list of configured providers with their status.
        
        Returns:
            List of provider status dictionaries
        """
        providers = []
        
        for provider_name in self._active_providers:
            integration = self._instances[provider_name]
            providers.append({
                "name": provider_name,
                "display_name": integration.provider_display_name,
                "connected": integration.is_connected,
                "supports": {
                    "sync": integration.supports_sync,
                    "test_cases": integration.supports_test_cases,
                    "bugs": integration.supports_bugs,
                    "cycles": integration.supports_cycles
                }
            })
        
        return providers
    
    async def bulk_sync(
        self,
        results: List[TestResult],
        mappings: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Perform bulk synchronization with different configurations per provider.
        
        Args:
            results: Test results to sync
            mappings: Provider-specific configurations
                {
                    "jira": {"project_key": "QA", "cycle_name": "Release 1.0"},
                    "zephyr": {"project_key": "QA", "cycle_name": "Sprint 1"},
                    "testlink": {"project_key": "QA Project", "cycle_name": "Cycle 1"}
                }
        
        Returns:
            Nested dictionary with sync results per provider and configuration
        """
        bulk_results = {}
        
        for provider, config in mappings.items():
            project_key = config.get('project_key')
            cycle_name = config.get('cycle_name')
            
            bulk_results[provider] = await self.sync_test_results(
                results=results,
                providers=[provider],
                project_key=project_key,
                cycle_name=cycle_name
            )
        
        return bulk_results


# Global singleton instance
integration_manager = IntegrationManager()
