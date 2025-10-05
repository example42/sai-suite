"""Data models for SAI action files."""

import re
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class ActionItem(BaseModel):
    """Individual action item with optional configuration and extra parameters."""

    name: str = Field(..., description="Software or service name")
    provider: Optional[str] = Field(None, description="Specific provider to use")
    timeout: Optional[int] = Field(None, description="Timeout for this specific action", ge=1)

    # Allow any additional fields to be passed through to the action
    model_config = {"extra": "allow"}

    def get_extra_params(self) -> Dict[str, Any]:
        """Get any extra parameters beyond the standard ones."""
        if hasattr(self, "__pydantic_extra__"):
            return dict(self.__pydantic_extra__)
        return {}


class ActionConfig(BaseModel):
    """Configuration options for action execution."""

    verbose: bool = Field(False, description="Enable verbose output")
    dry_run: bool = Field(False, description="Show what would be done without executing")
    yes: bool = Field(False, description="Assume yes for all prompts")
    quiet: bool = Field(False, description="Suppress non-essential output")
    timeout: Optional[int] = Field(None, description="Default timeout in seconds", ge=1)
    provider: Optional[str] = Field(None, description="Force specific provider for all actions")
    parallel: bool = Field(False, description="Execute actions in parallel when possible")
    continue_on_error: bool = Field(
        False, description="Continue executing remaining actions if one fails"
    )

    # Allow additional configuration options
    model_config = {"extra": "allow"}


class Actions(BaseModel):
    """Software management actions to execute - flexible to support any action type."""

    # Allow any action type as a field
    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def validate_action_structure(cls, values):
        """Validate that all action fields are lists and not empty."""
        if not isinstance(values, dict):
            raise ValueError("Actions must be a dictionary")

        # Validate action names follow pattern
        action_name_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

        for action_name, action_list in values.items():
            # Validate action name format
            if not action_name_pattern.match(action_name):
                raise ValueError(
                    f"Invalid action name '{action_name}'. Must start with a letter and contain only letters, numbers, underscores, and hyphens."
                )

            # Validate action list
            if not isinstance(action_list, list):
                raise ValueError(f"Action '{action_name}' must be a list")

            if len(action_list) == 0:
                raise ValueError(f"Action '{action_name}' cannot be empty")

        return values

    def __getattr__(self, name: str) -> Any:
        """Allow access to dynamic action fields."""
        # First check if it's in the extra fields
        if hasattr(self, "__pydantic_extra__") and name in self.__pydantic_extra__:
            return self.__pydantic_extra__[name]
        # Return None for undefined action types (for backward compatibility)
        return None

    def get_all_actions(self) -> List[tuple[str, Union[str, ActionItem]]]:
        """Get all actions as a flat list of (action_type, item) tuples."""
        all_actions = []

        # Get all extra fields (dynamic action types)
        if hasattr(self, "__pydantic_extra__"):
            for action_type, action_list in self.__pydantic_extra__.items():
                if action_list and isinstance(action_list, list):
                    for item in action_list:
                        all_actions.append((action_type, item))

        return all_actions

    def has_actions(self) -> bool:
        """Check if any actions are defined."""
        if hasattr(self, "__pydantic_extra__"):
            return len(self.__pydantic_extra__) > 0 and any(
                action_list and isinstance(action_list, list) and len(action_list) > 0
                for action_list in self.__pydantic_extra__.values()
            )
        return False

    def get_action_types(self) -> List[str]:
        """Get all defined action types."""
        if hasattr(self, "__pydantic_extra__"):
            return [
                action_type
                for action_type, action_list in self.__pydantic_extra__.items()
                if action_list and isinstance(action_list, list) and len(action_list) > 0
            ]
        return []


class ActionFile(BaseModel):
    """Complete action file structure."""

    config: Optional[ActionConfig] = Field(
        default_factory=ActionConfig, description="Configuration options"
    )
    actions: Actions = Field(..., description="Software management actions to execute")

    @field_validator("actions")
    @classmethod
    def validate_actions_not_empty(cls, v):
        """Ensure at least one action is defined."""
        if not v.has_actions():
            raise ValueError("At least one action must be defined")
        return v

    def normalize_action_item(self, item: Union[str, Dict[str, Any], ActionItem]) -> ActionItem:
        """Convert string or dict items to ActionItem objects."""
        if isinstance(item, str):
            return ActionItem(name=item)
        elif isinstance(item, dict):
            return ActionItem(**item)
        elif isinstance(item, ActionItem):
            return item
        else:
            raise ValueError(f"Invalid action item type: {type(item)}")

    def get_effective_config(self, global_config: Optional[Dict[str, Any]] = None) -> ActionConfig:
        """Get effective configuration by merging with global config."""
        if global_config is None:
            return self.config

        # Merge configurations, with action file config taking precedence
        merged_config = global_config.copy()
        if self.config:
            merged_config.update(self.config.model_dump(exclude_unset=True))

        return ActionConfig(**merged_config)
