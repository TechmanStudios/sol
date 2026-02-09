# SOL UI-Neutral Scripting Standard

## Rule
Scripts must not move the graph/camera as a side effect of selecting or injecting nodes.

Do not call:
- recenter()
- zoomTo()
- focusOnNode()
- any camera/viewport manipulation functions

## Why
UI movement introduces hidden coupling:
- it changes user behavior,
- can trigger layout/physics recalculations,
- and contaminates repeatability.

## Required script behavior
- label every injection with a log entry
- output runTag + schemaName + invariants
- emit exports reliably and consistently
