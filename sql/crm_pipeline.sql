-- Each row is one deal's stage at a recorded snapshot, not its final stage.
-- Calibration uses only outcomes already known at the planning cutoff.
WITH calibration AS (
 SELECT snapshot_stage,COUNT(*) AS resolved_deals,
 SUM(CASE WHEN outcome='won' THEN 1 ELSE 0 END) AS wins,
 (SUM(CASE WHEN outcome='won' THEN 1 ELSE 0 END)+2.0)/(COUNT(*)+4.0) AS win_probability
 FROM deal WHERE closed_on IS NOT NULL AND closed_on<=:cutoff
 AND snapshot_on<closed_on GROUP BY snapshot_stage
), open_pipeline AS (
 SELECT d.*,COALESCE(c.win_probability,0.5) AS win_probability,
 COALESCE(c.resolved_deals,0) AS calibration_sample
 FROM deal d LEFT JOIN calibration c USING(snapshot_stage)
 WHERE d.snapshot_on<=:cutoff AND (d.closed_on IS NULL OR d.closed_on>:cutoff)
 AND d.already_booked=0
)
SELECT lane_id,COUNT(*) AS open_deals,SUM(weekly_loads) AS unweighted_loads,
 SUM(weekly_loads*win_probability) AS expected_incremental_loads,
 MIN(calibration_sample) AS smallest_stage_sample
FROM open_pipeline GROUP BY lane_id ORDER BY lane_id;
