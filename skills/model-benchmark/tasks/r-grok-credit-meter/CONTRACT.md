# Design contract encoded by this evaluator

The evaluator pins the status-bar presentation boundary: a supplied weekly
percentage must render as a rounded credit reading with an optional reset date,
and absent data must render nothing. The prop is passed through an untyped JSX
spread so the baseline still typechecks without this new presentation input.

This does **not** independently prove the source, polling cadence, authentication
handling, or account-switch behavior of the meter. A candidate that produces a
correct live meter through a different state path can fail this prop-level gate;
conversely, a candidate that only implements this display can pass it. The
originating change is the reference for the broader integration and blind review
must assess it. Report deterministic results with that limitation.

