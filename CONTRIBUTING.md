# Contributing

Use GitHub issues for bug reports and feature proposals. Include the behavior you expected, what you observed, and the relevant platform and Python version. Use the private reporting process for vulnerabilities. [Security policy](SECURITY.md)

1. Fork or clone the repository, create a branch, and set up a Python 3.11+ virtual environment.
2. Make a focused change. Add a regression test when existing tests would miss the behavior. Keep runtime dependencies in the standard library and keep the two host copies of shared skills in sync.
3. From the checkout root, run the package tests and build checks in the virtual environment.

   ```sh
   python -m pip install build twine
   python -m unittest discover -s tests -v
   python -m build
   python -m twine check --strict 'dist/*'
   python -m pip install .
   agent-workflow verify examples/new-software
   agent-workflow verify examples/data-engineering
   ```

4. Open a pull request describing the problem, the change, and what you verified. Note platform-specific skips and any behavior that needs a live host session to verify. Link the related issue when one exists.

For lifecycle changes, test in a temporary target project and keep ownership of existing content intact. Include sample config or example updates when a public interface changes. Follow the [Code of Conduct](CODE_OF_CONDUCT.md) when participating in the project.
