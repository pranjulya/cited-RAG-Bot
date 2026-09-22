# JEV-01 — Shadow Decisions

## Typed probabilistic decisions

Jev is used for a narrow judgment, not prose generation. A Noul answer is the
probability that a yes/no statement is true. The application keeps this as a
normalized decision object instead of leaking TypeSafe's response schema into
the query pipeline.

## Shadow evaluation

Shadow mode runs a candidate decision beside the existing production path.
The candidate is measured against the baseline and golden labels, but cannot
change the user-visible result. This lets us measure agreement, errors,
latency, and calibration before choosing a threshold.

## Provider boundary

The TypeSafe HTTP shape belongs in one adapter. The application passes only the
question and its model-visible evidence labels/text. API keys and provider
payloads remain outside domain models, routes, logs, and public responses.

## Application ownership

Evidence IDs and citations are created and validated by the application. A Jev
provider failure is an operational observation, not proof of insufficient
evidence, so the existing deterministic path remains authoritative.
