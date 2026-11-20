# Page ranges

Normalize a comma-separated print selection into ascending, nonoverlapping ranges. Run this command from the example directory.

```console
python page_ranges.py "5,1-3,2,4-5,8"
```

The result is `1-5,8`. Invalid input produces a usage error and exit code 2.

Run the example's tests with Python 3.11 or newer.

```console
python -m unittest discover -s tests -v
```

With Agent Workflow installed, `agent-workflow init .` adds the host instructions and skills while preserving this project's configuration and context. Run `agent-workflow verify .` to execute the registered test suite. The project context records the selection rules and a possible next change. [Context index](docs/agent-workflow/context-index.md)
