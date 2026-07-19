# V5.7f JoinQuant Export Intake

This folder is the dedicated intake location for V5.7f platform replication exports.

Do not mix exports from bank, utilities, insurance, highway, telecom overlay or other strategies here.

Expected files after a JoinQuant V5.7f frozen-signal run:

```text
platform_exports_v57f/pending/result.csv
platform_exports_v57f/pending/transaction.csv
platform_exports_v57f/pending/position.csv
platform_exports_v57f/pending/log.txt
```

The Project Manager rule is strict:

```text
summary return alone is not enough
daily NAV attribution + transaction attribution + position attribution are required
```

