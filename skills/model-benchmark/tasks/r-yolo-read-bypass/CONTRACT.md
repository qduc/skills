# Design contract encoded by this evaluator

The evaluator asserts the fix lives in the read tools' own approval decision:
`createReadFileToolDefinition({ settingsService })` must return `false` from
`needsApproval` for an outside-workspace path when `shell.autoApproveMode`
is `'always'`, while `createCreateFileToolDefinition` must still return
`true` for outside-workspace writes in the same mode.

**Caveat for honest reporting.** The yolo read bypass could equally be
implemented at the approval-policy layer (the agent's tool-dispatch gate
consulting auto-approve mode before asking `needsApproval`). A candidate that
fixes the symptom that way would fail this gate despite behaving correctly,
because the gate only observes the tools' own `needsApproval`. Report any such
failures with this caveat; do not count them as incorrect fixes. The write pin
is an invariant guard: a fix that makes yolo bypass *writes* too fails it at
the fix commit.
