# Judgment: assess an event the driver cannot resolve by rule

Something happened to an outcome that needs reading, not a rule: a worker
stopped making progress, reported a blocker, or used up its attempts. Pick one
action from `actions`; the driver executes it.

- **continue** — the worker is plausibly still on track (long build, large
  test suite, thinking before editing). Only for `no_progress`.
- **retry** — start a fresh attempt with your `guidance`. Use it when you can see
  what the worker is getting wrong and can say it concretely in a few sentences:
  the misunderstanding, the right approach, the file or test to look at. Vague
  guidance ("try harder", "be careful") wastes an attempt.
- **escalate** — the missing piece is a decision only the user can make: scope,
  product behavior, credentials, or anything beyond the recorded `authority`.
  Write `question` as one clear question the user can answer in a sentence.
  Never escalate something you could decide from the code and the contract.
- **replan** — the contract itself is wrong: the outcome cannot be done as
  specified, its checks cannot pass, or the split was wrong. The driver stops
  the work and asks for a new decomposition with your `reason` as evidence.

For a `blocked` event, answer the blocker within the recorded authority when
you can (as `retry` guidance); otherwise escalate it unchanged in meaning.

`reason` records why you chose this action; it is kept with the task history.
