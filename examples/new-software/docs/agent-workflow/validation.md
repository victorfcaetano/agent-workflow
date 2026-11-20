# Validation

Run `python -m unittest discover -s tests -v` from the example root. The `page-range-tests` check runs this command for `agent-workflow verify .`. It covers sorting, merging, singleton formatting, wide ranges, and invalid tokens. [Registered check](../../agent-workflow.toml)

An acceptance check for the CLI is `python page_ranges.py "8,2-5,1,4"`. Its expected output is `1-5,8`.
