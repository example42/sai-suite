"""Data models for SAI action files."""

from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


class ActionItem(BaseModel):
    """Individual action item with optional configuration."""
    name: str = Field(..., description="Software or service name")
    provider: Optional[str] = Field(None, description="Specific provider to use")
    timeout: Optional[int] = Field(None, description="Timeout for this specific action", ge=1)


class ActionConfig(BaseModel):
    """Configuration options for action execution."""
    verbose: bool = Field(False, description="Enable verbose output")
    dry_run: bool = Field(False, description="Show what would be done without executing")
    yes: bool = Field(False, description="Assume yes for all prompts")
    quiet: bool = Field(False, description="Suppress non-essential output")
    timeout: Optional[int] = Field(None, description="Default timeout in seconds", ge=1)
    provider: Optional[str] = Field(None, description="Force specific provider for all actions")
    parallel: bool = Field(False, description="Execute actions in parallel when possible")
    continue_on_error: bool = Field(False, description="Continue executing remaining actions if one fails")


class Actions(BaseModel):
    """Software management actions to execute."""
    install: Optional[List[Union[str, ActionItem]]] = Field(None, description="Software packages to install")
    uninstall: Optional[List[Union[str, ActionItem]]] = Field(None, description="Software packages to uninstall")
    start: Optional[List[Union[str, ActionItem]]] = Field(None, description="Services to start")
    stop: Optional[List[Union[str, ActionItem]]] = Field(None, description="Services to stop")
    restart: Optional[List[Union[str, ActionItem]]] = Field(None, description="Services to restart")

    @field_validator('install', 'uninstall', 'start', 'stop', 'restart', mode='before')
    @classmethod
    def validate_action_lists(cls, v):
        """Ensure action lists are not empty if provided."""
        if v is not None and len(v) == 0:
            raise ValueError("Action lists cannot be empty")
        return v

    def get_all_actions(self) -> List[tuple[str, Union[str, ActionItem]]]:
        """Get all actions as a flat list of (action_type, item) tuples."""
        all_actions = []
        
        for action_type in ['install', 'uninstall', 'start', 'stop', 'restart']:
            action_list = getattr(self, action_type)
            if action_list:
                for item in action_list:
                    all_actions.append((action_type, item))
        
        return all_actions

    def has_actions(self) -> bool:
        """Check if any actions are defined."""
        return any([
            self.install,
            self.uninstall, 
            self.start,
            self.stop,
            self.restart
        ])


class ActionFile(BaseModel):
    """Complete action file structure."""
    config: Optional[ActionConfig] = Field(default_factory=ActionConfig, description="Configuration options")
    actions: Actions = Field(..., description="Software management actions to execute")

    @field_validator('actions')
    @classmethod
    def validate_actions_not_empty(cls, v):
        """Ensure at least one action is defined."""
        if not v.has_actions():
            raise ValueError("At least one action must be defined")
        return v

    def normalize_action_item(self, item: Union[str, ActionItem]) -> ActionItem:
        """Convert string items to ActionItem objects."""
        if isinstance(item, str):
            return ActionItem(name=item)
        return item

    def get_effective_config(self, global_config: Optional[Dict[str, Any]] = None) -> ActionConfig:
        """Get effective configuration by merging with global config."""
        if global_config is None:
            return self.config
        
        # Merge configurations, with action file config taking precedence
        merged_config = global_config.copy()
        if self.config:
            merged_config.update(self.config.model_dump(exclude_unset=True))
        
        return ActionConfig(**merged_config)