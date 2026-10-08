#!/bin/sh
# Can one linked worktree use a different hooks directory from the others?
set -e
d=$(mktemp -d)
trap 'rm -rf "$d"' EXIT
trap 'exit 130' INT TERM HUP
cd "$d"
git init -q main && cd main
git -c user.email=a@b -c user.name=x commit -q --allow-empty -m init
printf '#!/bin/sh\necho "HOOK shared pre-commit fired"\n' > .git/hooks/pre-commit
mkdir -p ../alt-hooks
printf '#!/bin/sh\necho "HOOK alternate pre-commit fired"\n' > ../alt-hooks/pre-commit
chmod +x .git/hooks/pre-commit ../alt-hooks/pre-commit
git worktree add -q ../wt-a
git worktree add -q ../wt-b
git config extensions.worktreeConfig true
(cd ../wt-b && git config --worktree core.hooksPath "$d/alt-hooks")
echo "git version: $(git --version)"
for w in main wt-a wt-b; do
  cd "$d/$w"
  echo "$w: --git-path hooks = $(git rev-parse --git-path hooks)"
  echo "$w: commit ->"
  git -c user.email=a@b -c user.name=x commit -q --allow-empty -m "from-$w" 2>&1
done
