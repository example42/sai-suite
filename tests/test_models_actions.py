"""Tests for action models."""

import pytest
from pydantic import ValidationError

from sai.models.actions import ActionFile, Actions, ActionConfig, ActionItem


class TestActionItem:
    """Test ActionItem model."""
    
    def test_simple_action_item(self):
        """Test creating a simple action item."""
        item = ActionItem(name="nginx")
        assert item.name == "nginx"
        assert item.provider is None
        assert item.timeout is None
    
    def test_action_item_with_options(self):
        """Test creating action item with options."""
        item = ActionItem(name="docker", provider="apt", timeout=300)
        assert item.name == "docker"
        assert item.provider == "apt"
        assert item.timeout == 300
    
    def test_action_item_invalid_timeout(self):
        """Test action item with invalid timeout."""
        with pytest.raises(ValidationError):
            ActionItem(name="nginx", timeout=0)
    
    def test_action_item_with_extra_params(self):
        """Test action item with extra parameters."""
        item = ActionItem(name="nginx", provider="apt", version="1.20", force=True, config_file="/etc/nginx.conf")
        assert item.name == "nginx"
        assert item.provider == "apt"
        
        # Test extra parameters
        extra_params = item.get_extra_params()
        assert extra_params["version"] == "1.20"
        assert extra_params["force"] is True
        assert extra_params["config_file"] == "/etc/nginx.conf"
        
        # Standard fields should not be in extra params
        assert "name" not in extra_params
        assert "provider" not in extra_params
        assert "timeout" not in extra_params


class TestActionConfig:
    """Test ActionConfig model."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ActionConfig()
        assert config.verbose is False
        assert config.dry_run is False
        assert config.yes is False
        assert config.quiet is False
        assert config.timeout is None
        assert config.provider is None
        assert config.parallel is False
        assert config.continue_on_error is False
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = ActionConfig(
            verbose=True,
            dry_run=True,
            timeout=300,
            provider="apt",
            parallel=True,
            continue_on_error=True
        )
        assert config.verbose is True
        assert config.dry_run is True
        assert config.timeout == 300
        assert config.provider == "apt"
        assert config.parallel is True
        assert config.continue_on_error is True


class TestActions:
    """Test Actions model."""
    
    def test_empty_actions(self):
        """Test creating empty actions."""
        actions = Actions()
        assert actions.install is None
        assert actions.uninstall is None
        assert actions.start is None
        assert actions.stop is None
        assert actions.restart is None
        assert not actions.has_actions()
    
    def test_install_actions_strings(self):
        """Test install actions with string items."""
        actions = Actions(install=["nginx", "curl"])
        assert actions.install == ["nginx", "curl"]
        assert actions.has_actions()
        
        all_actions = actions.get_all_actions()
        assert len(all_actions) == 2
        assert all_actions[0] == ("install", "nginx")
        assert all_actions[1] == ("install", "curl")
    
    def test_install_actions_mixed(self):
        """Test install actions with mixed string and object items."""
        actions = Actions(install=[
            "nginx",
            {"name": "docker", "provider": "apt"}
        ])
        assert len(actions.install) == 2
        assert actions.install[0] == "nginx"
        # Dict items remain as dicts in the flexible model
        assert isinstance(actions.install[1], dict)
        assert actions.install[1]["name"] == "docker"
        assert actions.install[1]["provider"] == "apt"
        assert actions.has_actions()
    
    def test_multiple_action_types(self):
        """Test multiple action types."""
        actions = Actions(
            install=["nginx"],
            start=["nginx"],
            uninstall=["old-package"]
        )
        assert actions.has_actions()
        
        all_actions = actions.get_all_actions()
        assert len(all_actions) == 3
        
        action_types = [action[0] for action in all_actions]
        assert "install" in action_types
        assert "start" in action_types
        assert "uninstall" in action_types
    
    def test_empty_action_list_validation(self):
        """Test that empty action lists are rejected."""
        with pytest.raises(ValidationError):
            Actions(install=[])


class TestActionFile:
    """Test ActionFile model."""
    
    def test_minimal_action_file(self):
        """Test minimal action file."""
        action_file = ActionFile(actions=Actions(install=["nginx"]))
        assert action_file.config is not None
        assert action_file.actions.install == ["nginx"]
    
    def test_action_file_with_config(self):
        """Test action file with configuration."""
        config = ActionConfig(verbose=True, dry_run=True)
        actions = Actions(install=["nginx", "curl"])
        
        action_file = ActionFile(config=config, actions=actions)
        assert action_file.config.verbose is True
        assert action_file.config.dry_run is True
        assert action_file.actions.install == ["nginx", "curl"]
    
    def test_action_file_no_actions(self):
        """Test action file with no actions fails validation."""
        with pytest.raises(ValidationError):
            ActionFile(actions=Actions())
    
    def test_normalize_action_item(self):
        """Test normalizing action items."""
        action_file = ActionFile(actions=Actions(install=["nginx"]))
        
        # Test string normalization
        item = action_file.normalize_action_item("nginx")
        assert isinstance(item, ActionItem)
        assert item.name == "nginx"
        
        # Test ActionItem passthrough
        original_item = ActionItem(name="docker", provider="apt")
        item = action_file.normalize_action_item(original_item)
        assert item is original_item
    
    def test_get_effective_config_no_global(self):
        """Test getting effective config without global config."""
        config = ActionConfig(verbose=True)
        action_file = ActionFile(config=config, actions=Actions(install=["nginx"]))
        
        effective = action_file.get_effective_config()
        assert effective.verbose is True
    
    def test_get_effective_config_with_global(self):
        """Test getting effective config with global config merge."""
        config = ActionConfig(verbose=True, dry_run=False)
        action_file = ActionFile(config=config, actions=Actions(install=["nginx"]))
        
        global_config = {"dry_run": True, "timeout": 300}
        effective = action_file.get_effective_config(global_config)
        
        # Action file config should take precedence
        assert effective.verbose is True  # From action file
        assert effective.dry_run is False  # From action file (overrides global)
        assert effective.timeout == 300  # From global (not in action file)
    
    def test_flexible_action_types(self):
        """Test that Actions supports any action type."""
        # Test with custom action types
        actions = Actions(
            install=["nginx"],
            deploy=["app1", "app2"],
            backup=["database"],
            custom_action=["item1"]
        )
        
        assert actions.has_actions()
        assert "install" in actions.get_action_types()
        assert "deploy" in actions.get_action_types()
        assert "backup" in actions.get_action_types()
        assert "custom_action" in actions.get_action_types()
        
        all_actions = actions.get_all_actions()
        assert len(all_actions) == 5  # 1 + 2 + 1 + 1 = 5 items
        
        # Test accessing dynamic fields
        assert actions.install == ["nginx"]
        assert actions.deploy == ["app1", "app2"]
        assert actions.backup == ["database"]
        assert actions.custom_action == ["item1"]
    
    def test_normalize_dict_action_item(self):
        """Test normalizing dict action items."""
        action_file = ActionFile(actions=Actions(install=["nginx"]))
        
        # Test dict normalization
        item_dict = {"name": "docker", "provider": "apt", "version": "20.10", "force": True}
        item = action_file.normalize_action_item(item_dict)
        assert isinstance(item, ActionItem)
        assert item.name == "docker"
        assert item.provider == "apt"
        
        # Check extra params
        extra_params = item.get_extra_params()
        assert extra_params["version"] == "20.10"
        assert extra_params["force"] is True