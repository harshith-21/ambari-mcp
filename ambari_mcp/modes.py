"""MCP operational modes for different Ambari management scenarios."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass, field

from .config import MCPModeType


@dataclass
class ModeRestrictions:
    """Restrictions and permissions for an operational mode."""
    allowed_operations: Set[str] = field(default_factory=set)
    denied_operations: Set[str] = field(default_factory=set)
    require_confirmation: Set[str] = field(default_factory=set)
    max_concurrent_operations: int = 5
    timeout_multiplier: float = 1.0
    priority_services: List[str] = field(default_factory=list)
    maintenance_mode_required: bool = False


@dataclass 
class ModeContext:
    """Context information for mode operations."""
    mode_type: MCPModeType
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    initiated_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPMode(ABC):
    """Abstract base class for MCP operational modes."""
    
    def __init__(self, mode_type: MCPModeType):
        self.mode_type = mode_type
        self.restrictions = self._define_restrictions()
        self.context: Optional[ModeContext] = None
        
    @abstractmethod
    def _define_restrictions(self) -> ModeRestrictions:
        """Define the restrictions for this mode."""
        pass
        
    @abstractmethod
    def get_description(self) -> str:
        """Get a human-readable description of this mode."""
        pass
        
    @abstractmethod
    def get_available_tools(self) -> List[str]:
        """Get list of tools available in this mode."""
        pass
        
    @abstractmethod
    def get_context_prompts(self) -> List[str]:
        """Get context-specific prompts for this mode."""
        pass
        
    def can_execute_operation(self, operation: str) -> bool:
        """Check if an operation can be executed in this mode."""
        if operation in self.restrictions.denied_operations:
            return False
        if self.restrictions.allowed_operations and operation not in self.restrictions.allowed_operations:
            return False
        return True
        
    def requires_confirmation(self, operation: str) -> bool:
        """Check if an operation requires user confirmation."""
        return operation in self.restrictions.require_confirmation
        
    def get_operation_timeout(self, base_timeout: int) -> int:
        """Get adjusted timeout for operations in this mode."""
        return int(base_timeout * self.restrictions.timeout_multiplier)
        
    def set_context(self, context: ModeContext) -> None:
        """Set the mode context."""
        self.context = context
        
    def get_mode_specific_resources(self) -> List[str]:
        """Get mode-specific resources."""
        return []


class NormalMode(MCPMode):
    """Normal operational mode - full access to all operations."""
    
    def __init__(self):
        super().__init__(MCPModeType.NORMAL)
        
    def _define_restrictions(self) -> ModeRestrictions:
        return ModeRestrictions(
            allowed_operations=set(),  # Empty means all allowed
            denied_operations=set(),
            require_confirmation={"stop_service", "restart_service", "update_configuration"},
            max_concurrent_operations=10,
            timeout_multiplier=1.0
        )
        
    def get_description(self) -> str:
        return "Normal operational mode with full access to all Ambari operations."
        
    def get_available_tools(self) -> List[str]:
        return [
            "get_cluster_status",
            "list_services", 
            "get_service_info",
            "start_service",
            "stop_service", 
            "restart_service",
            "list_hosts",
            "get_host_info",
            "get_service_components",
            "get_configurations",
            "update_configuration",
            "get_request_status",
            "list_recent_requests",
            "health_check"
        ]
        
    def get_context_prompts(self) -> List[str]:
        return [
            "cluster_overview",
            "service_management",
            "host_monitoring",
            "configuration_help"
        ]


class ClusterMaintenanceMode(MCPMode):
    """Maintenance mode - restricted operations, safety-first approach."""
    
    def __init__(self):
        super().__init__(MCPModeType.CLUSTER_MAINTENANCE)
        
    def _define_restrictions(self) -> ModeRestrictions:
        return ModeRestrictions(
            allowed_operations={
                "get_cluster_status", "list_services", "get_service_info",
                "list_hosts", "get_host_info", "get_service_components",
                "get_configurations", "get_request_status", "list_recent_requests",
                "health_check", "stop_service"  # Only allow stopping services
            },
            denied_operations={"start_service", "restart_service", "update_configuration"},
            require_confirmation={"stop_service"},
            max_concurrent_operations=3,
            timeout_multiplier=2.0,  # Longer timeouts for safety
            maintenance_mode_required=True
        )
        
    def get_description(self) -> str:
        return ("Maintenance mode with restricted operations. Only monitoring and "
                "safe shutdown operations are allowed. Configuration changes are disabled.")
        
    def get_available_tools(self) -> List[str]:
        return [
            "get_cluster_status",
            "list_services",
            "get_service_info", 
            "stop_service",  # Only stopping allowed
            "list_hosts",
            "get_host_info",
            "get_service_components",
            "get_configurations",  # Read-only
            "get_request_status",
            "list_recent_requests",
            "health_check"
        ]
        
    def get_context_prompts(self) -> List[str]:
        return [
            "maintenance_checklist",
            "safe_shutdown_sequence",
            "maintenance_monitoring"
        ]
        
    def get_mode_specific_resources(self) -> List[str]:
        return [
            "maintenance_procedures",
            "shutdown_sequences",
            "rollback_plans"
        ]


class ScaleUpMode(MCPMode):
    """Scale-up mode - optimized for adding capacity and scaling operations."""
    
    def __init__(self):
        super().__init__(MCPModeType.SCALE_UP)
        
    def _define_restrictions(self) -> ModeRestrictions:
        return ModeRestrictions(
            allowed_operations={
                "get_cluster_status", "list_services", "get_service_info",
                "start_service", "restart_service", "list_hosts", "get_host_info",
                "get_service_components", "get_configurations", "update_configuration",
                "get_request_status", "list_recent_requests", "health_check"
            },
            denied_operations={"stop_service"},  # Prevent accidental shutdowns during scaling
            require_confirmation={"restart_service", "update_configuration"},
            max_concurrent_operations=15,  # Higher concurrency for scaling
            timeout_multiplier=1.5,
            priority_services=["HDFS", "YARN", "HBASE"]  # Priority for scaling
        )
        
    def get_description(self) -> str:
        return ("Scale-up mode optimized for adding capacity. Service shutdowns are "
                "disabled to prevent accidental capacity reduction during scaling operations.")
        
    def get_available_tools(self) -> List[str]:
        return [
            "get_cluster_status",
            "list_services",
            "get_service_info",
            "start_service",
            "restart_service",  # For applying scale-up configs
            "list_hosts",
            "get_host_info", 
            "get_service_components",
            "get_configurations",
            "update_configuration",  # For scaling configs
            "get_request_status",
            "list_recent_requests",
            "health_check",
            "validate_scale_up"  # Mode-specific tool
        ]
        
    def get_context_prompts(self) -> List[str]:
        return [
            "scale_up_planning",
            "capacity_assessment", 
            "resource_allocation",
            "performance_optimization"
        ]
        
    def get_mode_specific_resources(self) -> List[str]:
        return [
            "scaling_best_practices",
            "capacity_planning_guide",
            "performance_tuning_configs"
        ]


class ConfigEditMode(MCPMode):
    """Configuration editing mode - focused on safe configuration management."""
    
    def __init__(self):
        super().__init__(MCPModeType.CONFIG_EDIT)
        
    def _define_restrictions(self) -> ModeRestrictions:
        return ModeRestrictions(
            allowed_operations={
                "get_cluster_status", "list_services", "get_service_info",
                "get_configurations", "update_configuration", "get_request_status",
                "list_recent_requests", "health_check", "list_hosts", "get_host_info"
            },
            denied_operations={"start_service", "stop_service", "restart_service"},
            require_confirmation={"update_configuration"},
            max_concurrent_operations=5,
            timeout_multiplier=1.2
        )
        
    def get_description(self) -> str:
        return ("Configuration editing mode focused on safe configuration management. "
                "Service operations are disabled to prevent conflicts during config changes.")
        
    def get_available_tools(self) -> List[str]:
        return [
            "get_cluster_status",
            "list_services",
            "get_service_info",
            "list_hosts",
            "get_host_info",
            "get_configurations",
            "update_configuration",
            "validate_configuration",  # Mode-specific
            "backup_configuration",   # Mode-specific
            "get_request_status",
            "list_recent_requests", 
            "health_check"
        ]
        
    def get_context_prompts(self) -> List[str]:
        return [
            "configuration_management",
            "config_validation",
            "backup_and_restore",
            "configuration_templates"
        ]
        
    def get_mode_specific_resources(self) -> List[str]:
        return [
            "configuration_templates",
            "validation_rules",
            "backup_procedures",
            "rollback_strategies"
        ]


class DevelopmentMode(MCPMode):
    """Development mode - enhanced logging and debugging capabilities."""
    
    def __init__(self):
        super().__init__(MCPModeType.DEVELOPMENT)
        
    def _define_restrictions(self) -> ModeRestrictions:
        return ModeRestrictions(
            allowed_operations=set(),  # All operations allowed
            denied_operations=set(),
            require_confirmation=set(),  # No confirmations in dev mode
            max_concurrent_operations=20,
            timeout_multiplier=0.5  # Shorter timeouts for faster feedback
        )
        
    def get_description(self) -> str:
        return ("Development mode with enhanced logging and debugging. All operations "
                "are allowed without confirmation for rapid development and testing.")
        
    def get_available_tools(self) -> List[str]:
        return [
            "get_cluster_status",
            "list_services",
            "get_service_info", 
            "start_service",
            "stop_service",
            "restart_service",
            "list_hosts",
            "get_host_info",
            "get_service_components",
            "get_configurations",
            "update_configuration",
            "get_request_status",
            "list_recent_requests",
            "health_check",
            "debug_mode_info",  # Mode-specific
            "simulate_operation"  # Mode-specific
        ]
        
    def get_context_prompts(self) -> List[str]:
        return [
            "development_workflow",
            "debugging_guide",
            "testing_scenarios",
            "api_exploration"
        ]
        
    def get_mode_specific_resources(self) -> List[str]:
        return [
            "api_documentation",
            "debugging_tools",
            "test_scenarios",
            "development_examples"
        ]


class MCPModeManager:
    """Manager for MCP operational modes."""
    
    def __init__(self):
        self._modes = {
            MCPModeType.NORMAL: NormalMode(),
            MCPModeType.CLUSTER_MAINTENANCE: ClusterMaintenanceMode(),
            MCPModeType.SCALE_UP: ScaleUpMode(),
            MCPModeType.CONFIG_EDIT: ConfigEditMode(),
            MCPModeType.DEVELOPMENT: DevelopmentMode()
        }
        self._current_mode = self._modes[MCPModeType.NORMAL]
        
    def switch_mode(self, mode_type: MCPModeType, context: Optional[ModeContext] = None) -> MCPMode:
        """Switch to a different operational mode."""
        if mode_type not in self._modes:
            raise ValueError(f"Unknown mode type: {mode_type}")
            
        self._current_mode = self._modes[mode_type]
        if context:
            self._current_mode.set_context(context)
            
        return self._current_mode
        
    def get_current_mode(self) -> MCPMode:
        """Get the current operational mode."""
        return self._current_mode
        
    def get_available_modes(self) -> Dict[MCPModeType, str]:
        """Get all available modes with descriptions."""
        return {
            mode_type: mode.get_description()
            for mode_type, mode in self._modes.items()
        }
        
    def can_execute_operation(self, operation: str) -> bool:
        """Check if an operation can be executed in the current mode."""
        return self._current_mode.can_execute_operation(operation)
        
    def requires_confirmation(self, operation: str) -> bool:
        """Check if an operation requires confirmation in the current mode."""
        return self._current_mode.requires_confirmation(operation)
        
    def get_operation_timeout(self, base_timeout: int) -> int:
        """Get adjusted timeout for the current mode."""
        return self._current_mode.get_operation_timeout(base_timeout)
        
    def get_mode_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the current mode."""
        mode = self._current_mode
        return {
            "mode_type": mode.mode_type.value,
            "description": mode.get_description(),
            "available_tools": mode.get_available_tools(),
            "context_prompts": mode.get_context_prompts(),
            "mode_specific_resources": mode.get_mode_specific_resources(),
            "restrictions": {
                "allowed_operations": list(mode.restrictions.allowed_operations),
                "denied_operations": list(mode.restrictions.denied_operations),
                "require_confirmation": list(mode.restrictions.require_confirmation),
                "max_concurrent_operations": mode.restrictions.max_concurrent_operations,
                "timeout_multiplier": mode.restrictions.timeout_multiplier,
                "maintenance_mode_required": mode.restrictions.maintenance_mode_required
            },
            "context": {
                "session_id": mode.context.session_id if mode.context else None,
                "user_id": mode.context.user_id if mode.context else None,
                "initiated_at": mode.context.initiated_at if mode.context else None,
                "metadata": mode.context.metadata if mode.context else {}
            }
        } 