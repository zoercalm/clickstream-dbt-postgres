# Range reprocessing and journey grain

Grain is one row per visit. Cart entries are ordered by event sequence and hit ID, so ties are deterministic. An order is counted only within its visit; this is not cross-device attribution.

Each day replaces hits then visits and inserts visits then hits in one PostgreSQL transaction. Its checkpoint commits with its data. A process interrupted after a commit skips completed dates only when --resume is requested for the same batch. The session lock remains held while the dbt subprocess builds the mart. Database crash durability uses PostgreSQL defaults; this demo does not implement distributed leases.

The dbt incremental pre-hook deletes all mart rows in the reloaded date range, so visits removed from the source do not survive in reporting. Missing raw data outside the requested range remains an external-source reconciliation concern. CLI failure is visible as a nonzero exit; an orchestrator can send an alert, but no transport is bundled.

Reference: https://docs.getdbt.com/docs/build/incremental-models
