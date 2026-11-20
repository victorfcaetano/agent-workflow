# Validation

Run `python -m unittest discover -s tests -v` from the example root, or run `agent-workflow verify .` after installing the harness. The tests copy the synthetic CSVs to temporary storage before injecting invalid records. [Registered check](../../agent-workflow.toml) · [Pipeline tests](../../tests/test_pipeline.py)

## Expected snapshot

The fixture has four customers and five orders. Three paid orders total 3,800 cents. Query the view in customer ID order to compare it with the expected snapshot.

```sql
SELECT customer_id, paid_orders, revenue_cents
FROM customer_sales
ORDER BY customer_id;
```

| Customer | Paid orders | Revenue in cents |
| --- | ---: | ---: |
| C001 | 2 | 2000 |
| C002 | 1 | 1800 |
| C003 | 0 | 0 |
| C004 | 0 | 0 |

The suite checks the declared foreign key, referential integrity, integer storage, and result rows. It rejects an incorrect header, duplicate order IDs, orphaned orders, unsupported statuses, negative or fractional cents, and missing order IDs. Failed loads clean up their new output file. A pre-existing output survives a refused run. [Quality checks](../../tests/test_pipeline.py)
