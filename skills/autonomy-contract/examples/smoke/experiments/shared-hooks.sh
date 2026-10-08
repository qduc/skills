#!/bin/sh
# Does a hook installed in the main worktree fire in a linked worktree?
set -e
d=$(mktemp -d); cd "$d"
git init -q main && cd main
git -c user.email=a@b -c user.name=x commit -q --allow-empty -m init
printf '#!/bin/sh\necho "HOOK pre-commit fired in $(pwd)"\n' > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
git worktree add -q ../linked
cd ../linked
echo "git version: $(git --version)"
echo "linked --git-dir:        $(git rev-parse --git-dir)"
echo "linked --git-path hooks: $(git rev-parse --git-path hooks)"
git -c user.email=a@b -c user.name=x commit -q --allow-empty -m from-linked 2>&1
