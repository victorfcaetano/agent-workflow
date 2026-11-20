# Customer sales in SQLite

Build a local customer-level revenue report from two synthetic CSV files. The pipeline requires Python 3.11 or newer with the standard-library SQLite module.

From this directory, pass a new database path. The following commands build and query a local snapshot.

```console
python pipeline.py customer-sales.sqlite
python -c "import sqlite3; db = sqlite3.connect('customer-sales.sqlite'); print(db.execute('SELECT * FROM customer_sales ORDER BY customer_id').fetchall()); db.close()"
```

The pipeline reads the fixture CSVs under `data/`. To use another directory containing the same two filenames and headers, pass `--inputs` and that directory. The output path must be unused. A second run against an existing file exits with an error and preserves its contents.

Run the tests from this directory.

```console
python -m unittest discover -s tests -v
```

The registered `pipeline-tests` check runs the same suite with `agent-workflow verify .`. Every test writes to a temporary directory. With Agent Workflow installed, run `agent-workflow init .` to add host instructions and skills. The project context documents the data contract and expected results. [Context index](docs/agent-workflow/context-index.md)
