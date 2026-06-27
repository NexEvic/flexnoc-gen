# 001 Sparse Connectivity Stale Routes

## Symptom

FlexNoC `exportVerilog` fails at PDD load or structure stability check:

```text
[E] Element '/<project>_struct' is not stable.
  | ISSUE: A Node has not been placed on any route.
  | ISSUE: Incompatible settings '<target_a>, <target_b>' for parameter '...datapathRoute..(<initiator>/I/0)'.
  | ISSUE: The switch '<switch>' can be split into ...
```

## Trigger Pattern

The DSL uses sparse connectivity, for example:

```python
noc.connect_all()
noc.disconnect("soc_ext_i1", "ddr_o0")
noc.disconnect("soc_ext_i1", "cfg_o1")
```

or the equivalent explicit `connect()` calls. The generated specification layer marks some initiator-target pairs as `False`, but the architecture layer still contains datapath routes for those disconnected pairs.

## Required Debug Steps

1. Reproduce the original `exportVerilog` command and keep the raw log.
2. Run:

   ```bash
   python3 scripts/diagnose_pdd_routes.py <generated.pdd>
   ```

   Exit code `1` means a PDD consistency issue was found; keep the printed
   report as diagnostic evidence.

3. If `STALE_ROUTES` is non-empty, the PDD is internally inconsistent. Do not classify this as a license or FlexNoC environment failure.
4. If `UNUSED_ARCH_NODES` is non-empty, the auto-derived topology contains nodes not placed on any route. These nodes can trigger `A Node has not been placed on any route`.
5. Regenerate the PDD with route filtering and unused-node pruning, then rerun `exportVerilog`.

## Expected Fix Direction

The durable fix belongs in `flexnoc_dsl` generation:

- `Architecture.auto_derive()` should derive routes only for pairs whose `NocProject._connectivity[(init, target)]` is `True`.
- After route derivation, prune `dtpSwitch` and `dtpLink` nodes that are not referenced by any remaining request or response path.
- `PddWriter` must not emit structure shadows for pruned architecture nodes.

## Confirmed Example

A generated PDD had:

- `specification:soc_ext_i1/I/0 -> ddr_o0/T/0 = False`
- `specification:soc_ext_i1/I/0 -> cfg_o1/T/0 = False`
- architecture `datapathRoute` still included both routes.

Removing the two stale routes eliminated the `Incompatible settings` message. Pruning the unused `dtpSwitch005` then allowed FlexNoC 5.3.0 `exportVerilog` to pass and produce:

```text
r52_sys_flexnoc_struct.v
r52_sys_flexnoc_struct_commons.v
simulationFileNames.txt
synthesisFileNames.txt
```

## Classification

Use this classification in core IP try-run/check artifacts:

```yaml
failure_class: flexnoc_pdd_generation_bug
retry_action: filter_disconnected_routes_and_prune_unused_nodes
owner: flexnoc-gen
not_a_tool_environment_blocker: true
```
