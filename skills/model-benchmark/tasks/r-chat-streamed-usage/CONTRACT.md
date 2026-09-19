# Design contract encoded by this evaluator

The evaluator asserts the observable wire effect: the chat-completions request
body must contain `stream_options: { include_usage: true }` (or an equivalent
that a server override leaves in place), and the model must report usage from
a terminal chunk carrying an empty `choices` array.

This is a wire-format contract, not a naming lottery: any fix that makes the
status bar receive token counts must put `include_usage` into the streamed
request, and any placement that reaches the request body satisfies the test.
The commit's own implementation places it before `providerOptions` so a
provider can override; the evaluator does not pin that placement.

Known acceptable alternatives that still pass: setting the flag via a
provider-specific override, or via a wrapper around the request builder.
