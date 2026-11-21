# Agent Workflow

Agent Workflow gives Claude Code and Codex a repository-scoped workflow for planning, implementation, verification, and handoff. A short instruction file points agents to shared skills and project context. The Python CLI installs and maintains those files and runs the checks your project registers.

## Initialize a project

You need Python 3.11 or later. The CLI uses the Python standard library at runtime. From this source checkout, initialize a sibling directory named `my-project`. The directory can be new or an existing repository. Change the path to use a different project.

**Windows PowerShell**

```powershell
python -m agent_workflow init ..\my-project
python -m agent_workflow doctor ..\my-project
```

**macOS or Linux**

```sh
python3 -m agent_workflow init ../my-project
python3 -m agent_workflow doctor ../my-project
```

To use the console command from other directories, install the checkout in a virtual environment. From this checkout, run the commands for your platform.

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\agent-workflow.exe init ..\my-project
```

**macOS or Linux**

```sh
python3 -m venv .venv
./.venv/bin/python -m pip install .
./.venv/bin/agent-workflow init ../my-project
```

You can also install a built wheel with `python -m pip install /path/to/agent_workflow-0.1.0-py3-none-any.whl`. The commands below assume the environment where you installed the CLI is active. From the checkout, activate it with `.\.venv\Scripts\Activate.ps1` in PowerShell or `. .venv/bin/activate` on macOS and Linux. You can also call the executable by its full path.

### Work with your agent

Open the target project in Claude Code or Codex. For a new project, ask the agent to onboard the project using your goals and constraints, then describe what you want to build. For an existing project, ask it to onboard the repository and record the architecture, domain rules, and validation commands it can verify. You can then work in natural language, for example, “Add the CSV export and verify the output with the project's checks.”

`init` installs the instruction blocks and skills, creates missing context files under `docs/agent-workflow/`, and starts onboarding at `pending` in `agent-workflow.toml`. The onboarding skill investigates the project, records `Verified`, `Hypothesis`, and `Open question` entries, and links the topics in `context-index.md`. Quick changes stay focused. Substantial changes use OpenSpec when configured or a local change record when it is unavailable.

## Commands

Run `agent-workflow <command> [project]`. The project defaults to the working directory. `version` takes no project argument.

| Command | Result | Exit status |
| --- | --- | --- |
| `install` | Add the managed root instruction blocks and host skills. | `0` on success, `1` on operation failure. |
| `init` | Install the assets and create missing onboarding and context starters. | `0` on success, `1` on operation failure. |
| `doctor` | Report executables on `PATH`, expected locations, manifest, configuration, and lock warnings. | `0` for informational results and warnings, `2` for errors. |
| `status` | Show onboarding state and local active change directories. | `0` on success, `2` on error. |
| `verify` | Run registered checks and report required and optional results. | `0` when required checks pass, `1` for a required check failure, `2` for missing or invalid check configuration. |
| `update` | Refresh unchanged managed content and report conflicts. | `0` on success, `1` for conflicts or operation failure. |
| `remove` | Remove unchanged managed assets and report modified assets it preserved. | `0` on success, `1` on operation failure. |
| `version` | Print the package version. | `0` on success. |

Invalid command-line syntax exits `2`. Put your validation commands in `[[checks]]` tables in `agent-workflow.toml`. Each entry specifies an executable and arguments as an array. You can also set the working directory, timeout, and whether the check is required. Check execution is explicit through `verify`. [Project checks and extensions](docs/extending.md#register-deterministic-checks)

### Update or remove the workflow

Install the newer package first, then run `agent-workflow update` in the target project. The manifest tracks each managed file or instruction block by its installed contents. If your changes overlap an update, the CLI preserves your version and writes the incoming copy under `.agent-workflow/updates/` for review. Store custom root instructions outside the managed blocks and use separately named project skills.

Run `agent-workflow remove` to uninstall unchanged managed files and blocks. It preserves customized assets, unowned files, and project-owned context and check configuration. Inspect preserved assets and update candidates before deciding whether to keep or merge them.

If a process was forcibly terminated, it can leave `.agent-workflow.lock` and a partially applied operation. Run `agent-workflow doctor` in the target project. It reports the lock and leaves cleanup to you. Confirm that no workflow mutation is still running, then inspect the working tree and `.agent-workflow/manifest.json` if present. Reconcile partial changes against your last known project state and remove the stale lock only after that inspection. Then retry the intended command.

If a rollback cannot restore an original file, the CLI reports a recovery artifact in `.agent-workflow/recovery/`. Run `agent-workflow doctor`, inspect the artifact's paths and saved bytes, then reconcile those files manually before retrying. The artifact is evidence for recovery, not an instruction to overwrite later project edits.

## Examples

Run `agent-workflow verify` from either example root after installing the CLI. Each example documents its app or pipeline and its expected results.

- A small Python application with unit tests and project context. [New software project](examples/new-software/)
- A SQLite pipeline with synthetic CSV input, documented lineage, and data-quality checks. [Data engineering project](examples/data-engineering/)

## Compatibility and contributing

The project targets Windows, macOS, and Linux. CI checks the CLI, examples, and packaging with Python 3.11 and 3.13. Actual skill discovery and behavior depend on the host release, project trust, and permissions, and require live verification in that host. The installer leaves user settings, permission rules, and existing hooks untouched. [Host compatibility](docs/compatibility.md)

Read the [architecture](docs/architecture.md) for installer ownership and workflow design. For development setup, tests, and pull requests, see [Contributing](CONTRIBUTING.md). To disclose a vulnerability privately, see the [security policy](SECURITY.md). The code is available under the [MIT License](LICENSE).
