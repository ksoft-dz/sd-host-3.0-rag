# Implementation Guidelines

## G1 — One Output Port Update Per Function, at the End

An output port update (interrupt signal, data send, etc.) yields the current thread to other threads in the simulation framework. Firing mid-function exposes partially-updated internal state.

- Accumulate all internal state changes first (registers, flags, buffers).
- Fire the output port **once**, as the **last action** before returning.
- If multiple output-worthy events occur in the same function, combine them into a single update.

**Exception:** Loops that process items one-by-one (e.g., block transfers) may need to fire at natural pause points where the environment must observe intermediate state.

## G2 — Batch Work Between Observable Events

When processing a sequence of items (blocks, descriptors, etc.), only break and fire an output when an event **observable by the driver/user** is reached. If an event is not relevant to the driver (not enabled, not monitored), don't represent it at all — skip it and keep processing.

- If the next item produces no driver-observable event → accumulate it silently.
- If the next item produces an observable event → flush accumulated work, fire output, stop.
- After the loop completes with no pending events → flush everything, fire final output.

The key insight: an event that no one observes doesn't need to exist. This lets the model abstract away arbitrary amounts of internal work between the points the driver actually cares about.
