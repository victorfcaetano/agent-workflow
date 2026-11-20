# Selection rules

## Verified facts

Pages start at 1. Each comma-separated token is a positive page number or an inclusive ascending range. Duplicate and adjacent intervals collapse into one interval. A singleton prints as one number. The parser sorts interval endpoints and merges them without allocating an entry for every selected page. [Implementation](../../page_ranges.py)

The empty selection, empty tokens, descending ranges, negative numbers, and fractional pages are invalid. The tests cover a billion-page endpoint to exercise the interval representation. [Regression tests](../../tests/test_page_ranges.py)

## Open question

Should a future caller be able to supply a document length and reject out-of-bounds selections? The current CLI takes only the selection string.
