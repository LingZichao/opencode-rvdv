from __future__ import annotations

import os
from pathlib import Path

from src.utils.env import load_project_dotenv


load_project_dotenv()


def get_project_root() -> Path:
    """Return the AgenticISG repository root."""
    return Path(__file__).resolve().parents[2]


def _resolve_path_override(*env_names: str) -> Path | None:
    for env_name in env_names:
        value = os.getenv(env_name)
        if value:
            return Path(value).expanduser().resolve()
    return None


def get_workspace_root() -> Path:
    """Return the static runtime workspace root."""
    override = _resolve_path_override("AGENTICISG_WORKSPACE_ROOT")
    if override:
        return override
    return get_project_root() / "workspace"


def get_agent_doc_root() -> Path:
    """Return the directory that stores agent-readable documentation."""
    return get_workspace_root() / "agentDoc"


def get_workspace_codebase_root() -> Path:
    """Return the default RTL/code mirror inside the static workspace."""
    return get_workspace_root() / "openc910"


def get_coverage_root() -> Path:
    """Return the coverage database root."""
    override = _resolve_path_override("AGENTICISG_COVERAGEDB", "COVERAGEDB")
    if override:
        return override
    return get_project_root() / "coverageDB"


def get_task_root(task_name: str | None) -> Path:
    """Return the task runtime root under coverageDB/tasks."""
    tasks_root = get_coverage_root() / "tasks"
    if task_name is None:
        return tasks_root
    return tasks_root / task_name


def get_template_root() -> Path:
    """Return the directory containing shared coverage template assets."""
    override = _resolve_path_override("AGENTICISG_TEMPLATE_DIR")
    if override:
        return override
    return get_coverage_root() / "template"


def get_task_workspace(task_name: str | None) -> Path:
    """Backward-compatible alias for the task runtime root."""
    return get_task_root(task_name)


def get_task_isg_scripts_root(task_name: str | None) -> Path:
    """Return the ISG scripts directory under workspace/isgScripts/<task_name>.

    This is the centralized location for all ISG scripts, organized by task ID.
    The workspace directory is the only readable and writable directory for the agent.
    """
    if task_name is None:
        return get_workspace_root() / "isgScripts"
    return get_workspace_root() / "isgScripts" / task_name


def get_task_sim_root(task_name: str | None) -> Path:
    """Return the simulation directory under coverageDB/tasks/<task_name>/sim.

    Note: Simulation files remain in coverageDB, not in workspace.
    """
    task_root = get_task_root(task_name)
    return task_root / "sim"


def get_template_sim_root() -> Path:
    return get_template_root() / "sim"


def get_baseline_vdb_path() -> Path:
    return get_template_root() / "BASELINE.vdb"


def get_regression_root() -> Path:
    """Return the directory for regression outputs and historical reports."""
    return get_coverage_root() / "regression"


def get_scoreboard_root() -> Path:
    """Return the default directory for scoreboard files."""
    return get_regression_root() / "long_agent_scoreboard"


def get_log_root() -> Path:
    """Return the directory used for application logs."""
    return get_coverage_root() / "logs"


def get_rtl_root() -> Path:
    """Resolve the RTL source root with sensible migration-friendly fallbacks."""
    env_root = _resolve_path_override("C910_RTL_ROOT")
    candidates = []
    if env_root:
        candidates.append(env_root)

    project_root = get_project_root()
    candidates.extend(
        [
            get_workspace_codebase_root().resolve(),
            (project_root.parent / "openc910" / "C910_RTL_FACTORY" / "gen_rtl").resolve(),
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if candidates else get_workspace_codebase_root().resolve()


def get_cli_preflight_issues() -> list[str]:
    """Collect missing runtime assets that block local CLI execution."""
    issues: list[str] = []

    project_root = get_project_root()
    workspace_root = get_workspace_root()
    workspace_codebase_root = get_workspace_codebase_root()
    agent_doc_root = get_agent_doc_root()
    coverage_root = get_coverage_root()
    template_root = get_template_root()
    template_sim_root = get_template_sim_root()
    baseline_vdb = get_baseline_vdb_path()
    rtl_root = get_rtl_root()
    makefile_path = project_root / "makefile"

    if not makefile_path.exists():
        issues.append(f"Missing makefile: {makefile_path}")
    if not workspace_root.exists():
        issues.append(f"Missing workspace directory: {workspace_root}")
    if not workspace_codebase_root.exists():
        issues.append(f"Missing workspace codebase directory: {workspace_codebase_root}")
    if not agent_doc_root.exists():
        issues.append(f"Missing workspace agentDoc directory: {agent_doc_root}")
    if not coverage_root.exists():
        issues.append(f"Missing coverage database directory: {coverage_root}")
    if not template_root.exists():
        issues.append(f"Missing coverage template directory: {template_root}")
    if not template_sim_root.exists():
        issues.append(f"Missing simulation template directory: {template_sim_root}")
    else:
        makefile_frv = template_sim_root / "makefileFRV"
        if not makefile_frv.exists():
            issues.append(f"Missing simulation makefile: {makefile_frv}")
    if not baseline_vdb.exists():
        issues.append(f"Missing baseline coverage database: {baseline_vdb}")
    if not rtl_root.exists():
        issues.append(f"Missing RTL root: {rtl_root}")

    return issues
