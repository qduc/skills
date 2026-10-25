# Working in this repository

This repository holds agent skills under `skills/<name>/`. See
[README.md](README.md) for layout and setup.

## Before creating or changing a skill

Read the [incident index](incidents/README.md). Open every post-mortem that
lists the skill you're changing, or that involves the kind of rule you're adding
(gates, checks, retained state, delegation). Check your change against its
"Lessons for skill authors" and don't repeat those mistakes.

When a skill causes a new failure worth recording, write a post-mortem in
`incidents/` following the format in its README, and add it to the index.
