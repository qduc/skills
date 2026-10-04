# Heal as you drive

This skill and the helper skills it drives (`herdr`, `term2`) have defects that
only show up in real use. The agent driving the skill **heals** them in-flow:
when you find a defect while coordinating, fix it in that same task, and don't
leave it behind as a workaround when repair is within existing authority.
Check the current task or explicitly applicable user preferences for that authority;
the skill grants none. Otherwise capture and defer the repair with a next step.
A heal never widens task authority or acceptance criteria.

A **defect** is evidence that the skill or a helper told you something false:
- a helper errors on valid input;
- a helper refuses an operation the evidence shows is safe;
- a helper reports a false positive or false negative;
- an instruction or host fact is contradicted by what you observed.

A manual workaround is the signature: an extra keypress, a blocker you had to
ignore, a result you re-derived by hand.

1. **Capture** an `incident` note at the next checkpoint (schema in
   [retro](retro.md)) with `heal: open`, the exact command and
   output, and the workaround you used.
2. **Heal by lane:**
   - *Host fact* (a tool quirk, model profile, path, or quota): correct its
     entry in the [host inventory](host-inventory.md).
   - *Instruction defect* (wording in this skill or a helper skill that is
     unclear, missing, or contradicted): make a small edit and mark it
     `<!-- lesson: <key> promoted <date> -->`.
   - *Helper defect* (a script under a skill's `scripts/`): add a test to that
     skill's suite that reproduces the observed output and fails, then fix the
     script. If your harness is review-only, route the fix to an implementer.
     Before changing a helper's CLI or output format, check for running
     consumers (for example `ps` for live invocations and other coordinators'
     watch commands), and keep the old form working or migrate them first.
     <!-- lesson: live-consumer-compat promoted 2026-09-29 -->
   - *Behavior rule* (changes planning, delegation, routing, verification, or
     stop behavior): record it in [Candidate experiments](experiments.md).
     It is an experiment, not a heal.
3. **Gate:** the owning skill's tests pass
   (`python3 -m unittest discover -s <skill-dir>/scripts`), and a changed
   instruction reads correctly in its context. Make a refusal accurate: fix what
   it detects and keep what it guards.
4. **Record:** set `heal: done` with the commit or changed paths.
   - If the heal would take more than about 30 minutes, or would change a
     contract other skills depend on, set `heal: deferred` with the next step.
   - Commit a heal by its paths (`git commit -- <paths>`). If a healed file also
     holds another session's uncommitted edits, leave the heal uncommitted and
     say so in the note.
5. **Announce** each heal in your next update to the user: the defect, its
   lane, and the evidence the fix works.

A heal is complete when its note reads `heal: done` with passing-test evidence,
or `heal: deferred` with a named next step. Before a session ends, move every
`heal: open` note to one of those two states. The [retro](retro.md)
handles lessons that recur across tasks, and pruning. Use the installed
`workflow-evolution` skill for authorized experiments.

