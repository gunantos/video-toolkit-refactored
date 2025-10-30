"""
Workflow Manager

Orchestrates the execution of video processing workflows with:
- Step-by-step execution
- Progress tracking
- Error handling and recovery
- Async support
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import traceback

from core.config import get_config
from core.constants import WORKFLOW_PRESETS, WorkflowStep, ProcessingStatus
from core.exceptions import (
    WorkflowError, WorkflowValidationError, WorkflowExecutionError, 
    StepError, TimeoutError
)
from core.utils.logging import get_logger
from core.workflow.steps import WorkflowStepExecutor
from core.workflow.presets import PresetManager

logger = get_logger(__name__)


class WorkflowContext:
    """Context object that carries state through workflow execution"""
    
    def __init__(self, video_source: str, options: Dict[str, Any] = None):
        self.video_source = video_source
        self.options = options or {}
        self.config = get_config()
        
        # Execution state
        self.current_step = None
        self.status = ProcessingStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.error = None
        
        # File tracking
        self.working_dir = None
        self.video_file = None
        self.audio_file = None
        self.subtitle_files = []
        self.output_files = []
        
        # Results tracking
        self.step_results = {}
        self.upload_results = {}
        self.metadata = {}
    
    def add_output_file(self, file_path: Path, file_type: str = "output"):
        """Add output file to tracking"""
        self.output_files.append({
            'path': file_path,
            'type': file_type,
            'created_at': datetime.now()
        })
    
    def get_latest_video(self) -> Optional[Path]:
        """Get the most recent video file"""
        video_files = [f for f in self.output_files if f['type'] in ['video', 'processed']]
        if video_files:
            return max(video_files, key=lambda x: x['created_at'])['path']
        return self.video_file
    
    def set_error(self, error: Exception, step: str = None):
        """Set error state"""
        self.error = error
        self.status = ProcessingStatus.FAILED
        if step:
            self.current_step = step
        logger.error(f"Workflow error in step {step}: {error}")


class WorkflowManager:
    """Main workflow orchestration manager"""
    
    def __init__(self):
        self.config = get_config()
        self.step_executor = WorkflowStepExecutor()
        self.preset_manager = PresetManager()
        self.active_workflows = {}  # Track active workflows
    
    async def execute_workflow(
        self, 
        preset_key: str, 
        video_source: str,
        options: Dict[str, Any] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Execute a complete workflow"""
        
        # Create workflow context
        context = WorkflowContext(video_source, options)
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Validate and prepare workflow
            workflow_config = self._prepare_workflow(preset_key, context)
            
            # Track active workflow
            self.active_workflows[workflow_id] = context
            
            # Execute workflow steps
            context.status = ProcessingStatus.RUNNING
            context.start_time = datetime.now()
            
            if progress_callback:
                progress_callback(f"Starting workflow: {workflow_config['name']}")
            
            for i, step_name in enumerate(workflow_config['steps']):
                try:
                    context.current_step = step_name
                    
                    if progress_callback:
                        progress_callback(f"Step {i+1}/{len(workflow_config['steps'])}: {step_name}")
                    
                    # Execute step
                    step_result = await self._execute_step(step_name, context)
                    context.step_results[step_name] = step_result
                    
                    logger.info(f"Step '{step_name}' completed successfully")
                    
                except StepError as e:
                    # Step-specific error handling
                    context.set_error(e, step_name)
                    
                    if self._is_critical_step(step_name, workflow_config):
                        # Critical step failed, abort workflow
                        raise WorkflowExecutionError(
                            f"Critical step '{step_name}' failed: {e.message}"
                        ) from e
                    else:
                        # Non-critical step, log and continue
                        logger.warning(f"Non-critical step '{step_name}' failed: {e.message}")
                        continue
            
            # Workflow completed successfully
            context.status = ProcessingStatus.COMPLETED
            context.end_time = datetime.now()
            
            if progress_callback:
                progress_callback("✅ Workflow completed successfully!")
            
            logger.info(f"Workflow '{preset_key}' completed successfully")
            
            return {
                'success': True,
                'workflow_id': workflow_id,
                'output_files': [f['path'] for f in context.output_files],
                'upload_results': context.upload_results,
                'metadata': context.metadata,
                'execution_time': (context.end_time - context.start_time).total_seconds()
            }
            
        except Exception as e:
            # Workflow failed
            context.set_error(e)
            context.end_time = datetime.now()
            
            if progress_callback:
                progress_callback(f"❌ Workflow failed: {e}")
            
            logger.error(f"Workflow '{preset_key}' failed: {e}")
            
            return {
                'success': False,
                'workflow_id': workflow_id,
                'error': str(e),
                'failed_step': context.current_step,
                'partial_results': context.step_results
            }
        
        finally:
            # Cleanup
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
    
    def _prepare_workflow(self, preset_key: str, context: WorkflowContext) -> Dict:
        """Prepare and validate workflow configuration"""
        
        # Get preset configuration
        if preset_key not in WORKFLOW_PRESETS:
            raise WorkflowValidationError(f"Unknown workflow preset: {preset_key}")
        
        workflow_config = WORKFLOW_PRESETS[preset_key].copy()
        
        # Apply user options
        if context.options:
            # Override configuration with user options
            if 'platforms' in context.options:
                context.config.platforms.enabled_platforms = context.options['platforms']
            
            if 'split_duration' in context.options:
                context.config.processing.split_duration = context.options['split_duration']
        
        # Validate workflow steps
        self._validate_workflow_steps(workflow_config['steps'])
        
        # Setup working directory
        context.working_dir = self._create_working_directory(context.video_source)
        
        return workflow_config
    
    def _validate_workflow_steps(self, steps: List[str]):
        """Validate workflow steps and dependencies"""
        
        # Check if all steps are valid
        valid_steps = {step.value for step in WorkflowStep}
        invalid_steps = [step for step in steps if step not in valid_steps]
        
        if invalid_steps:
            raise WorkflowValidationError(f"Invalid workflow steps: {invalid_steps}")
        
        # Check step dependencies
        step_dependencies = {
            'merge_av': ['split_av'],
            'translate_subtitle': ['subtitle'],
            'embed_subtitle': ['subtitle']
        }
        
        for step in steps:
            if step in step_dependencies:
                for dependency in step_dependencies[step]:
                    if dependency not in steps:
                        raise WorkflowValidationError(
                            f"Step '{step}' requires '{dependency}' but it's not in workflow"
                        )
    
    def _create_working_directory(self, video_source: str) -> Path:
        """Create working directory for workflow execution"""
        
        # Generate directory name from video source
        if video_source.startswith('http'):
            # URL source - use timestamp
            dir_name = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        elif video_source.startswith('search:'):
            # Search source
            search_term = video_source[7:].replace(' ', '_')
            dir_name = f"search_{search_term}_{datetime.now().strftime('%H%M%S')}"
        else:
            # File/folder source
            source_path = Path(video_source)
            dir_name = f"{source_path.stem}_{datetime.now().strftime('%H%M%S')}"
        
        working_dir = self.config.paths.output_dir / dir_name
        working_dir.mkdir(parents=True, exist_ok=True)
        
        return working_dir
    
    async def _execute_step(self, step_name: str, context: WorkflowContext) -> Dict[str, Any]:
        """Execute a single workflow step"""
        
        logger.info(f"Executing step: {step_name}")
        
        try:
            # Get step timeout
            step_timeout = self._get_step_timeout(step_name)
            
            # Execute step with timeout
            result = await asyncio.wait_for(
                self.step_executor.execute_step(step_name, context),
                timeout=step_timeout
            )
            
            logger.info(f"Step '{step_name}' completed in {result.get('execution_time', 0):.1f}s")
            return result
            
        except asyncio.TimeoutError:
            raise StepError(
                step_name, 
                f"Step timed out after {step_timeout} seconds"
            )
        except Exception as e:
            raise StepError(
                step_name,
                f"Step execution failed: {str(e)}",
                details=traceback.format_exc()
            )
    
    def _get_step_timeout(self, step_name: str) -> int:
        """Get timeout for specific step"""
        step_timeouts = {
            'download': 3600,  # 1 hour
            'subtitle': 1800,  # 30 minutes
            'upload': 1800,    # 30 minutes per platform
        }
        return step_timeouts.get(step_name, 900)  # Default 15 minutes
    
    def _is_critical_step(self, step_name: str, workflow_config: Dict) -> bool:
        """Check if step is critical for workflow success"""
        critical_steps = {'download', 'upload'}
        return step_name in critical_steps
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get status of active workflow"""
        if workflow_id in self.active_workflows:
            context = self.active_workflows[workflow_id]
            return {
                'workflow_id': workflow_id,
                'status': context.status.value,
                'current_step': context.current_step,
                'progress': len(context.step_results),
                'start_time': context.start_time,
                'error': str(context.error) if context.error else None
            }
        return None
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel active workflow"""
        if workflow_id in self.active_workflows:
            context = self.active_workflows[workflow_id]
            context.status = ProcessingStatus.CANCELLED
            # TODO: Implement actual cancellation logic
            return True
        return False
    
    def list_active_workflows(self) -> List[Dict]:
        """List all active workflows"""
        return [
            self.get_workflow_status(workflow_id) 
            for workflow_id in self.active_workflows
        ]
