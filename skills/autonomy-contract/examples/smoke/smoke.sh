#!/bin/sh
# Smoke test of the autonomy-contract machinery on a small question unrelated
# to any experiment: "Does git worktree share hooks between worktrees?"
#
# The research decisions (claims, excerpts, findings) were made by an agent in
# an interactive first pass and are replayed here so the run is reproducible.
# The fetches and experiments are real. Needs network for 3 fetches of
# git-scm.com, plus git and python3. Writes runs/, store/, transcript.log here.
#
# Each step states the exit code it expects; the script stops on a mismatch.
set -u
cd "$(dirname "$0")"
LAB=../../scripts/lab.py
RAW=$(mktemp -d)
FETCHES=0
rm -rf runs store transcript.log
: > transcript.log

step() {  # step <expected-exit> <shell command...>
  want=$1; shift
  printf '$ %s\n' "$*" >> transcript.log
  out=$(sh -c "$*" 2>&1); got=$?
  printf '%s\n[exit %s]\n\n' "$out" "$got" >> transcript.log
  printf '%s\n[exit %s]\n' "$out" "$got"
  [ "$got" = "$want" ] || { echo "SMOKE FAIL: expected exit $want, got $got: $*"; exit 1; }
}

fetch() {  # fetch <url> <name>: real web call, counted outside the ledger
  FETCHES=$((FETCHES + 1))
  step 0 "curl -sfL '$1' -o '$RAW/$2.html' && echo fetched $1"
}

quoted() {  # quoted <name> <excerpt>: the excerpt really occurs in the fetched page
  step 0 "python3 - '$RAW/$1.html' <<'PY'
import html, re, sys
page = open(sys.argv[1], errors='ignore').read()
page = re.sub(r'<script.*?</script>|<style.*?</style>', '', page, flags=re.S)
text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', page)))
excerpt = '''$2'''
assert excerpt in text, 'EXCERPT NOT FOUND: ' + excerpt
print('excerpt found in page')
PY"
}

echo "== run 1: Does git worktree share hooks between worktrees?"
step 0 "python3 $LAB init runs/run1 --goal 'Does git worktree share hooks between worktrees?' --store store/knowledge.jsonl --max-cycles 2 --max-web 3 --max-minutes 20"
step 0 "python3 $LAB recall runs/run1"
step 0 "python3 $LAB add runs/run1 claim '{\"id\":\"C1\",\"text\":\"Linked worktrees run the same hooks as the main worktree by default (one shared hooks directory).\",\"status\":\"open\",\"why\":\"decides whether installing a hook once covers every worktree\"}'"
step 0 "python3 $LAB add runs/run1 claim '{\"id\":\"C2\",\"text\":\"Refutation candidate: each linked worktree has its own hooks directory under its private GIT_DIR.\",\"status\":\"open\",\"why\":\"if true, hooks must be installed per worktree\"}'"
step 0 "python3 $LAB log runs/run1 decide plan --data '{\"order\":[\"C1\",\"C2\"],\"method\":\"primary docs (git-scm.com), then a local experiment\"}'"
step 0 "python3 $LAB charge runs/run1 cycle --note 'C1+C2: read githooks and git-worktree docs, then experiment'"

step 0 "python3 $LAB charge runs/run1 web --note 'fetch https://git-scm.com/docs/githooks'"
fetch https://git-scm.com/docs/githooks githooks
quoted githooks 'By default the hooks directory is $GIT_DIR/hooks , but that can be changed via the core.hooksPath configuration variable'
step 0 "python3 $LAB add runs/run1 source - <<'J'
{\"id\":\"S1\",\"url\":\"https://git-scm.com/docs/githooks\",\"title\":\"githooks - Hooks used by Git\",\"kind\":\"primary\",\"excerpt\":\"By default the hooks directory is \$GIT_DIR/hooks , but that can be changed via the core.hooksPath configuration variable\",\"notes\":\"Read literally, a linked worktree has a private GIT_DIR, which would favour C2.\"}
J"
step 0 "python3 $LAB log runs/run1 verify tension --data '{\"claims\":[\"C1\",\"C2\"],\"note\":\"githooks says GIT_DIR/hooks; linked worktrees have a private GIT_DIR\"}'"

step 0 "python3 $LAB charge runs/run1 web --note 'fetch https://git-scm.com/docs/git-worktree'"
fetch https://git-scm.com/docs/git-worktree git-worktree
quoted git-worktree 'Path resolution via git rev-parse --git-path uses either $GIT_DIR or $GIT_COMMON_DIR depending on the path.'
quoted git-worktree 'In order to have worktree-specific configuration, you can turn on the worktreeConfig extension'
step 0 "python3 $LAB add runs/run1 source - <<'J'
{\"id\":\"S2\",\"url\":\"https://git-scm.com/docs/git-worktree\",\"title\":\"git-worktree - Manage multiple working trees\",\"kind\":\"primary\",\"excerpt\":\"Path resolution via git rev-parse --git-path uses either \$GIT_DIR or \$GIT_COMMON_DIR depending on the path.\",\"notes\":\"The page does not say which side hooks/ resolves to.\"}
J"
step 0 "python3 $LAB add runs/run1 source - <<'J'
{\"id\":\"S3\",\"url\":\"https://git-scm.com/docs/git-worktree\",\"title\":\"git-worktree - CONFIGURATION FILE\",\"kind\":\"primary\",\"excerpt\":\"In order to have worktree-specific configuration, you can turn on the worktreeConfig extension\"}
J"

step 0 "python3 $LAB log runs/run1 decide experiment --data '{\"claims\":[\"C1\",\"C2\"],\"why\":\"docs do not say where hooks/ resolves; a local repo settles it with no web budget\"}'"
mkdir -p runs/run1/experiments
step 0 "sh experiments/shared-hooks.sh 2>&1 | sed 's#/tmp/tmp\.[A-Za-z0-9]*#<tmp>#g' | tee runs/run1/experiments/shared-hooks.log"
step 0 "python3 $LAB add runs/run1 source '{\"id\":\"S4\",\"url\":\"file:experiments/shared-hooks.log\",\"title\":\"Local experiment: hook in main worktree, commit in linked worktree\",\"kind\":\"experiment\",\"excerpt\":\"linked --git-path hooks: <tmp>/main/.git/hooks\",\"notes\":\"Same log: HOOK pre-commit fired in <tmp>/linked. Script: examples/smoke/experiments/shared-hooks.sh\"}'"
step 0 "python3 $LAB add runs/run1 finding '{\"id\":\"F1\",\"claim_ids\":[\"C1\"],\"source_ids\":[\"S4\",\"S2\"],\"statement\":\"A hook in the main worktree .git/hooks fires for commits in a linked worktree; git rev-parse --git-path hooks in the linked worktree resolves to the main .git/hooks.\",\"confidence\":\"high\",\"kind\":\"evidence\",\"uncertainty\":\"One git version; the docs do not state the hooks/ resolution explicitly.\"}'"
step 0 "python3 $LAB add runs/run1 finding '{\"id\":\"F2\",\"claim_ids\":[\"C2\"],\"source_ids\":[\"S1\",\"S4\"],\"statement\":\"Contradiction resolved: githooks names GIT_DIR/hooks and a linked worktree has a private GIT_DIR, but hooks/ resolves through the common dir, so linked worktrees get no hooks directory of their own.\",\"confidence\":\"high\",\"kind\":\"evidence\",\"uncertainty\":\"Resolution rests on the experiment, not on documentation text.\"}'"
step 0 "python3 $LAB add runs/run1 claim '{\"id\":\"C1\",\"text\":\"Linked worktrees run the same hooks as the main worktree by default (one shared hooks directory).\",\"status\":\"supported\"}'"
step 0 "python3 $LAB add runs/run1 claim '{\"id\":\"C2\",\"text\":\"Refutation candidate: each linked worktree has its own hooks directory under its private GIT_DIR.\",\"status\":\"contradicted\"}'"
step 0 "python3 $LAB log runs/run1 verify challenge --data '{\"P1_assumption\":\"assumed core.hooksPath unset\",\"P3_consistency\":\"S1 vs S4 recorded as F2\",\"P4_scope\":\"can one worktree opt out? added C3\"}'"
step 0 "python3 $LAB add runs/run1 claim '{\"id\":\"C3\",\"text\":\"One worktree can use different hooks via extensions.worktreeConfig plus a per-worktree core.hooksPath.\",\"status\":\"open\",\"why\":\"raised by the P4 scope challenge\"}'"
step 0 "python3 $LAB check runs/run1"

step 0 "python3 $LAB charge runs/run1 cycle --note 'C3: counter-evidence and opt-out check in git-config docs'"
step 0 "python3 $LAB charge runs/run1 web --note 'fetch https://git-scm.com/docs/git-config'"
fetch https://git-scm.com/docs/git-config git-config
quoted git-config '--worktree Similar to --local except that $GIT_DIR/config.worktree is read from or written to if extensions.worktreeConfig is enabled.'
step 0 "python3 $LAB add runs/run1 source - <<'J'
{\"id\":\"S5\",\"url\":\"https://git-scm.com/docs/git-config\",\"title\":\"git-config - the --worktree option\",\"kind\":\"primary\",\"excerpt\":\"--worktree Similar to --local except that \$GIT_DIR/config.worktree is read from or written to if extensions.worktreeConfig is enabled.\"}
J"
step 0 "python3 $LAB add runs/run1 finding '{\"id\":\"F3\",\"claim_ids\":[\"C3\"],\"source_ids\":[\"S3\",\"S5\"],\"statement\":\"Docs suggest one worktree can opt out of the shared hooks: enable extensions.worktreeConfig, then set core.hooksPath with git config --worktree. Not tested in this run.\",\"confidence\":\"low\",\"kind\":\"inference\",\"uncertainty\":\"Inference across two doc passages; the cycle budget was spent before an experiment.\"}'"
step 0 "python3 $LAB add runs/run1 claim '{\"id\":\"C3\",\"text\":\"One worktree can use different hooks via extensions.worktreeConfig plus a per-worktree core.hooksPath.\",\"status\":\"unresolved\"}'"

echo "== budget refusal: a fourth web call"
step 3 "python3 $LAB charge runs/run1 web --note 'would fetch a forum thread as extra counter-evidence'"
echo "== stop rule"
step 10 "python3 $LAB check runs/run1"

echo "== learn: write knowledge to the store"
step 0 "python3 $LAB add runs/run1 knowledge '{\"kind\":\"finding\",\"finding_ids\":[\"F1\",\"F2\"],\"statement\":\"git worktree: linked worktrees share the main repository hooks directory by default (git rev-parse --git-path hooks resolves to the common .git/hooks), so a hook installed once fires in every worktree.\",\"confidence\":\"high\",\"tags\":[\"git\",\"worktree\",\"hooks\",\"core.hooksPath\"]}'"
step 0 "python3 $LAB add runs/run1 knowledge '{\"kind\":\"question\",\"finding_ids\":[\"F3\"],\"statement\":\"Can one git worktree use different hooks by enabling extensions.worktreeConfig and setting core.hooksPath with git config --worktree?\",\"tags\":[\"git\",\"worktree\",\"hooks\",\"worktreeConfig\",\"core.hooksPath\"]}'"
step 0 "python3 $LAB add runs/run1 knowledge '{\"kind\":\"lesson\",\"statement\":\"For behaviour of a local tool, a 10-line local experiment settled what the official docs left ambiguous, at zero web cost. Try the experiment before spending web calls on forums.\",\"evidence\":\"run1: githooks says GIT_DIR/hooks, ambiguous for linked worktrees; experiments/shared-hooks.sh resolved it.\",\"tags\":[\"method\",\"experiment\",\"budget\"]}'"
step 0 "cp brief-run1.md runs/run1/brief.md"
step 0 "python3 $LAB validate runs/run1"

echo "== fault injection on a copy of run 1"
step 0 "cp -r runs/run1 runs/run1-fault-injection"
step 0 "python3 $LAB add runs/run1-fault-injection finding '{\"id\":\"F9\",\"claim_ids\":[\"C1\"],\"source_ids\":[\"S99\"],\"statement\":\"Injected fault: cites a source id that was never recorded.\",\"confidence\":\"high\",\"uncertainty\":\"none\"}'"
step 0 "echo 'Injected: see https://example.com/never-fetched' >> runs/run1-fault-injection/brief.md"
step 4 "python3 $LAB validate runs/run1-fault-injection"
step 0 "python3 $LAB audit runs/run1 --observed-web $FETCHES"

echo "== run 2: a later run reads run 1's knowledge back"
RUN1_FETCHES=$FETCHES
step 0 "python3 $LAB init runs/run2 --goal 'Can one git worktree run different hooks from the other worktrees of the same repository?' --store store/knowledge.jsonl --max-cycles 2 --max-web 1 --max-minutes 15"
step 0 "python3 $LAB recall runs/run2"
QID=$(python3 -c "import json;print([e['id'] for e in map(json.loads,open('store/knowledge.jsonl')) if e['kind']=='question'][0])")
FID=$(python3 -c "import json;print([e['id'] for e in map(json.loads,open('store/knowledge.jsonl')) if e['kind']=='finding'][0])")
LID=$(python3 -c "import json;print([e['id'] for e in map(json.loads,open('store/knowledge.jsonl')) if e['kind']=='lesson'][0])")
step 0 "python3 $LAB log runs/run2 observe knowledge_used --data '{\"ids\":[\"$FID\",\"$QID\",\"$LID\"],\"why\":\"$FID gives the default (shared hooks); $QID is this goal, left open by run1 with sources; $LID says run the experiment before spending web calls\"}'"
step 0 "python3 $LAB add runs/run2 claim '{\"id\":\"C1\",\"text\":\"With extensions.worktreeConfig enabled, git config --worktree core.hooksPath makes one linked worktree use a different hooks directory.\",\"status\":\"open\"}'"
step 0 "python3 $LAB add runs/run2 claim '{\"id\":\"C2\",\"text\":\"Refutation candidate: setting core.hooksPath from one worktree also changes the hooks of the other worktrees.\",\"status\":\"open\"}'"
step 0 "python3 $LAB charge runs/run2 cycle --note 'C1+C2: experiment first (lesson $LID), sources reused from $QID'"
mkdir -p runs/run2/experiments
step 0 "sh experiments/per-worktree-hooks.sh 2>&1 | sed 's#/tmp/tmp\.[A-Za-z0-9]*#<tmp>#g' | tee runs/run2/experiments/per-worktree-hooks.log"
step 0 "python3 $LAB add runs/run2 source - <<'J'
{\"id\":\"S1\",\"url\":\"https://git-scm.com/docs/git-config\",\"title\":\"git-config - the --worktree option (from the knowledge store)\",\"kind\":\"primary\",\"via\":\"$QID\",\"excerpt\":\"--worktree Similar to --local except that \$GIT_DIR/config.worktree is read from or written to if extensions.worktreeConfig is enabled.\"}
J"
step 0 "python3 $LAB add runs/run2 source '{\"id\":\"S2\",\"url\":\"file:experiments/per-worktree-hooks.log\",\"title\":\"Local experiment: per-worktree core.hooksPath in wt-b only\",\"kind\":\"experiment\",\"excerpt\":\"wt-b: --git-path hooks = <tmp>/alt-hooks\",\"notes\":\"Same log: main and wt-a print HOOK shared pre-commit fired; wt-b prints HOOK alternate pre-commit fired.\"}'"
step 0 "python3 $LAB add runs/run2 finding '{\"id\":\"F1\",\"claim_ids\":[\"C1\"],\"source_ids\":[\"S2\",\"S1\"],\"statement\":\"After git config extensions.worktreeConfig true, running git config --worktree core.hooksPath <dir> inside one linked worktree makes only that worktree use <dir>.\",\"confidence\":\"high\",\"kind\":\"evidence\",\"uncertainty\":\"One git version (see log). Older Git versions refuse repositories with this extension.\"}'"
step 0 "python3 $LAB add runs/run2 finding '{\"id\":\"F2\",\"claim_ids\":[\"C2\"],\"source_ids\":[\"S2\"],\"statement\":\"The other worktrees kept the shared hooks: main and wt-a still ran the shared pre-commit hook.\",\"confidence\":\"high\",\"kind\":\"evidence\",\"uncertainty\":\"Without extensions.worktreeConfig, --worktree behaves like --local and would change the shared config; not exercised here.\"}'"
step 0 "python3 $LAB add runs/run2 claim '{\"id\":\"C1\",\"text\":\"With extensions.worktreeConfig enabled, git config --worktree core.hooksPath makes one linked worktree use a different hooks directory.\",\"status\":\"supported\"}'"
step 0 "python3 $LAB add runs/run2 claim '{\"id\":\"C2\",\"text\":\"Refutation candidate: setting core.hooksPath from one worktree also changes the hooks of the other worktrees.\",\"status\":\"contradicted\"}'"
echo "== stop rule: every claim resolved after one cycle and zero web calls"
step 10 "python3 $LAB check runs/run2"
step 0 "python3 $LAB add runs/run2 knowledge '{\"kind\":\"finding\",\"finding_ids\":[\"F1\",\"F2\"],\"statement\":\"git worktree: one linked worktree can use its own hooks via git config extensions.worktreeConfig true plus git config --worktree core.hooksPath <dir>; other worktrees keep the shared hooks.\",\"confidence\":\"high\",\"tags\":[\"git\",\"worktree\",\"hooks\",\"worktreeConfig\",\"core.hooksPath\"]}'"
step 0 "cp brief-run2.md runs/run2/brief.md"
step 0 "python3 $LAB validate runs/run2"
step 0 "python3 $LAB audit runs/run2 --observed-web $((FETCHES - RUN1_FETCHES))"
step 0 "grep -h '\"knowledge_recalled\"\|\"knowledge_used\"' runs/run2/log.jsonl"
rm -rf "$RAW"
echo "SMOKE OK: $FETCHES real fetches"
