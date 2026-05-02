# Visualizations

This directory contains exported figures used in the drift analysis and service
monitoring review.

Included files:

- `dashboard-screenshot.png`: Grafana dashboard view after simulated API traffic
- `input_length_drift.png` and `input_length_drift.svg`: drift in query length
  across production windows
- `response_length_drift.png` and `response_length_drift.svg`: drift in answer
  length across production windows
- `retrieval_score_drift.png` and `retrieval_score_drift.svg`: drift in top
  retrieval similarity score
- `integrity_anomalies.png` and `integrity_anomalies.svg`: anomaly counts for
  empty inputs, oversized inputs, and low-score retrieval events

The PNG files are intended for direct viewing in reports. The SVG files are
included for high-resolution reuse in slides or documents.
