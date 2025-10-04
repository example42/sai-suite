"""RAG (Retrieval-Augmented Generation) indexer for semantic search."""

import asyncio
import json
import pickle
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Union, TYPE_CHECKING
from datetime import datetime, timedelta

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import faiss
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    np = None
    SentenceTransformer = None
    faiss = None

if TYPE_CHECKING:
    import faiss

from ..models.repository import RepositoryPackage, SearchResult
from ..models.saidata import SaiData
from ..utils.errors import RAGError


logger = logging.getLogger(__name__)


class RAGIndexer:
    """RAG indexer with vector embedding support for semantic search."""
    
    def __init__(
        self,
        index_dir: Union[str, Path],
        model_name: str = "all-MiniLM-L6-v2",
        max_sequence_length: int = 512
    ):
        """Initialize RAG indexer.
        
        Args:
            index_dir: Directory to store index files
            model_name: Sentence transformer model name
            max_sequence_length: Maximum sequence length for embeddings
            
        Raises:
            RAGError: If RAG dependencies are not available
        """
        if not RAG_AVAILABLE:
            raise RAGError(
                "RAG dependencies not available. Install with: pip install sai[rag]"
            )
        
        self.index_dir = Path(index_dir)
        self.model_name = model_name
        self.max_sequence_length = max_sequence_length
        
        # Create index directory
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize model (lazy loading)
        self._model: Optional[SentenceTransformer] = None
        self._model_lock = asyncio.Lock()
        
        # Index storage
        self._package_index: Optional["faiss.Index"] = None
        self._package_metadata: List[Dict[str, Any]] = []
        self._saidata_index: Optional["faiss.Index"] = None
        self._saidata_metadata: List[Dict[str, Any]] = []
        
        # Index file paths
        self._package_index_path = self.index_dir / "packages.faiss"
        self._package_metadata_path = self.index_dir / "packages_metadata.pkl"
        self._saidata_index_path = self.index_dir / "saidata.faiss"
        self._saidata_metadata_path = self.index_dir / "saidata_metadata.pkl"
        self._model_info_path = self.index_dir / "model_info.json"
    
    async def _get_model(self) -> SentenceTransformer:
        """Get or initialize the sentence transformer model."""
        if self._model is None:
            async with self._model_lock:
                if self._model is None:
                    logger.info(f"Loading sentence transformer model: {self.model_name}")
                    # Run model loading in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    self._model = await loop.run_in_executor(
                        None,
                        lambda: SentenceTransformer(
                            self.model_name,
                            device='cpu'  # Use CPU for better compatibility
                        )
                    )
                    # Set max sequence length
                    self._model.max_seq_length = self.max_sequence_length
                    logger.info("Model loaded successfully")
        
        return self._model
    
    def _create_package_text(self, package: RepositoryPackage) -> str:
        """Create searchable text representation of a package.
        
        Args:
            package: Repository package
            
        Returns:
            Text representation for embedding
        """
        text_parts = [package.name]
        
        if package.description:
            text_parts.append(package.description)
        
        if package.category:
            text_parts.append(f"category: {package.category}")
        
        if package.tags:
            text_parts.append(f"tags: {' '.join(package.tags)}")
        
        if package.maintainer:
            text_parts.append(f"maintainer: {package.maintainer}")
        
        # Add repository and platform context
        text_parts.append(f"repository: {package.repository_name}")
        text_parts.append(f"platform: {package.platform}")
        
        return " ".join(text_parts)
    
    def _create_saidata_text(self, saidata: SaiData) -> str:
        """Create searchable text representation of saidata.
        
        Args:
            saidata: SaiData object
            
        Returns:
            Text representation for embedding
        """
        text_parts = [saidata.metadata.name]
        
        if saidata.metadata.display_name:
            text_parts.append(saidata.metadata.display_name)
        
        if saidata.metadata.description:
            text_parts.append(saidata.metadata.description)
        
        if saidata.metadata.category:
            text_parts.append(f"category: {saidata.metadata.category}")
        
        if saidata.metadata.subcategory:
            text_parts.append(f"subcategory: {saidata.metadata.subcategory}")
        
        if saidata.metadata.tags:
            text_parts.append(f"tags: {' '.join(saidata.metadata.tags)}")
        
        if saidata.metadata.language:
            text_parts.append(f"language: {saidata.metadata.language}")
        
        # Add provider information
        if saidata.providers:
            providers = list(saidata.providers.keys())
            text_parts.append(f"providers: {' '.join(providers)}")
        
        # Add package names from providers
        if saidata.providers:
            package_names = []
            for provider_config in saidata.providers.values():
                if provider_config.packages:
                    for pkg in provider_config.packages:
                        package_names.append(pkg.name)
            if package_names:
                text_parts.append(f"packages: {' '.join(package_names)}")
        
        return " ".join(text_parts)
    
    async def index_repository_data(self, packages: List[RepositoryPackage]) -> None:
        """Index repository data for semantic search.
        
        Args:
            packages: List of repository packages to index
        """
        if not packages:
            logger.warning("No packages provided for indexing")
            return
        
        logger.info(f"Indexing {len(packages)} repository packages")
        
        # Get model
        model = await self._get_model()
        
        # Create text representations
        texts = [self._create_package_text(pkg) for pkg in packages]
        
        # Generate embeddings in batches to manage memory
        batch_size = 100
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
            
            # Run embedding generation in thread pool
            loop = asyncio.get_event_loop()
            batch_embeddings = await loop.run_in_executor(
                None,
                lambda: model.encode(batch_texts, convert_to_numpy=True, show_progress_bar=False)
            )
            embeddings.append(batch_embeddings)
        
        # Combine all embeddings
        all_embeddings = np.vstack(embeddings)
        
        # Create FAISS index
        dimension = all_embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(all_embeddings)
        index.add(all_embeddings)
        
        # Store metadata
        metadata = []
        for pkg in packages:
            metadata.append({
                'name': pkg.name,
                'version': pkg.version,
                'description': pkg.description,
                'repository_name': pkg.repository_name,
                'platform': pkg.platform,
                'category': pkg.category,
                'tags': pkg.tags,
                'homepage': pkg.homepage,
                'maintainer': pkg.maintainer,
                'license': pkg.license,
                'last_updated': pkg.last_updated.isoformat() if pkg.last_updated else None
            })
        
        # Save index and metadata
        await self._save_package_index(index, metadata)
        
        logger.info(f"Successfully indexed {len(packages)} packages")
    
    async def index_existing_saidata(self, saidata_files: List[Path]) -> None:
        """Index existing saidata files for similarity search.
        
        Args:
            saidata_files: List of paths to saidata files
        """
        if not saidata_files:
            logger.warning("No saidata files provided for indexing")
            return
        
        logger.info(f"Indexing {len(saidata_files)} saidata files")
        
        # Load and parse saidata files
        saidata_objects = []
        valid_files = []
        
        for file_path in saidata_files:
            try:
                # Load saidata file
                import yaml
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                # Parse as SaiData
                saidata = SaiData(**data)
                saidata_objects.append(saidata)
                valid_files.append(file_path)
                
            except Exception as e:
                logger.warning(f"Failed to load saidata from {file_path}: {e}")
                continue
        
        if not saidata_objects:
            logger.warning("No valid saidata files found")
            return
        
        # Get model
        model = await self._get_model()
        
        # Create text representations
        texts = [self._create_saidata_text(saidata) for saidata in saidata_objects]
        
        # Generate embeddings
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        )
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        
        # Store metadata
        metadata = []
        for i, (saidata, file_path) in enumerate(zip(saidata_objects, valid_files)):
            metadata.append({
                'name': saidata.metadata.name,
                'display_name': saidata.metadata.display_name,
                'description': saidata.metadata.description,
                'category': saidata.metadata.category,
                'subcategory': saidata.metadata.subcategory,
                'tags': saidata.metadata.tags,
                'version': saidata.metadata.version,
                'license': saidata.metadata.license,
                'language': saidata.metadata.language,
                'providers': list(saidata.providers.keys()) if saidata.providers else [],
                'file_path': str(file_path),
                'indexed_at': datetime.utcnow().isoformat()
            })
        
        # Save index and metadata
        await self._save_saidata_index(index, metadata)
        
        logger.info(f"Successfully indexed {len(saidata_objects)} saidata files")
    
    async def search_similar_packages(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.3
    ) -> List[RepositoryPackage]:
        """Find similar packages using semantic search.
        
        Args:
            query: Search query
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of similar repository packages
        """
        # Load package index if not loaded
        if self._package_index is None:
            await self._load_package_index()
        
        if self._package_index is None or not self._package_metadata:
            logger.warning("Package index not available")
            return []
        
        # Get model and generate query embedding
        model = await self._get_model()
        
        loop = asyncio.get_event_loop()
        query_embedding = await loop.run_in_executor(
            None,
            lambda: model.encode([query], convert_to_numpy=True, show_progress_bar=False)
        )
        
        # Normalize query embedding
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self._package_index.search(query_embedding, limit * 2)  # Get more to filter
        
        # Filter by minimum score and convert to packages
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= min_score and idx < len(self._package_metadata):
                metadata = self._package_metadata[idx]
                
                # Convert metadata back to RepositoryPackage
                package = RepositoryPackage(
                    name=metadata['name'],
                    version=metadata['version'] or 'unknown',
                    description=metadata['description'],
                    repository_name=metadata['repository_name'],
                    platform=metadata['platform'],
                    category=metadata['category'],
                    tags=metadata['tags'],
                    homepage=metadata['homepage'],
                    maintainer=metadata['maintainer'],
                    license=metadata['license'],
                    last_updated=datetime.fromisoformat(metadata['last_updated']) if metadata['last_updated'] else None
                )
                
                results.append(package)
                
                if len(results) >= limit:
                    break
        
        logger.debug(f"Found {len(results)} similar packages for query: {query}")
        return results
    
    async def find_similar_saidata(
        self,
        software_name: str,
        limit: int = 3,
        min_score: float = 0.4
    ) -> List[SaiData]:
        """Find similar existing saidata files.
        
        Args:
            software_name: Software name to find similar saidata for
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of similar SaiData objects
        """
        # Load saidata index if not loaded
        if self._saidata_index is None:
            await self._load_saidata_index()
        
        if self._saidata_index is None or not self._saidata_metadata:
            logger.warning("Saidata index not available")
            return []
        
        # Get model and generate query embedding
        model = await self._get_model()
        
        # Create query text similar to saidata text creation
        query = f"{software_name} software application"
        
        loop = asyncio.get_event_loop()
        query_embedding = await loop.run_in_executor(
            None,
            lambda: model.encode([query], convert_to_numpy=True, show_progress_bar=False)
        )
        
        # Normalize query embedding
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self._saidata_index.search(query_embedding, limit * 2)
        
        # Filter by minimum score and load saidata files
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= min_score and idx < len(self._saidata_metadata):
                metadata = self._saidata_metadata[idx]
                
                try:
                    # Load the actual saidata file
                    file_path = Path(metadata['file_path'])
                    if file_path.exists():
                        import yaml
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f)
                        
                        saidata = SaiData(**data)
                        results.append(saidata)
                        
                        if len(results) >= limit:
                            break
                
                except Exception as e:
                    logger.warning(f"Failed to load saidata from {metadata['file_path']}: {e}")
                    continue
        
        logger.debug(f"Found {len(results)} similar saidata files for: {software_name}")
        return results
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get indexing statistics.
        
        Returns:
            Dictionary with index statistics
        """
        stats = {
            'model_name': self.model_name,
            'package_index_available': False,
            'saidata_index_available': False,
            'package_count': 0,
            'saidata_count': 0,
            'index_size_bytes': 0,
            'last_updated': None
        }
        
        # Check package index
        if self._package_index_path.exists():
            stats['package_index_available'] = True
            stats['index_size_bytes'] += self._package_index_path.stat().st_size
            
            if self._package_metadata_path.exists():
                stats['index_size_bytes'] += self._package_metadata_path.stat().st_size
                
                # Load metadata to get count
                try:
                    with open(self._package_metadata_path, 'rb') as f:
                        metadata = pickle.load(f)
                    stats['package_count'] = len(metadata)
                except Exception:
                    pass
        
        # Check saidata index
        if self._saidata_index_path.exists():
            stats['saidata_index_available'] = True
            stats['index_size_bytes'] += self._saidata_index_path.stat().st_size
            
            if self._saidata_metadata_path.exists():
                stats['index_size_bytes'] += self._saidata_metadata_path.stat().st_size
                
                # Load metadata to get count
                try:
                    with open(self._saidata_metadata_path, 'rb') as f:
                        metadata = pickle.load(f)
                    stats['saidata_count'] = len(metadata)
                except Exception:
                    pass
        
        # Check model info
        if self._model_info_path.exists():
            try:
                with open(self._model_info_path, 'r') as f:
                    model_info = json.load(f)
                stats['last_updated'] = model_info.get('last_updated')
            except Exception:
                pass
        
        return stats
    
    async def rebuild_indices(
        self,
        packages: Optional[List[RepositoryPackage]] = None,
        saidata_files: Optional[List[Path]] = None
    ) -> Dict[str, bool]:
        """Rebuild all indices.
        
        Args:
            packages: Repository packages to index (if None, skip package index)
            saidata_files: Saidata files to index (if None, skip saidata index)
            
        Returns:
            Dictionary with rebuild results
        """
        results = {
            'package_index_rebuilt': False,
            'saidata_index_rebuilt': False
        }
        
        try:
            if packages is not None:
                await self.index_repository_data(packages)
                results['package_index_rebuilt'] = True
        except Exception as e:
            logger.error(f"Failed to rebuild package index: {e}")
        
        try:
            if saidata_files is not None:
                await self.index_existing_saidata(saidata_files)
                results['saidata_index_rebuilt'] = True
        except Exception as e:
            logger.error(f"Failed to rebuild saidata index: {e}")
        
        # Update model info
        try:
            model_info = {
                'model_name': self.model_name,
                'last_updated': datetime.utcnow().isoformat(),
                'max_sequence_length': self.max_sequence_length
            }
            with open(self._model_info_path, 'w') as f:
                json.dump(model_info, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update model info: {e}")
        
        return results
    
    async def clear_indices(self) -> None:
        """Clear all indices and cached data."""
        # Clear in-memory data
        self._package_index = None
        self._package_metadata = []
        self._saidata_index = None
        self._saidata_metadata = []
        
        # Remove index files
        for file_path in [
            self._package_index_path,
            self._package_metadata_path,
            self._saidata_index_path,
            self._saidata_metadata_path,
            self._model_info_path
        ]:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove {file_path}: {e}")
        
        logger.info("All indices cleared")
    
    async def _save_package_index(self, index: "faiss.Index", metadata: List[Dict[str, Any]]) -> None:
        """Save package index and metadata to disk."""
        # Save FAISS index
        faiss.write_index(index, str(self._package_index_path))
        
        # Save metadata
        with open(self._package_metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        
        # Update in-memory references
        self._package_index = index
        self._package_metadata = metadata
    
    async def _save_saidata_index(self, index: "faiss.Index", metadata: List[Dict[str, Any]]) -> None:
        """Save saidata index and metadata to disk."""
        # Save FAISS index
        faiss.write_index(index, str(self._saidata_index_path))
        
        # Save metadata
        with open(self._saidata_metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        
        # Update in-memory references
        self._saidata_index = index
        self._saidata_metadata = metadata
    
    async def _load_package_index(self) -> None:
        """Load package index and metadata from disk."""
        if not self._package_index_path.exists() or not self._package_metadata_path.exists():
            return
        
        try:
            # Load FAISS index
            self._package_index = faiss.read_index(str(self._package_index_path))
            
            # Load metadata
            with open(self._package_metadata_path, 'rb') as f:
                self._package_metadata = pickle.load(f)
            
            logger.debug(f"Loaded package index with {len(self._package_metadata)} entries")
            
        except Exception as e:
            logger.error(f"Failed to load package index: {e}")
            self._package_index = None
            self._package_metadata = []
    
    async def _load_saidata_index(self) -> None:
        """Load saidata index and metadata from disk."""
        if not self._saidata_index_path.exists() or not self._saidata_metadata_path.exists():
            return
        
        try:
            # Load FAISS index
            self._saidata_index = faiss.read_index(str(self._saidata_index_path))
            
            # Load metadata
            with open(self._saidata_metadata_path, 'rb') as f:
                self._saidata_metadata = pickle.load(f)
            
            logger.debug(f"Loaded saidata index with {len(self._saidata_metadata)} entries")
            
        except Exception as e:
            logger.error(f"Failed to load saidata index: {e}")
            self._saidata_index = None
            self._saidata_metadata = []


class RAGContextBuilder:
    """Builder for RAG context injection into LLM prompts."""
    
    def __init__(self, indexer: RAGIndexer, config: Optional[Dict[str, Any]] = None):
        """Initialize context builder.
        
        Args:
            indexer: RAG indexer instance
            config: RAG configuration dictionary
        """
        self.indexer = indexer
        self.config = config or {}
        self._sample_saidata_cache: Optional[List[SaiData]] = None
    
    async def build_context(
        self,
        software_name: str,
        target_providers: Optional[List[str]] = None,
        max_packages: int = 5,
        max_saidata: int = 3
    ) -> Dict[str, Any]:
        """Build RAG context for LLM prompt injection.
        
        Args:
            software_name: Software name to build context for
            target_providers: Target providers to focus on
            max_packages: Maximum number of similar packages to include
            max_saidata: Maximum number of similar saidata to include
            
        Returns:
            Dictionary with RAG context data
        """
        context = {
            'similar_packages': [],
            'similar_saidata': [],
            'sample_saidata': [],
            'provider_specific_packages': {},
            'context_summary': ''
        }
        
        try:
            # Find similar packages
            similar_packages = await self.indexer.search_similar_packages(
                software_name,
                limit=max_packages
            )
            context['similar_packages'] = similar_packages
            
            # Group packages by provider if target providers specified
            if target_providers and similar_packages:
                for provider in target_providers:
                    provider_packages = [
                        pkg for pkg in similar_packages
                        if provider.lower() in pkg.repository_name.lower()
                    ]
                    if provider_packages:
                        context['provider_specific_packages'][provider] = provider_packages
            
            # Find similar saidata from indexed files
            similar_saidata = await self.indexer.find_similar_saidata(
                software_name,
                limit=max_saidata
            )
            context['similar_saidata'] = similar_saidata
            
            # Load default sample saidata if enabled and no similar saidata found
            if self.config.get('use_default_samples', True) and len(similar_saidata) < max_saidata:
                sample_saidata = await self._load_default_sample_saidata()
                remaining_slots = max_saidata - len(similar_saidata)
                context['sample_saidata'] = sample_saidata[:remaining_slots]
            
            # Build context summary
            context['context_summary'] = self._build_context_summary(
                software_name,
                similar_packages,
                similar_saidata + context['sample_saidata'],
                target_providers
            )
            
        except Exception as e:
            logger.warning(f"Failed to build RAG context for {software_name}: {e}")
        
        return context
    
    def _build_context_summary(
        self,
        software_name: str,
        similar_packages: List[RepositoryPackage],
        similar_saidata: List[SaiData],
        target_providers: Optional[List[str]]
    ) -> str:
        """Build a summary of the RAG context.
        
        Args:
            software_name: Software name
            similar_packages: Similar packages found
            similar_saidata: Similar saidata found
            target_providers: Target providers
            
        Returns:
            Context summary string
        """
        summary_parts = []
        
        if similar_packages:
            summary_parts.append(f"Found {len(similar_packages)} similar packages in repositories")
            
            # Summarize by repository
            repo_counts = {}
            for pkg in similar_packages:
                repo_counts[pkg.repository_name] = repo_counts.get(pkg.repository_name, 0) + 1
            
            repo_summary = ", ".join([f"{repo}: {count}" for repo, count in repo_counts.items()])
            summary_parts.append(f"Repository distribution: {repo_summary}")
        
        if similar_saidata:
            summary_parts.append(f"Found {len(similar_saidata)} similar saidata examples")
            
            # Summarize categories
            categories = [s.metadata.category for s in similar_saidata if s.metadata.category]
            if categories:
                unique_categories = list(set(categories))
                summary_parts.append(f"Categories: {', '.join(unique_categories)}")
        
        if target_providers:
            summary_parts.append(f"Targeting providers: {', '.join(target_providers)}")
        
        return ". ".join(summary_parts) if summary_parts else f"Building context for {software_name}"
    
    async def _load_default_sample_saidata(self) -> List[SaiData]:
        """Load default sample saidata files for use as examples.
        
        Returns:
            List of SaiData objects from sample files
        """
        if self._sample_saidata_cache is not None:
            return self._sample_saidata_cache
        
        sample_saidata = []
        
        # Determine sample directory
        sample_dir = self.config.get('default_samples_directory')
        if not sample_dir:
            # Try to find docs/saidata_samples relative to current working directory
            import os
            cwd = Path(os.getcwd())
            potential_paths = [
                cwd / "docs" / "saidata_samples",
                cwd.parent / "docs" / "saidata_samples",
                Path(__file__).parent.parent.parent / "docs" / "saidata_samples"
            ]
            
            for path in potential_paths:
                if path.exists() and path.is_dir():
                    sample_dir = path
                    break
        
        if not sample_dir or not Path(sample_dir).exists():
            logger.debug("No default sample saidata directory found")
            self._sample_saidata_cache = []
            return self._sample_saidata_cache
        
        sample_dir = Path(sample_dir)
        max_samples = self.config.get('max_sample_examples', 3)
        
        try:
            # Load YAML files from sample directory
            yaml_files = list(sample_dir.glob("*.yaml")) + list(sample_dir.glob("*.yml"))
            
            for yaml_file in yaml_files[:max_samples]:
                try:
                    import yaml
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    
                    # Parse as SaiData
                    saidata = SaiData(**data)
                    sample_saidata.append(saidata)
                    
                    logger.debug(f"Loaded sample saidata: {saidata.metadata.name}")
                    
                except Exception as e:
                    logger.warning(f"Failed to load sample saidata from {yaml_file}: {e}")
                    continue
            
            logger.info(f"Loaded {len(sample_saidata)} default sample saidata files from {sample_dir}")
            
        except Exception as e:
            logger.warning(f"Failed to load default sample saidata: {e}")
        
        # Cache the results
        self._sample_saidata_cache = sample_saidata
        return sample_saidata