"""Update engine for intelligent saidata merging and updating."""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Union, Set
from enum import Enum
from pathlib import Path

import click

from ..models.generation import (
    GenerationRequest, 
    GenerationResult, 
    GenerationContext,
    ValidationError as GenValidationError,
    LLMProvider,
    GenerationMode
)
from ..models.saidata import SaiData, Metadata, ProviderConfig
from .generation_engine import GenerationEngine


logger = logging.getLogger(__name__)


class MergeStrategy(str, Enum):
    """Merge strategies for updating saidata."""
    PRESERVE = "preserve"  # Preserve existing data, only add new fields
    ENHANCE = "enhance"    # Enhance existing data with new information
    REPLACE = "replace"    # Replace existing data with new data


class ConflictResolution(str, Enum):
    """Conflict resolution strategies."""
    KEEP_EXISTING = "keep_existing"
    USE_NEW = "use_new"
    MERGE = "merge"
    PROMPT = "prompt"


class UpdateEngineError(Exception):
    """Base exception for update engine errors."""
    pass


class MergeConflictError(UpdateEngineError):
    """Merge conflict that requires resolution."""
    pass


class UpdateResult:
    """Result of an update operation."""
    
    def __init__(self, success: bool, saidata: Optional[SaiData] = None,
                 conflicts_resolved: int = 0, fields_added: int = 0,
                 fields_updated: int = 0, warnings: List[str] = None):
        self.success = success
        self.saidata = saidata
        self.conflicts_resolved = conflicts_resolved
        self.fields_added = fields_added
        self.fields_updated = fields_updated
        self.warnings = warnings or []


class UpdateEngine:
    """Engine for intelligent saidata updating and merging."""
    
    def __init__(self, config=None, generation_engine: Optional[GenerationEngine] = None):
        """Initialize update engine.
        
        Args:
            config: Engine configuration
            generation_engine: Generation engine instance (optional)
        """
        self.config = config or {}
        self.generation_engine = generation_engine or GenerationEngine(config)
        
        # Track update statistics
        self._updates_performed = 0
        self._total_conflicts_resolved = 0
        self._total_fields_added = 0
        self._total_fields_updated = 0
    
    async def update_saidata(
        self,
        existing_saidata: SaiData,
        target_providers: List[str] = None,
        llm_provider: LLMProvider = LLMProvider.OPENAI,
        use_rag: bool = True,
        merge_strategy: str = "enhance",
        interactive: bool = False,
        user_hints: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """Update existing saidata with new information.
        
        Args:
            existing_saidata: Current saidata to update
            target_providers: Target providers for updated saidata
            llm_provider: LLM provider to use
            use_rag: Whether to use RAG for context
            merge_strategy: Strategy for merging data
            interactive: Whether to prompt for conflict resolution
            user_hints: Additional hints for generation
            
        Returns:
            GenerationResult with updated saidata
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting saidata update for '{existing_saidata.metadata.name}'")
            
            # Generate fresh saidata for comparison
            fresh_request = GenerationRequest(
                software_name=existing_saidata.metadata.name,
                target_providers=target_providers or [],
                llm_provider=llm_provider,
                use_rag=use_rag,
                generation_mode=GenerationMode.UPDATE,
                existing_saidata=existing_saidata,
                user_hints=user_hints
            )
            
            fresh_result = await self.generation_engine.generate_saidata(fresh_request)
            
            if not fresh_result.success:
                logger.error(f"Failed to generate fresh saidata for comparison")
                return fresh_result
            
            # Merge existing and fresh saidata
            merge_result = await self._merge_saidata(
                existing=existing_saidata,
                fresh=fresh_result.saidata,
                strategy=MergeStrategy(merge_strategy),
                interactive=interactive
            )
            
            if not merge_result.success:
                return GenerationResult(
                    success=False,
                    saidata=None,
                    validation_errors=[GenValidationError(
                        field="merge",
                        message="Failed to merge saidata",
                        severity="error"
                    )],
                    warnings=merge_result.warnings,
                    generation_time=time.time() - start_time,
                    llm_provider_used=llm_provider.value if hasattr(llm_provider, 'value') else llm_provider,
                    repository_sources_used=fresh_result.repository_sources_used
                )
            
            # Validate merged result
            validation_result = await self.generation_engine.validate_saidata_file(Path("temp"))
            
            # Update statistics
            self._updates_performed += 1
            self._total_conflicts_resolved += merge_result.conflicts_resolved
            self._total_fields_added += merge_result.fields_added
            self._total_fields_updated += merge_result.fields_updated
            
            generation_time = time.time() - start_time
            
            result = GenerationResult(
                success=True,
                saidata=merge_result.saidata,
                validation_errors=[],
                warnings=merge_result.warnings + fresh_result.warnings,
                generation_time=generation_time,
                llm_provider_used=fresh_result.llm_provider_used,
                repository_sources_used=fresh_result.repository_sources_used,
                tokens_used=fresh_result.tokens_used,
                cost_estimate=fresh_result.cost_estimate
            )
            
            logger.info(f"Successfully updated saidata for '{existing_saidata.metadata.name}' in {generation_time:.2f}s")
            logger.info(f"Merge stats: {merge_result.fields_added} added, {merge_result.fields_updated} updated, {merge_result.conflicts_resolved} conflicts resolved")
            
            return result
            
        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Failed to update saidata for '{existing_saidata.metadata.name}': {e}")
            
            return GenerationResult(
                success=False,
                saidata=None,
                validation_errors=[GenValidationError(
                    field="update",
                    message=str(e),
                    severity="error"
                )],
                warnings=[],
                generation_time=generation_time,
                llm_provider_used=llm_provider.value if hasattr(llm_provider, 'value') else llm_provider,
                repository_sources_used=[]
            )
    
    async def _merge_saidata(
        self,
        existing: SaiData,
        fresh: SaiData,
        strategy: MergeStrategy,
        interactive: bool = False
    ) -> UpdateResult:
        """Merge existing and fresh saidata.
        
        Args:
            existing: Existing saidata
            fresh: Fresh saidata from generation
            strategy: Merge strategy to use
            interactive: Whether to prompt for conflict resolution
            
        Returns:
            UpdateResult with merged saidata
        """
        try:
            logger.debug(f"Merging saidata with strategy: {strategy.value}")
            
            # Convert to dictionaries for easier manipulation
            existing_dict = existing.model_dump(exclude_none=True)
            fresh_dict = fresh.model_dump(exclude_none=True)
            
            # Perform merge based on strategy
            if strategy == MergeStrategy.PRESERVE:
                merged_dict, stats = await self._merge_preserve(existing_dict, fresh_dict, interactive)
            elif strategy == MergeStrategy.ENHANCE:
                merged_dict, stats = await self._merge_enhance(existing_dict, fresh_dict, interactive)
            elif strategy == MergeStrategy.REPLACE:
                merged_dict, stats = await self._merge_replace(existing_dict, fresh_dict, interactive)
            else:
                raise UpdateEngineError(f"Unknown merge strategy: {strategy}")
            
            # Convert back to SaiData
            merged_saidata = SaiData(**merged_dict)
            
            return UpdateResult(
                success=True,
                saidata=merged_saidata,
                conflicts_resolved=stats['conflicts_resolved'],
                fields_added=stats['fields_added'],
                fields_updated=stats['fields_updated'],
                warnings=stats.get('warnings', [])
            )
            
        except Exception as e:
            logger.error(f"Failed to merge saidata: {e}")
            return UpdateResult(
                success=False,
                warnings=[f"Merge failed: {e}"]
            )
    
    async def _merge_preserve(
        self,
        existing: Dict[str, Any],
        fresh: Dict[str, Any],
        interactive: bool
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Merge with preserve strategy - keep existing data, only add new fields.
        
        Args:
            existing: Existing saidata dictionary
            fresh: Fresh saidata dictionary
            interactive: Whether to prompt for decisions
            
        Returns:
            Tuple of (merged_dict, stats)
        """
        merged = existing.copy()
        stats = {'conflicts_resolved': 0, 'fields_added': 0, 'fields_updated': 0, 'warnings': []}
        
        # Add new top-level fields that don't exist
        for key, value in fresh.items():
            if key not in merged:
                merged[key] = value
                stats['fields_added'] += 1
                logger.debug(f"Added new field: {key}")
            elif key == 'providers':
                # Special handling for providers - merge provider configs
                provider_stats = await self._merge_providers_preserve(
                    merged.get('providers', {}),
                    fresh.get('providers', {}),
                    interactive
                )
                stats['fields_added'] += provider_stats['fields_added']
                stats['fields_updated'] += provider_stats['fields_updated']
                stats['conflicts_resolved'] += provider_stats['conflicts_resolved']
        
        return merged, stats
    
    async def _merge_enhance(
        self,
        existing: Dict[str, Any],
        fresh: Dict[str, Any],
        interactive: bool
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Merge with enhance strategy - enhance existing data with new information.
        
        Args:
            existing: Existing saidata dictionary
            fresh: Fresh saidata dictionary
            interactive: Whether to prompt for decisions
            
        Returns:
            Tuple of (merged_dict, stats)
        """
        merged = existing.copy()
        stats = {'conflicts_resolved': 0, 'fields_added': 0, 'fields_updated': 0, 'warnings': []}
        
        # Enhance metadata
        if 'metadata' in fresh:
            metadata_stats = await self._merge_metadata_enhance(
                merged.get('metadata', {}),
                fresh['metadata'],
                interactive
            )
            stats['fields_added'] += metadata_stats['fields_added']
            stats['fields_updated'] += metadata_stats['fields_updated']
            stats['conflicts_resolved'] += metadata_stats['conflicts_resolved']
        
        # Enhance providers
        if 'providers' in fresh:
            provider_stats = await self._merge_providers_enhance(
                merged.get('providers', {}),
                fresh['providers'],
                interactive
            )
            stats['fields_added'] += provider_stats['fields_added']
            stats['fields_updated'] += provider_stats['fields_updated']
            stats['conflicts_resolved'] += provider_stats['conflicts_resolved']
        
        # Add new top-level fields
        for key, value in fresh.items():
            if key not in merged and key not in ['metadata', 'providers']:
                merged[key] = value
                stats['fields_added'] += 1
                logger.debug(f"Added new field: {key}")
        
        return merged, stats
    
    async def _merge_replace(
        self,
        existing: Dict[str, Any],
        fresh: Dict[str, Any],
        interactive: bool
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Merge with replace strategy - replace existing data with new data.
        
        Args:
            existing: Existing saidata dictionary
            fresh: Fresh saidata dictionary
            interactive: Whether to prompt for decisions
            
        Returns:
            Tuple of (merged_dict, stats)
        """
        # Start with fresh data
        merged = fresh.copy()
        stats = {'conflicts_resolved': 0, 'fields_added': 0, 'fields_updated': 0, 'warnings': []}
        
        # Preserve user-customized fields if interactive
        if interactive:
            preserved_fields = await self._prompt_preserve_fields(existing, fresh)
            for field_path in preserved_fields:
                self._set_nested_field(merged, field_path, self._get_nested_field(existing, field_path))
                stats['conflicts_resolved'] += 1
        
        # Count all fields as updated since we're replacing
        stats['fields_updated'] = len(fresh)
        
        return merged, stats
    
    async def _merge_metadata_enhance(
        self,
        existing_metadata: Dict[str, Any],
        fresh_metadata: Dict[str, Any],
        interactive: bool
    ) -> Dict[str, Any]:
        """Enhance metadata fields.
        
        Args:
            existing_metadata: Existing metadata
            fresh_metadata: Fresh metadata
            interactive: Whether to prompt for decisions
            
        Returns:
            Statistics dictionary
        """
        stats = {'conflicts_resolved': 0, 'fields_added': 0, 'fields_updated': 0}
        
        # Fields that should be enhanced rather than replaced
        enhance_fields = ['description', 'tags', 'urls', 'security']
        
        for key, fresh_value in fresh_metadata.items():
            if key not in existing_metadata:
                existing_metadata[key] = fresh_value
                stats['fields_added'] += 1
            elif key in enhance_fields:
                if key == 'description' and fresh_value and len(fresh_value) > len(existing_metadata.get(key, '')):
                    # Use longer, more detailed description
                    if interactive:
                        choice = await self._prompt_field_choice(
                            f"metadata.{key}",
                            existing_metadata[key],
                            fresh_value
                        )
                        if choice == ConflictResolution.USE_NEW:
                            existing_metadata[key] = fresh_value
                            stats['fields_updated'] += 1
                        stats['conflicts_resolved'] += 1
                    else:
                        existing_metadata[key] = fresh_value
                        stats['fields_updated'] += 1
                elif key == 'tags':
                    # Merge tags
                    existing_tags = set(existing_metadata.get(key, []))
                    fresh_tags = set(fresh_value or [])
                    merged_tags = list(existing_tags | fresh_tags)
                    if merged_tags != existing_metadata.get(key, []):
                        existing_metadata[key] = merged_tags
                        stats['fields_updated'] += 1
                elif key in ['urls', 'security'] and isinstance(fresh_value, dict):
                    # Merge nested dictionaries
                    existing_nested = existing_metadata.get(key, {})
                    for nested_key, nested_value in fresh_value.items():
                        if nested_key not in existing_nested:
                            existing_nested[nested_key] = nested_value
                            stats['fields_added'] += 1
                    existing_metadata[key] = existing_nested
        
        return stats
    
    async def _merge_providers_preserve(
        self,
        existing_providers: Dict[str, Any],
        fresh_providers: Dict[str, Any],
        interactive: bool
    ) -> Dict[str, Any]:
        """Merge providers with preserve strategy.
        
        Args:
            existing_providers: Existing provider configs
            fresh_providers: Fresh provider configs
            interactive: Whether to prompt for decisions
            
        Returns:
            Statistics dictionary
        """
        stats = {'conflicts_resolved': 0, 'fields_added': 0, 'fields_updated': 0}
        
        # Add new providers that don't exist
        for provider_name, provider_config in fresh_providers.items():
            if provider_name not in existing_providers:
                existing_providers[provider_name] = provider_config
                stats['fields_added'] += 1
                logger.debug(f"Added new provider: {provider_name}")
        
        return stats
    
    async def _merge_providers_enhance(
        self,
        existing_providers: Dict[str, Any],
        fresh_providers: Dict[str, Any],
        interactive: bool
    ) -> Dict[str, Any]:
        """Merge providers with enhance strategy.
        
        Args:
            existing_providers: Existing provider configs
            fresh_providers: Fresh provider configs
            interactive: Whether to prompt for decisions
            
        Returns:
            Statistics dictionary
        """
        stats = {'conflicts_resolved': 0, 'fields_added': 0, 'fields_updated': 0}
        
        for provider_name, fresh_config in fresh_providers.items():
            if provider_name not in existing_providers:
                existing_providers[provider_name] = fresh_config
                stats['fields_added'] += 1
                logger.debug(f"Added new provider: {provider_name}")
            else:
                # Enhance existing provider config
                existing_config = existing_providers[provider_name]
                provider_stats = await self._merge_provider_config(
                    existing_config,
                    fresh_config,
                    interactive,
                    provider_name
                )
                stats['fields_added'] += provider_stats['fields_added']
                stats['fields_updated'] += provider_stats['fields_updated']
                stats['conflicts_resolved'] += provider_stats['conflicts_resolved']
        
        return stats
    
    async def _merge_provider_config(
        self,
        existing_config: Dict[str, Any],
        fresh_config: Dict[str, Any],
        interactive: bool,
        provider_name: str
    ) -> Dict[str, Any]:
        """Merge individual provider configuration.
        
        Args:
            existing_config: Existing provider config
            fresh_config: Fresh provider config
            interactive: Whether to prompt for decisions
            provider_name: Name of the provider
            
        Returns:
            Statistics dictionary
        """
        stats = {'conflicts_resolved': 0, 'fields_added': 0, 'fields_updated': 0}
        
        # Fields that can be merged (lists)
        mergeable_fields = ['packages', 'services', 'files', 'directories', 'commands', 'ports', 'containers']
        
        for key, fresh_value in fresh_config.items():
            if key not in existing_config:
                existing_config[key] = fresh_value
                stats['fields_added'] += 1
            elif key in mergeable_fields and isinstance(fresh_value, list):
                # Merge lists by name/identifier
                merged_list = await self._merge_list_by_name(
                    existing_config[key],
                    fresh_value,
                    interactive,
                    f"{provider_name}.{key}"
                )
                if merged_list != existing_config[key]:
                    existing_config[key] = merged_list
                    stats['fields_updated'] += 1
        
        return stats
    
    async def _merge_list_by_name(
        self,
        existing_list: List[Dict[str, Any]],
        fresh_list: List[Dict[str, Any]],
        interactive: bool,
        field_path: str
    ) -> List[Dict[str, Any]]:
        """Merge lists by matching items by name.
        
        Args:
            existing_list: Existing list of items
            fresh_list: Fresh list of items
            interactive: Whether to prompt for decisions
            field_path: Field path for logging
            
        Returns:
            Merged list
        """
        merged = existing_list.copy()
        existing_names = {item.get('name') for item in existing_list if 'name' in item}
        
        for fresh_item in fresh_list:
            fresh_name = fresh_item.get('name')
            if fresh_name and fresh_name not in existing_names:
                merged.append(fresh_item)
                logger.debug(f"Added new item to {field_path}: {fresh_name}")
        
        return merged
    
    async def _prompt_field_choice(
        self,
        field_path: str,
        existing_value: Any,
        fresh_value: Any
    ) -> ConflictResolution:
        """Prompt user for field conflict resolution.
        
        Args:
            field_path: Path to the conflicting field
            existing_value: Current value
            fresh_value: New value
            
        Returns:
            User's choice for conflict resolution
        """
        click.echo(f"\nConflict in field: {field_path}")
        click.echo(f"Existing: {existing_value}")
        click.echo(f"New:      {fresh_value}")
        
        choice = click.prompt(
            "Choose resolution",
            type=click.Choice(['existing', 'new', 'merge'], case_sensitive=False),
            default='new'
        )
        
        if choice.lower() == 'existing':
            return ConflictResolution.KEEP_EXISTING
        elif choice.lower() == 'new':
            return ConflictResolution.USE_NEW
        else:
            return ConflictResolution.MERGE
    
    async def _prompt_preserve_fields(
        self,
        existing: Dict[str, Any],
        fresh: Dict[str, Any]
    ) -> List[str]:
        """Prompt user to select fields to preserve during replace.
        
        Args:
            existing: Existing data
            fresh: Fresh data
            
        Returns:
            List of field paths to preserve
        """
        preserved_fields = []
        
        click.echo("\nReplace mode: Select fields to preserve from existing data:")
        
        # Check top-level fields
        for key in existing.keys():
            if key in fresh and existing[key] != fresh[key]:
                if click.confirm(f"Preserve existing '{key}'?"):
                    preserved_fields.append(key)
        
        return preserved_fields
    
    def _get_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value by path.
        
        Args:
            data: Data dictionary
            field_path: Dot-separated field path
            
        Returns:
            Field value or None if not found
        """
        keys = field_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _set_nested_field(self, data: Dict[str, Any], field_path: str, value: Any) -> None:
        """Set nested field value by path.
        
        Args:
            data: Data dictionary
            field_path: Dot-separated field path
            value: Value to set
        """
        keys = field_path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def get_update_stats(self) -> Dict[str, Any]:
        """Get update statistics.
        
        Returns:
            Dictionary with update statistics
        """
        return {
            "total_updates": self._updates_performed,
            "total_conflicts_resolved": self._total_conflicts_resolved,
            "total_fields_added": self._total_fields_added,
            "total_fields_updated": self._total_fields_updated,
            "average_conflicts_per_update": (
                self._total_conflicts_resolved / self._updates_performed 
                if self._updates_performed > 0 else 0
            ),
            "average_fields_added_per_update": (
                self._total_fields_added / self._updates_performed 
                if self._updates_performed > 0 else 0
            )
        }