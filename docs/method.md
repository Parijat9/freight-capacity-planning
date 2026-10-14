# Planning assumptions

## Time and grain

One row represents one lane and a Monday-start week. The sample spans 116 weeks from
1 July 2024. Forecast evaluation trains on 104 weeks and holds out the next 12.
The operational plan is for 21 September 2026, using observations through 14 September
and a CRM cutoff of 20 September. Historical values represent booked-load demand.

## Metrics

WAPE = sum absolute forecast errors / sum actual loads. It is unavailable when actual
loads sum to zero. Portfolio WAPE is calculated from all errors and loads, not by
averaging lane percentages. The residual band uses the recent rolling one-step
absolute errors and a finite-sample 90% quantile. Applying it to a 12-week horizon is
an approximation; the observed coverage makes that weakness visible. A production
version should calibrate by horizon and monitor shifts before using the bands for commitments.

## CRM interpretation

Calibration records retain the stage seen at a past snapshot and the later resolved
outcome. Using the final Closed Won stage as a predictor would leak the answer.
The mock data has 240 resolved opportunities and 24 open ones. A stage with no resolved
observations uses the prior mean of 0.5. This uncertainty should trigger commercial review.

Standard Zoho Deals fields do not provide lane, weekly load count, booking status or
historical stage snapshots. Map approved custom fields and retain snapshots before
using live CRM data. `crm.py` deliberately does not infer these values from deal amount.
Deals already included in the booked-demand series must be excluded from incremental demand.

## Decision assumptions

Contract cost is $820 per reserved load, spot cost $1,100, and unmet-load penalty $1,900.
The planner buys spot only if its cost is below the penalty. These values are editable
illustrations. The optimizer compares empirical residual demand scenarios and allows
unused reservations. It does not model lane substitution, correlated network shocks,
driver hours, equipment compatibility, tender rejection or multi-week contracts.

The generator contains annual seasonality similar to the model's features. That is a
favorable setting and limits generalization. L06 adds a late shift to expose failure.
Use independently sourced history and multiple rolling holdouts before making commercial
claims. No actual operating savings or forecasting improvements are attributed to an employer.
