"""
NOVA Autonomous Coding Agent Core
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from nova.environment.environment_manager import EnvironmentManager
from nova.environment.dependency_manager import DependencyManager
from nova.project.project_runner import ProjectRunner
from nova.project.error_analyzer import ErrorAnalyzer
from nova.project.test_runner import TestRunner
from nova.project.state_manager import ProjectStateManager
from nova.permissions.permission_manager import PermissionManager, PermissionLevel
from nova.services.memory_service import MemoryService
from nova.utils.constants import NovaException

logger = logging.getLogger("NOVA.CodingAgent")


class CodingAgent:
    """
    Orchestrates the Day 4 Software Engineering Autonomous Workflow:
    UNDERSTAND -> DETECT LANGUAGE -> DETECT ENVIRONMENT -> DETECT DEPENDENCIES ->
    PLAN -> PERMISSION CHECK -> PREPARE ENVIRONMENT -> INSTALL DEPENDENCIES ->
    RUN -> CAPTURE RESULT -> CLASSIFY ERROR -> PROPOSE FIX -> PERMISSION ->
    APPLY FIX -> VERIFY -> SAVE MEMORY.
    """

    MAX_DEBUG_ATTEMPTS: int = 3

    def __init__(
        self,
        workspace_root: Optional[Union[str, Path]] = None,
        permission_manager: Optional[PermissionManager] = None,
        memory_service: Optional[MemoryService] = None,
    ):
        self.workspace_root: Path = Path(workspace_root or Path.cwd()).resolve()
        self.permission_manager: PermissionManager = permission_manager or PermissionManager(workspace_root=self.workspace_root)
        self.memory_service: Optional[MemoryService] = memory_service

        # Instantiate sub-services
        self.env_manager = EnvironmentManager(workspace_root=self.workspace_root, permission_manager=self.permission_manager)
        self.dep_manager = DependencyManager(
            workspace_root=self.workspace_root,
            environment_manager=self.env_manager,
            permission_manager=self.permission_manager,
        )
        self.runner = ProjectRunner(
            workspace_root=self.workspace_root,
            environment_manager=self.env_manager,
            permission_manager=self.permission_manager,
        )
        self.error_analyzer = ErrorAnalyzer()
        self.test_runner = TestRunner(
            workspace_root=self.workspace_root,
            environment_manager=self.env_manager,
            permission_manager=self.permission_manager,
        )
        self.state_manager = ProjectStateManager(workspace_root=self.workspace_root)

    def analyze_project(self) -> Dict[str, Any]:
        """
        Scans workspace, detects language, environment status, dependency files, and entry points.
        """
        lang_info = self.env_manager.detect_language()
        env_health = self.env_manager.health_check()
        dep_files = self.dep_manager.detect_dependency_files()
        dep_check = self.dep_manager.check_missing_dependencies()
        entry_point = self.runner.find_entry_point()
        test_info = self.test_runner.detect_test_framework()

        summary = {
            "workspace_root": str(self.workspace_root),
            "primary_language": lang_info["primary"],
            "environment": env_health,
            "dependency_files": dep_files["files_found"],
            "missing_dependencies": dep_check["missing"],
            "entry_point": str(entry_point.relative_to(self.workspace_root)) if entry_point else None,
            "tests_detected": test_info["has_tests"],
        }

        self.state_manager.update_environment(env_health)
        self.state_manager.update_dependencies(dep_check)
        return summary

    def execute_workflow(
        self,
        task_description: str,
        user_approved_venv: bool = False,
        user_approved_install: bool = False,
        user_approved_run: bool = False,
        user_approved_fix: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes full Day 4 autonomous workflow.
        """
        self.state_manager.update_task(task_description, status="IN_PROGRESS")
        self.state_manager.reset_debug_attempts()

        workflow_log: List[str] = []
        action_proposals: List[Dict[str, Any]] = []

        # 1. UNDERSTAND & DETECT
        workflow_log.append("Phase 1: Analyzing project workspace, environment, and dependencies...")
        project_analysis = self.analyze_project()

        # 2. PREPARE ENVIRONMENT
        workflow_log.append("Phase 2: Verifying Python environment...")
        env_health = project_analysis["environment"]

        if env_health["status"] == "Missing" or not env_health["details"]["venv_found"]:
            workflow_log.append("Virtual environment '.venv' not found. Proposing creation...")
            create_res = self.env_manager.create_virtual_environment(venv_name=".venv", user_approved=user_approved_venv)
            if not create_res.get("success"):
                if create_res.get("permission_required"):
                    action_proposals.append(create_res["proposed_action"])
                    workflow_log.append("Waiting for user permission to create virtual environment '.venv'.")
                    return self._build_workflow_result(
                        success=False,
                        status="WAITING_FOR_PERMISSION",
                        workflow_log=workflow_log,
                        action_proposals=action_proposals,
                    )
                else:
                    workflow_log.append(f"Virtual environment creation failed: {create_res.get('error')}")

        # 3. DETECT & INSTALL DEPENDENCIES
        workflow_log.append("Phase 3: Checking project dependencies...")
        dep_check = self.dep_manager.check_missing_dependencies()
        if dep_check["missing"]:
            workflow_log.append(f"Missing dependencies detected: {dep_check['missing']}")
            for pkg in dep_check["missing"]:
                inst_res = self.dep_manager.install_dependency(pkg, user_approved=user_approved_install)
                if not inst_res.get("success"):
                    if inst_res.get("permission_required"):
                        action_proposals.append(inst_res["proposed_action"])
                        workflow_log.append(f"Waiting for user permission to install missing package '{pkg}'.")
                    else:
                        workflow_log.append(f"Installation of package '{pkg}' failed: {inst_res.get('error')}")

            if action_proposals:
                return self._build_workflow_result(
                    success=False,
                    status="WAITING_FOR_PERMISSION",
                    workflow_log=workflow_log,
                    action_proposals=action_proposals,
                )

        # 4. RUN PROJECT
        workflow_log.append("Phase 4: Executing project entry point...")
        run_res = self.runner.run_project(user_approved=user_approved_run)

        if run_res.get("permission_required"):
            action_proposals.append(run_res["proposed_action"])
            workflow_log.append("Waiting for user permission to execute project script.")
            return self._build_workflow_result(
                success=False,
                status="WAITING_FOR_PERMISSION",
                workflow_log=workflow_log,
                action_proposals=action_proposals,
            )

        self.state_manager.record_execution(run_res)

        # 5. CAPTURE & DEBUG LOOP
        current_run = run_res
        attempts = 0

        while not current_run.get("success") and attempts < self.MAX_DEBUG_ATTEMPTS:
            attempts = self.state_manager.increment_debug_attempts()
            workflow_log.append(f"Phase 5 (Debug Iteration {attempts}/{self.MAX_DEBUG_ATTEMPTS}): Analyzing execution error...")

            error_diag = self.error_analyzer.analyze(
                stderr=current_run.get("stderr", ""),
                stdout=current_run.get("stdout", ""),
                exit_code=current_run.get("exit_code", -1),
            )
            self.state_manager.record_error(error_diag)

            workflow_log.append(f"Error Classified: [{error_diag['error_type']}] -> {error_diag['likely_cause']}")

            # Handle missing module auto-recommendation
            if error_diag["error_type"] == "ModuleNotFoundError" and error_diag["target_package"]:
                missing_pkg = error_diag["target_package"]
                workflow_log.append(f"Proposing fix: Install missing module '{missing_pkg}'.")

                inst_res = self.dep_manager.install_dependency(missing_pkg, user_approved=user_approved_fix)
                if not inst_res.get("success"):
                    if inst_res.get("permission_required"):
                        action_proposals.append(inst_res["proposed_action"])
                        workflow_log.append(f"Waiting for user permission to install '{missing_pkg}' for self-debugging.")
                        return self._build_workflow_result(
                            success=False,
                            status="WAITING_FOR_PERMISSION",
                            workflow_log=workflow_log,
                            action_proposals=action_proposals,
                        )
                    else:
                        workflow_log.append(f"Failed to auto-install package '{missing_pkg}': {inst_res.get('error')}")
                        break
                else:
                    workflow_log.append(f"Successfully installed package '{missing_pkg}'. Re-running program...")
                    current_run = self.runner.run_project(user_approved=True)
                    self.state_manager.record_execution(current_run)
            else:
                workflow_log.append(f"Suggested Action for code fix: {error_diag['suggested_action']}")
                break

        # 6. RUN TESTS IF PRESENT
        test_results = None
        test_info = self.test_runner.detect_test_framework()
        if test_info["has_tests"]:
            workflow_log.append("Phase 6: Running project test suite...")
            test_results = self.test_runner.run_tests()
            self.state_manager.record_test_result(test_results)
            workflow_log.append(f"Test Summary: {test_results.get('passed', 0)} passed, {test_results.get('failed', 0)} failed.")

        # 7. SAVE MEMORY & RECORD OUTCOME
        final_success = current_run.get("success", False)
        status_str = "COMPLETED_SUCCESS" if final_success else "COMPLETED_WITH_ERRORS"
        self.state_manager.update_task(task_description, status=status_str)

        if self.memory_service:
            self._record_memory_history(task_description, status_str, final_success)

        return self._build_workflow_result(
            success=final_success,
            status=status_str,
            workflow_log=workflow_log,
            action_proposals=action_proposals,
            execution_result=current_run,
            test_result=test_results,
            debug_attempts=attempts,
        )

    def _build_workflow_result(
        self,
        success: bool,
        status: str,
        workflow_log: List[str],
        action_proposals: List[Dict[str, Any]],
        execution_result: Optional[Dict[str, Any]] = None,
        test_result: Optional[Dict[str, Any]] = None,
        debug_attempts: int = 0,
    ) -> Dict[str, Any]:
        return {
            "success": success,
            "status": status,
            "workflow_log": workflow_log,
            "action_proposals": action_proposals,
            "execution_result": execution_result,
            "test_result": test_result,
            "debug_attempts": debug_attempts,
            "project_state": self.state_manager.get_state(),
        }

    def _record_memory_history(self, task: str, status: str, success: bool) -> None:
        try:
            episodes = self.memory_service.get_memory("long_term.json")
            if episodes is None:
                episodes = {"episodes": []}
            if "episodes" not in episodes:
                episodes["episodes"] = []

            episodes["episodes"].append({
                "task": task,
                "status": status,
                "success": success,
                "workspace": str(self.workspace_root),
                "timestamp": self.state_manager.get_state().get("last_updated"),
            })
            self.memory_service.save_memory("long_term.json", episodes)
        except Exception as e:
            logger.error(f"Failed to record project memory: {e}")
