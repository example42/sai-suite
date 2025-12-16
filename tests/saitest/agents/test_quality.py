"""Tests for quality check agent."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from saitest.agents.quality import quality_check_agent, _validate_against_schema
from saitest.core.state import create_initial_state
from saitest.models.state import PlatformResult


@pytest.mark.asyncio
async def test_quality_check_agent_no_saidata():
    """Test quality check agent when no saidata is generated."""
    state = create_initial_state("nginx")
    state["generated_saidata"] = None
    
    result = await quality_check_agent(state)
    
    assert result["validation_errors"] == ["No generated saidata available"]
    assert result["completeness_score"] == 0.0
    assert result["accuracy_score"] == 0.0
    assert result["overall_confidence"] == 0.0
    assert result["needs_human_review"] is True


@pytest.mark.asyncio
async def test_quality_check_agent_with_valid_saidata():
    """Test quality check agent with valid saidata."""
    state = create_initial_state("nginx")
    
    # Create valid saidata
    state["generated_saidata"] = {
        "default": {
            "version": "0.3",
            "metadata": {
                "name": "nginx",
                "description": "High-performance HTTP server"
            },
            "packages": [
                {
                    "name": "nginx",
                    "package_name": "nginx"
                }
            ]
        },
        "overrides": {}
    }
    
    # Mock LLM response
    mock_llm_response = Mock()
    mock_llm_response.content = '''```json
{
    "completeness": 0.85,
    "accuracy": 0.90,
    "overall": 0.87,
    "reasoning": "Good coverage of basic resources"
}
```'''
    
    with patch('saitest.agents.quality.ChatOpenAI') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm
        
        result = await quality_check_agent(state)
    
    assert result["completeness_score"] == 0.85
    assert result["accuracy_score"] == 0.90
    assert result["overall_confidence"] == 0.87
    assert result["needs_human_review"] is False  # Above 0.7 threshold


@pytest.mark.asyncio
async def test_quality_check_agent_low_confidence():
    """Test quality check agent with low confidence score."""
    state = create_initial_state("nginx")
    
    state["generated_saidata"] = {
        "default": {
            "version": "0.3",
            "metadata": {"name": "nginx"}
        },
        "overrides": {}
    }
    
    # Mock LLM response with low confidence
    mock_llm_response = Mock()
    mock_llm_response.content = '''```json
{
    "completeness": 0.50,
    "accuracy": 0.60,
    "overall": 0.55,
    "reasoning": "Missing important resources"
}
```'''
    
    with patch('saitest.agents.quality.ChatOpenAI') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm
        
        result = await quality_check_agent(state)
    
    assert result["overall_confidence"] == 0.55
    assert result["needs_human_review"] is True  # Below 0.7 threshold


@pytest.mark.asyncio
async def test_quality_check_agent_with_validation_errors():
    """Test quality check agent when schema validation fails."""
    state = create_initial_state("nginx")
    
    # Create invalid saidata (missing required fields)
    state["generated_saidata"] = {
        "default": {
            "version": "0.3",
            # Missing metadata
            "packages": []
        },
        "overrides": {}
    }
    
    # Mock LLM response with good scores
    mock_llm_response = Mock()
    mock_llm_response.content = '''```json
{
    "completeness": 0.85,
    "accuracy": 0.90,
    "overall": 0.87,
    "reasoning": "Good structure"
}
```'''
    
    with patch('saitest.agents.quality.ChatOpenAI') as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm
        
        result = await quality_check_agent(state)
    
    # Should need human review due to validation errors
    assert len(result["validation_errors"]) > 0
    assert result["needs_human_review"] is True


@pytest.mark.asyncio
async def test_validate_against_schema_valid():
    """Test schema validation with valid saidata."""
    saidata = {
        "default": {
            "version": "0.3",
            "metadata": {
                "name": "nginx",
                "description": "Test"
            },
            "packages": [
                {
                    "name": "nginx",
                    "package_name": "nginx"
                }
            ]
        },
        "overrides": {}
    }
    
    errors = await _validate_against_schema(saidata)
    
    # Should have no errors for valid saidata
    assert isinstance(errors, list)


@pytest.mark.asyncio
async def test_validate_against_schema_invalid():
    """Test schema validation with invalid saidata."""
    saidata = {
        "default": {
            "version": "invalid_version",  # Invalid version format
            # Missing metadata
        },
        "overrides": {}
    }
    
    errors = await _validate_against_schema(saidata)
    
    # Should have validation errors
    assert len(errors) > 0
    assert any("metadata" in error.lower() or "version" in error.lower() for error in errors)
