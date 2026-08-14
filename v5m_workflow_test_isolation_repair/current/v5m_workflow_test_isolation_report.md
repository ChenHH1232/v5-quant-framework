# V5m Workflow Test Isolation Repair

- Unit test mode is isolated from the formal `current` directory.
- Production gate was rebuilt only after actual Fast and Standard test executions returned zero.
- Extended remains `not_run` and does not block the production gate.
