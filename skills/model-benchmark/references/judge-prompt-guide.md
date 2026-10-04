# Blind LLM Judge Prompting Guide

When comparing model outputs and agent diffs, use an independent judge model with full anonymization.

## Anonymization Protocol

1. Strip any commit messages, harness prefixes (`[Pi]`, `[Term2]`, `[Codex]`), or author markers.
2. Label diffs as `candidate-A.diff`, `candidate-B.diff`, etc.
3. Shuffle the order of candidates between runs to avoid positional bias.

---

## Standard Judge Prompt Template

```markdown
Review candidate-A.diff, candidate-B.diff, and candidate-C.diff as anonymized solutions to this task:

<TASK_PROMPT>
[Insert exact task prompt here]
</TASK_PROMPT>

Do not inspect other directories or attempt to identify harnesses/models. 
Judge each candidate along the following dimensions:
1. Functional Correctness: Does it solve the exact problem without introducing subtle bugs?
2. Backward & Forward Compatibility: Are schemas, events, and API boundaries preserved?
3. Scope Discipline: Is the diff minimal and focused, or does it include unnecessary refactors?
4. Test Quality: Are the added tests robust, testing at appropriate public boundaries without brittle implementation coupling?
5. Code Style & Maintainability: Does the code adhere to the codebase's existing conventions?

Scoring instructions:
- Score each candidate out of 10.
- Provide concrete findings for each candidate with specific line/function citations.
- Rank the candidates (e.g., A > B > C).
- State clearly if there is a tie.
```

---

## Judge Execution Examples

Keep judge execution tool-free. Diff collection, empty/duplicate detection,
typechecking, evaluator tests, totals, and ranking are deterministic benchmark
work; provide their results to the judge rather than letting an expensive model
re-run them. In Claude CLI, `--allowed-tools` changes approval behavior but does
not restrict tool availability. Use `--tools ""` for a self-contained prompt.

### Executing with Claude
```bash
claude --print --model opus --effort high --disable-slash-commands --tools "" \
  < judge-prompt.txt > claude-verdict.txt
```

### Executing with Gemini / Antigravity Subagent
Delegate to a `research` subagent with pro model:
```python
# Pass judge prompt and candidate diffs into prompt
```
