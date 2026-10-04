#!/usr/bin/env bash
# Open-ended feature task: there is no hidden test, because any hidden test
# would have to name modules and an API the candidate was never told to invent.
# The gate is therefore deliberately weak — it proves the candidate did not
# leave the message-rendering suite broken, nothing more. Quality on this task
# is settled by the blind judge, not here.
set -uo pipefail
NODE_ENV=test ./node_modules/.bin/vitest run source/components/message --reporter=dot
