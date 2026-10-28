# Optional personal coordinator profiles

These are **opt-in personal instructions**, not skills, account credentials or
host profiles. They are never installed by discovery or the default workspace
generator. [Qduc's coordinator profile](qduc-coordinator.md) preserves a particular
collaboration style; other users should not inherit its permissions or model choices.

Carrying the Term2 and skill repositories preserves software and these preferences,
**not a configured/recovered coordinator**. It carries no prior tasks, history,
provider login, Discord token, host capability evidence or boot/service setup.
Use the intended committed revisions: a remote clone/release may lag your local
branch. Revalidate this setup on the new host rather than copying old host facts.

## New host: opt into Qduc's pane-coordinator workflow

Commands below are setup instructions, not an installer. Review paths and existing
files first; the examples assume a fresh home with no existing skills symlink or
workspace. Do not replace an existing global AGENTS or host profile. This profile
is applied to **one coordinator workspace**, not globally to every agent/worker.

1. **Prepare the host and Term2.** Follow the carried Term2 checkout's `README.md`
   (Develop from source) and its platform instructions. At the time of writing that
   means Node 24 and pnpm 11, Python 3, Git and, on Linux, `bubblewrap`, `socat` and
   `ripgrep`. Install a compatible Herdr separately: its skill is not its binary.
   Set your Git identity. Keep coordinator, bridge and workers under the same OS
   user and normal absolute, user-owned mode-0700 `XDG_RUNTIME_DIR`.
   ```sh
   SRC="$HOME/term2"                 # absolute carried source checkout
   SKILLS="$HOME/qduc-skills"        # absolute carried skill checkout
   WORKSPACE="$HOME/coord/term2"     # new/empty coordinator workspace
   (cd "$SRC" && pnpm install --frozen-lockfile && pnpm build && npm link)
   mkdir -p "$HOME/.agents"
   ln -s "$SKILLS/skills" "$HOME/.agents/skills"  # destination must be absent
   ```
   `npm link` exposes the built package's `term2` executable for pane helpers.
   Neither cloning nor linking logs into a provider, starts Herdr, creates a bot,
   authorizes paid routes, or installs auto-start services.
2. **Discover, don't transplant, host setup.** Read
   [coordinator-setup](../skills/coordinator-setup/SKILL.md), including its selected
   adapter guidance. Start with its read-only probe:
   ```sh
   python3 "$SKILLS/skills/coordinator-setup/scripts/host_profile.py" discover
   ```
   Validate the installed Herdr pane operations/help and actual Term2 executable.
   Save verified capabilities using that skill's host-profile instructions
   (normally `~/.config/coordinator/host.json`), preserving unknown/unavailable
   capabilities. Discovery output alone does not establish a usable worker route.
   Choose the hand-supervised pane route, not the driven-runtime driver interview.
3. **Authenticate privately and validate models.** For the preferred subscription
   route, run `term2 --codex-login` locally and complete browser/terminal setup;
   use `term2 --list-models` to check available IDs. Keep tokens out of prompts,
   this repository and reports. Don't substitute a PAYG route without permission.
4. **Generate the standard workspace, then explicitly opt in once.**
   ```sh
   python3 "$SKILLS/skills/coordinator-setup/scripts/init_workspace.py" \
     "$WORKSPACE" --project term2 --source-checkout "$SRC"
   cat "$SKILLS/profiles/qduc-coordinator.md" >> "$WORKSPACE/AGENTS.md"
   git -C "$WORKSPACE" add AGENTS.md
   git -C "$WORKSPACE" commit -m "Opt into Qduc's personal coordinator profile"
   ```
   The unchanged generator creates the normal scaffold and initial commit first.
   Appending the profile is the opt-in, not an idempotent installer: don't repeat
   it on an already customized workspace. Review/merge later profile changes by
   hand. Keep project-specific decisions in the generated `decisions/README.md`.
   Term2 loads the current workspace's AGENTS in its prompt; it does not implicitly
   load the sibling source checkout's AGENTS or inject this profile into workers.
5. **Start the coordinator interactively.** Replace `MODEL_ID` with an available,
   authorized ID; do not add a positional prompt (that selects batch mode).
   ```sh
   cd "$WORKSPACE"
   term2 --provider codex --model MODEL_ID --reasoning high \
     --control-socket=coord --discord-input
   ```
   Alternatively use `/bridge connect coord` in the intended existing TUI.
   Ask it to use `supervise-panes` and `herdr`. Keep this session running.
6. **Configure Discord through the existing Term2 documentation.** Read
   `$SRC/docs/reference/discord-bridge.md`, especially its first-run checklist;
   don't infer current schema/transport behavior from an old profile. That checklist
   covers bot creation/installation, channel permissions and message-content access,
   your human/channel IDs, and a private config with a fresh absolute private state
   directory. Use its private token enrollment (`term2 discord --save-token`) and
   start the bridge (`term2 discord`) in a second terminal, using the same absolute
   config path for both if customized. Never put a token in JSON, this profile or
   chat. Check `/bridge status` and `term2 control list --status` locally.
   Discord cannot satisfy local approval/question prompts; inspect the terminal if
   a request stalls. Do not enable blanket approvals just to hide a setup problem.
7. **Verify the real workflow, then call it working.** From the configured human in
   the private channel, send a harmless request asking for an explicit
   `discord_send` reply. Then ask for a small read-only task delegated to one pane
   worker (for example, identify the project's documented build command and report
   it with a source path). Observe actual worker admission, coordinator inspection
   of the result and a Discord report. Verify later modifying work with the repo's
   normal build/test/integration commands. Record what was actually observed and
   any limits; file copies, a discovered executable or fixture checks alone do not
   demonstrate end-to-end Discord/provider behavior or reboot recovery.

To use only the generic scaffold, omit the append/opt-in commit in step 4; it does
not acquire this person's permissions. To opt out later, review/remove the appended
personal section from the workspace AGENTS, leaving its generic scaffold and other
work intact, then start a fresh/rebuilt session. Already loaded instructions are not
changed merely by editing files. No credentials, transcripts or task logs are needed
to reproduce the collaboration style, but identical model behavior is not promised.
