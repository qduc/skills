# Design contract encoded by this evaluator

The evaluator observes the existing Responses-event normalizer. It requires
that normalizer to accept a vendor-lane value, use it for opaque native items
and encrypted-reasoning metadata, and retain the previous OpenAI lane as its
default. Calls use an untyped invocation because the lane argument is new while
the normalizer itself exists in the baseline.

This pins the shared-adapter design. A competent implementation could create a
separate adapter for the second provider and never extend the existing
normalizer; it could preserve the user-visible behavior yet fail this gate.
Record that outcome as a design-contract miss, not as proof that the candidate
replayed ciphertext incorrectly.

