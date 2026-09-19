# Design contract encoded by this evaluator

The evaluator observes the existing per-request generation-budget object. It
requires verbose reasoning to be truncated at its retention cap, to return the
retained prefix to its caller, and not to consume the aggregate visible-output
budget. It also pins that the visible-text cap remains fail-closed.

This is not a naming lottery: the class and its observation methods already
exist at the baseline. It nevertheless chooses the budget-object seam. A
candidate could instead catch the budget failure at a higher streaming layer
and continue the turn; that could repair the reported symptom but would fail
this evaluator. Report such a result as an alternative design, not an
incorrect diagnosis.

