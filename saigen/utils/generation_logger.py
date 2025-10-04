"""Generation process logging utility for detailed tracking of saigen operations."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from ..models.generation import GenerationContext, GenerationRequest
from ..models.repository import RepositoryPackage
from ..models.saidata import SaiData


@dataclass
class LLMInteraction:
    """Record of an LLM interaction."""
    timestamp: str
    provider: str
    model: str
    prompt: str
    response: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    duration_seconds: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class DataOperation:
    """Record of a data operation."""
    timestamp: str
    operation_type: str  # 'repository_fetch', 'rag_query', 'validation', 'file_save', etc.
    description: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    duration_seconds: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class ProcessStep:
    """Record of a process step."""
    timestamp: str
    step_name: str
    description: str
    status: str  # 'started', 'completed', 'failed'
    duration_seconds: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class GenerationLogger:
    """Logger for detailed generation process tracking."""
    
    def __init__(self, log_file_path: Path, software_name: str):
        """Initialize generation logger.
        
        Args:
            log_file_path: Path to the log file
            software_name: Name of the software being generated
        """
        self.log_file_path = log_file_path
        self.software_name = software_name
        self.session_id = f"{software_name}_{int(time.time())}"
        self.start_time = datetime.now()
        
        # Ensure log directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize log data structure
        self.log_data = {
            "session_id": self.session_id,
            "software_name": software_name,
            "start_time": self.start_time.isoformat(),
            "end_time": None,
            "total_duration_seconds": 0.0,
            "success": False,
            "generation_request": None,
            "generation_context": None,
            "process_steps": [],
            "llm_interactions": [],
            "data_operations": [],
            "final_result": None,
            "errors": [],
            "warnings": [],
            "metadata": {
                "saigen_version": self._get_saigen_version(),
                "python_version": self._get_python_version(),
                "system_info": self._get_system_info()
            }
        }
        
        # Write initial log entry
        self._write_log()
        
        # Set up file logger for real-time updates
        self._setup_file_logger()
    
    def log_generation_request(self, request: GenerationRequest) -> None:
        """Log the initial generation request.
        
        Args:
            request: Generation request to log
        """
        self.log_data["generation_request"] = {
            "software_name": request.software_name,
            "target_providers": request.target_providers,
            "llm_provider": request.llm_provider.value if hasattr(request.llm_provider, 'value') else str(request.llm_provider),
            "use_rag": request.use_rag,
            "user_hints": request.user_hints,
            "has_existing_saidata": request.existing_saidata is not None
        }
        self._write_log()
    
    def log_generation_context(self, context: GenerationContext) -> None:
        """Log the generation context.
        
        Args:
            context: Generation context to log
        """
        # Serialize context data safely
        context_data = {
            "software_name": context.software_name,
            "target_providers": context.target_providers,
            "user_hints": context.user_hints,
            "has_existing_saidata": context.existing_saidata is not None,
            "repository_data_count": len(context.repository_data) if context.repository_data else 0,
            "similar_saidata_count": len(context.similar_saidata) if context.similar_saidata else 0,
            "sample_saidata_count": len(getattr(context, 'sample_saidata', [])),
        }
        
        # Add repository data summary
        if context.repository_data:
            repo_summary = {}
            for pkg in context.repository_data:
                repo_name = pkg.repository_name
                if repo_name not in repo_summary:
                    repo_summary[repo_name] = []
                repo_summary[repo_name].append({
                    "name": pkg.name,
                    "version": pkg.version,
                    "description": pkg.description[:100] if pkg.description else None
                })
            context_data["repository_data_summary"] = repo_summary
        
        # Add similar saidata summary
        if context.similar_saidata:
            similar_summary = []
            for saidata in context.similar_saidata:
                similar_summary.append({
                    "name": saidata.metadata.name,
                    "category": saidata.metadata.category,
                    "providers": list(saidata.providers.keys()) if saidata.providers else []
                })
            context_data["similar_saidata_summary"] = similar_summary
        
        self.log_data["generation_context"] = context_data
        self._write_log()
    
    def log_generation_context_enhancement(self, enhancement_info: Dict[str, Any]) -> None:
        """Log context enhancement information for 0.3 schema.
        
        Args:
            enhancement_info: Information about context enhancements
        """
        if "generation_context" not in self.log_data:
            self.log_data["generation_context"] = {}
        
        self.log_data["generation_context"]["enhancement_v03"] = enhancement_info
        self._write_log()
    
    def log_process_step(self, step_name: str, description: str, status: str = "started", 
                        metadata: Optional[Dict[str, Any]] = None) -> ProcessStep:
        """Log a process step.
        
        Args:
            step_name: Name of the step
            description: Description of the step
            status: Step status ('started', 'completed', 'failed')
            metadata: Additional metadata
            
        Returns:
            ProcessStep object for tracking
        """
        step = ProcessStep(
            timestamp=datetime.now().isoformat(),
            step_name=step_name,
            description=description,
            status=status,
            metadata=metadata or {}
        )
        
        self.log_data["process_steps"].append(asdict(step))
        self._write_log()
        return step
    
    def update_process_step(self, step: ProcessStep, status: str, duration_seconds: float = 0.0,
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """Update a process step.
        
        Args:
            step: ProcessStep to update
            status: New status
            duration_seconds: Duration of the step
            metadata: Additional metadata to merge
        """
        # Find and update the step in log_data
        for logged_step in self.log_data["process_steps"]:
            if (logged_step["step_name"] == step.step_name and 
                logged_step["timestamp"] == step.timestamp):
                logged_step["status"] = status
                logged_step["duration_seconds"] = duration_seconds
                if metadata:
                    logged_step["metadata"].update(metadata)
                break
        
        self._write_log()
    
    def log_llm_interaction(self, provider: str, model: str, prompt: str, response: str,
                           tokens_used: Optional[int] = None, cost_estimate: Optional[float] = None,
                           duration_seconds: float = 0.0, success: bool = True, 
                           error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log an LLM interaction.
        
        Args:
            provider: LLM provider name
            model: Model name
            prompt: Prompt sent to LLM
            response: Response from LLM
            tokens_used: Number of tokens used
            cost_estimate: Estimated cost
            duration_seconds: Duration of the interaction
            success: Whether the interaction was successful
            error: Error message if failed
            metadata: Additional metadata (e.g., retry_attempt flag)
        """
        interaction_data = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "response": response,
            "tokens_used": tokens_used,
            "cost_estimate": cost_estimate,
            "duration_seconds": duration_seconds,
            "success": success,
            "error": error,
            "metadata": metadata or {}
        }
        
        self.log_data["llm_interactions"].append(interaction_data)
        self._write_log()
    
    def log_data_operation(self, operation_type: str, description: str,
                          input_data: Optional[Dict[str, Any]] = None,
                          output_data: Optional[Dict[str, Any]] = None,
                          duration_seconds: float = 0.0, success: bool = True,
                          error: Optional[str] = None) -> None:
        """Log a data operation.
        
        Args:
            operation_type: Type of operation
            description: Description of the operation
            input_data: Input data (will be serialized safely)
            output_data: Output data (will be serialized safely)
            duration_seconds: Duration of the operation
            success: Whether the operation was successful
            error: Error message if failed
        """
        operation = DataOperation(
            timestamp=datetime.now().isoformat(),
            operation_type=operation_type,
            description=description,
            input_data=self._serialize_safely(input_data),
            output_data=self._serialize_safely(output_data),
            duration_seconds=duration_seconds,
            success=success,
            error=error
        )
        
        self.log_data["data_operations"].append(asdict(operation))
        self._write_log()
    
    def log_error(self, error: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error.
        
        Args:
            error: Error message
            context: Additional context
        """
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "context": context or {}
        }
        self.log_data["errors"].append(error_entry)
        self._write_log()
    
    def log_warning(self, warning: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning.
        
        Args:
            warning: Warning message
            context: Additional context
        """
        warning_entry = {
            "timestamp": datetime.now().isoformat(),
            "warning": warning,
            "context": context or {}
        }
        self.log_data["warnings"].append(warning_entry)
        self._write_log()
    
    def log_final_result(self, success: bool, saidata: Optional[SaiData] = None,
                        validation_errors: Optional[List[str]] = None,
                        output_file: Optional[Path] = None) -> None:
        """Log the final generation result.
        
        Args:
            success: Whether generation was successful
            saidata: Generated saidata (if successful)
            validation_errors: Validation errors (if any)
            output_file: Output file path
        """
        result_data = {
            "success": success,
            "has_saidata": saidata is not None,
            "validation_errors": validation_errors or [],
            "output_file": str(output_file) if output_file else None
        }
        
        if saidata:
            result_data["saidata_summary"] = {
                "name": saidata.metadata.name,
                "version": saidata.version,
                "category": saidata.metadata.category,
                "providers": list(saidata.providers.keys()) if saidata.providers else [],
                "package_count": sum(len(p.packages) for p in saidata.providers.values() if p.packages) if saidata.providers else 0,
                "service_count": sum(len(p.services) for p in saidata.providers.values() if p.services) if saidata.providers else 0
            }
        
        self.log_data["final_result"] = result_data
        self.log_data["success"] = success
        self._finalize_log()
    
    @contextmanager
    def log_step(self, step_name: str, description: str, metadata: Optional[Dict[str, Any]] = None):
        """Context manager for logging a process step with automatic timing.
        
        Args:
            step_name: Name of the step
            description: Description of the step
            metadata: Additional metadata
        """
        start_time = time.time()
        step = self.log_process_step(step_name, description, "started", metadata)
        
        try:
            yield step
            duration = time.time() - start_time
            self.update_process_step(step, "completed", duration)
        except Exception as e:
            duration = time.time() - start_time
            self.update_process_step(step, "failed", duration, {"error": str(e)})
            raise
    
    @contextmanager
    def log_data_op(self, operation_type: str, description: str, 
                    input_data: Optional[Dict[str, Any]] = None):
        """Context manager for logging a data operation with automatic timing.
        
        Args:
            operation_type: Type of operation
            description: Description of the operation
            input_data: Input data
        """
        start_time = time.time()
        output_data = None
        
        try:
            yield lambda data: setattr(self, '_temp_output_data', data)
            duration = time.time() - start_time
            output_data = getattr(self, '_temp_output_data', None)
            self.log_data_operation(operation_type, description, input_data, output_data, duration, True)
        except Exception as e:
            duration = time.time() - start_time
            self.log_data_operation(operation_type, description, input_data, None, duration, False, str(e))
            raise
        finally:
            if hasattr(self, '_temp_output_data'):
                delattr(self, '_temp_output_data')
    
    def _finalize_log(self) -> None:
        """Finalize the log with end time and total duration."""
        end_time = datetime.now()
        self.log_data["end_time"] = end_time.isoformat()
        self.log_data["total_duration_seconds"] = (end_time - self.start_time).total_seconds()
        self._write_log()
    
    def _write_log(self) -> None:
        """Write current log data to file."""
        try:
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.log_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # Fallback to basic logging if file write fails
            logging.error(f"Failed to write generation log: {e}")
    
    def _serialize_safely(self, data: Any) -> Any:
        """Safely serialize data for JSON logging.
        
        Args:
            data: Data to serialize
            
        Returns:
            JSON-serializable data
        """
        if data is None:
            return None
        
        try:
            # Try to serialize as-is first
            json.dumps(data)
            return data
        except (TypeError, ValueError):
            # Handle complex objects
            if hasattr(data, 'model_dump'):
                # Pydantic model
                return data.model_dump()
            elif hasattr(data, '__dict__'):
                # Regular object with attributes
                return {k: self._serialize_safely(v) for k, v in data.__dict__.items()}
            elif isinstance(data, (list, tuple)):
                return [self._serialize_safely(item) for item in data]
            elif isinstance(data, dict):
                return {k: self._serialize_safely(v) for k, v in data.items()}
            else:
                # Fallback to string representation
                return str(data)
    
    def _setup_file_logger(self) -> None:
        """Set up file logger for real-time updates."""
        # Create a separate logger for this session
        logger_name = f"saigen.generation.{self.session_id}"
        self.file_logger = logging.getLogger(logger_name)
        self.file_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.file_logger.handlers[:]:
            self.file_logger.removeHandler(handler)
        
        # Create file handler for text logs
        text_log_path = self.log_file_path.with_suffix('.log')
        file_handler = logging.FileHandler(text_log_path, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        self.file_logger.addHandler(file_handler)
        self.file_logger.info(f"Generation logging started for {self.software_name}")
    
    def _get_saigen_version(self) -> str:
        """Get saigen version."""
        try:
            from ..version import get_version
            return get_version()
        except Exception:
            return "unknown"
    
    def _get_python_version(self) -> str:
        """Get Python version."""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    def _get_system_info(self) -> Dict[str, str]:
        """Get system information."""
        import platform
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "machine": platform.machine(),
            "python_implementation": platform.python_implementation()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the generation process.
        
        Returns:
            Summary dictionary
        """
        return {
            "session_id": self.session_id,
            "software_name": self.software_name,
            "success": self.log_data["success"],
            "total_duration": self.log_data.get("total_duration_seconds", 0.0),
            "process_steps_count": len(self.log_data["process_steps"]),
            "llm_interactions_count": len(self.log_data["llm_interactions"]),
            "data_operations_count": len(self.log_data["data_operations"]),
            "errors_count": len(self.log_data["errors"]),
            "warnings_count": len(self.log_data["warnings"]),
            "total_tokens_used": sum(
                interaction.get("tokens_used", 0) or 0 
                for interaction in self.log_data["llm_interactions"]
            ),
            "total_cost_estimate": sum(
                interaction.get("cost_estimate", 0.0) or 0.0 
                for interaction in self.log_data["llm_interactions"]
            )
        }


def create_generation_log_filename(software_name: str, timestamp: Optional[datetime] = None) -> str:
    """Create a standardized log filename for generation.
    
    Args:
        software_name: Name of the software
        timestamp: Timestamp to use (defaults to now)
        
    Returns:
        Log filename
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    # Sanitize software name for filename
    import re
    safe_name = re.sub(r'[^\w\-_.]', '_', software_name)
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    
    return f"saigen_generate_{safe_name}_{timestamp_str}.json"