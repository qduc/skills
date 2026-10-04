# Design contract encoded by this evaluator

The evaluator uses the settings picker’s existing rendered interface and
requires a configured credential to be masked rather than truncated or echoed.
It does not require a particular secret-classification helper or storage
strategy.

The originating fix also prevents completion from putting a stored credential
into an editor buffer. That is a related protection, but it is deliberately not
encoded here: this task’s prompt and gate concern terminal disclosure in the
picker. Do not read a passing result as proof that every credential-editing path
is safe.

