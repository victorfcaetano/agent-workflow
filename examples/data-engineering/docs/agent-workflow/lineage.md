# Schema and lineage

Both inputs are UTF-8 CSVs with an exact header row. The loader inserts customers before orders with SQLite foreign-key enforcement enabled. Each row belongs to one snapshot. [Inputs](../../data) · [Loader and schema](../../pipeline.py)

| Source | Destination | Rules |
| --- | --- | --- |
| `customers.csv` | `customers(customer_id, name)` | Nonblank text key and name. Each customer ID occurs once. |
| `orders.csv` | `orders(order_id, customer_id, status, amount_cents)` | Unique nonblank order ID. Customer ID references `customers`. Status is `paid` or `cancelled`. Amount is a nonnegative whole number of cents, supplied as ASCII digits and stored as a SQLite integer. |
| Customers joined to paid orders | `customer_sales(customer_id, paid_orders, revenue_cents)` | One row per customer. Count paid orders and sum their cents. Return zero for both measures when a customer has no paid orders. |

The join condition applies the paid-status filter before the left join produces unmatched customers. As a result, both a customer with only cancelled orders and one with no orders appear in the report. The database retains cancelled orders in the source table for reconciliation. [View definition](../../pipeline.py)
