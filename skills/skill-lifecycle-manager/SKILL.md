---
name: skill-lifecycle-manager
description: Manage Bank Quant V5 skill lifecycle and dynamic updates. Use when a skill becomes unavailable, stale, inaccurate, blocked by API or data-source changes, when a non-skill workaround succeeds and should be converted into a reusable skill, when deprecating or disabling a skill, or when updating skill status, replacement routes, lessons learned, and validation rules.
---

# V5 Skill Lifecycle Manager

## Role

Maintain the V5 skill system as a living research operating environment.

## Mission

Keep skills accurate, usable, and aligned with current data-source reality. Convert repeated successful non-skill work into new reusable skills.

## Skill Status

Use these status labels:

- `active`: skill is current and recommended.
- `limited`: skill works only under explicit constraints.
- `deprecated`: skill should not be used for new work, but remains useful as historical reference.
- `disabled`: skill is known to be unavailable or unsafe for current work.
- `candidate`: a successful non-skill workflow should be converted into a skill after review.

## Disable Rules

Mark a skill or sub-capability as `disabled` when:

- its primary API or data source is no longer available;
- its output is no longer reproducible;
- it depends on credentials, permissions, or files that are unavailable;
- it creates unacceptable leakage, look-ahead, survivorship, or maintenance risk;
- a newer skill provides a safer replacement.

Do not delete the old skill by default. Keep it as historical evidence unless the user explicitly asks to remove it.

## Non-Skill Success Rule

When a task succeeds without an existing skill:

1. Record what worked.
2. Identify the repeatable procedure.
3. Identify inputs, outputs, guardrails, and failure modes.
4. Decide whether it should become a new skill.
5. If yes, create a candidate skill with concise instructions.
6. Validate the new skill with the skill validator.
7. Update the project context and routing rules.

## Update Workflow

```text
Detect skill issue or successful workaround
  -> classify status
  -> document reason
  -> define replacement route
  -> update affected SKILL.md files
  -> update config/v5_context.json
  -> validate skills
  -> run project tests
  -> record outcome
```

## Required Output

```text
Skill:
Previous Status:
New Status:
Reason:
Replacement Route:
Files Updated:
Validation:
Lessons Learned:
Next Action:
```

## Guardrails

- Do not keep using a failed skill just because it exists.
- Do not silently bypass a failed skill without recording the reason.
- Do not promote a workaround into a skill unless it is repeatable.
- Do not mark a skill disabled only because one run failed; distinguish transient errors from structural unavailability.
- Always preserve source, date, and reason for lifecycle changes.
