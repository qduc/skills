# Host inventory

For routing work on this machine, read the local inventory at
`../../../runtime/local-config/host-inventory.md` relative to this file if it
exists. That private snapshot is excluded from publication. Recheck dated
observations before relying on them.

On another installation, discover the host before routing agents:

1. Identify installed agent CLIs and their executable locations.
2. Check supported models and providers using each installed CLI's help and
   model-list commands.
3. Verify whether the orchestration host supports starting, prompting, waiting
   for, and resuming each agent. Distinguish installed tools from recognized kinds.
4. Record the verification date, capabilities, and observed limitations in the
   local inventory. Keep account details and credentials out of shared references.

Use [routing.md](routing.md) to select the appropriate capability for the task.
A local inventory records availability; it does not change the routing principles.
