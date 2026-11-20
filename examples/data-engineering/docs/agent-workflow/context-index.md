# Customer sales project context

The pipeline loads a full synthetic snapshot into a new local SQLite file. A customer-level view summarizes paid orders. [Pipeline](../../pipeline.py)

| Topic | Project evidence |
| --- | --- |
| Input schema, relationships, and aggregation rules | [Schema and lineage](lineage.md) |
| Data-quality checks and expected output | [Validation](validation.md) |

## Open question

How should refunds affect revenue if they are introduced? The fixture and current loader accept `paid` and `cancelled` as the two order states.
