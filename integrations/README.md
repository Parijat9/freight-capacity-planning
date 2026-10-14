# Weekly planning workflow

The repository's scheduled CI rebuilds the synthetic analysis and retains the outputs.
A tenant workflow can use the same contract after source approval and sandbox testing.

1. Extract a dated TMS load snapshot and a read-only CRM snapshot to restricted storage.
2. Validate one row per lane/week, missing weeks, duplicate deal IDs and booking status.
3. Run the model and compare performance against the simple baselines.
4. Route material demand shifts and capacity shortfalls to the planning owner.
5. Copy the approved capacity rows into the workbook using `refresh-plan.ts`.
6. The planner reviews rates, demand and reservations, then records the approved decision.

The Office Script updates only Demand loads and Reserved loads by lane ID. It validates
the entire payload before writing, rejects duplicates or missing lanes, and preserves
formulas and unit-cost assumptions. Call it from Excel Online's Run script action with
a JSON array containing `lane_id`, `expected_loads`, `contracted_loads`.
The script source is supplied; live Excel Online execution is not claimed.

For Power Automate, use a scheduled trigger, retrieve the approved JSON from controlled
storage, run the script and route the review to the planner. Never store OAuth tokens
or tenant URLs in a public repository. API failures should stop publication of the new
plan rather than retain an unlabeled stale result.

## Delivery checkpoints

Operations signs off the booked-load definition. Sales confirms which opportunities
are incremental. Finance approves rates and the shortfall penalty. The planning owner
accepts the forecast limitations and records overrides. Review model error, spot usage,
unmet loads and override frequency after each cycle.

References: [Zoho CRM V8 records](https://www.zoho.com/crm/developer/docs/api/v8/get-records.html),
[Office Scripts with Power Automate](https://learn.microsoft.com/en-us/office/dev/scripts/develop/power-automate-integration).
