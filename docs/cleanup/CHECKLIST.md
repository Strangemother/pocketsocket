# Cleanup Checklist

Use this checklist with [INVENTORY.md](INVENTORY.md). Each verification clause
should be satisfied before checking an item off. Run the relevant checks from
the repository root unless a command says otherwise.

## Actively Harmful

- [x] **A1. Delete `service_orig.nim`.** Remove the orphaned segfaulting copy
  from `server/src/pocketsocketpkg/`.
  **Verify:** `test ! -e server/src/pocketsocketpkg/service_orig.nim` and
  `! rg -n "service_orig" server/src server/tests` both succeed.

- [x] **A2. Remove duplicate hook invocation on socket drop.** Keep the close
  and registry-removal path, but do not call the Python hook again after a hook
  returns `1`.
  **Verify:** inspect the drop branch in
  `server/src/pocketsocketpkg/broadcast.nim` and confirm it contains no second
  `hook.call_py_hook` call; run the regression test proving a drop event invokes
  the hook exactly once.

- [x] **A3. Fix the benchmark package path and make local imports explicit.**
  Point the harness at `package/` and fail if benchmarks import another
  `pocketsocket` installation.
  **Verify:** `rg -n 'PYTHON_PKG|assert_local_module' benchmarks/lib/harness.py`
  shows `package` and the guard, then run the guard and
  `python3 benchmarks/run_all.py --quick --only startup --dir "$(mktemp -d)"`.

- [ ] **A4. Resolve the template independently of the caller's working
  directory.** Support the documented override/executable-relative lookup and
  keep a loud built-in fallback when no template exists.
  **Verify:** start the server from `/tmp` and confirm it serves the repository
  template, or explicitly logs the missing-template fallback; also verify the
  CLI `--template` path if implemented.

## Dead Weight

- [x] **B1. Delete or relocate `chat.nim`.** It must not remain in the shipped
  package source directory as an orphaned example.
  **Verify:** `test ! -e server/src/pocketsocketpkg/chat.nim` or confirm it is
  under a documented examples directory and `rg -n 'chat' server/src server/tests`
  has no production import.

- [x] **B2. Delete `imp.nim`.** Remove the empty orphaned stub.
  **Verify:** `test ! -e server/src/pocketsocketpkg/imp.nim` and
  `! rg -n '(^|[[:space:]])import.*imp|imp\.nim' server/src server/tests` both
  succeed.

- [x] **B3. Remove the unused `clients` HashSet.** Delete the declaration and
  the now-unneeded `std/sets` import from `broadcast.nim`.
  **Verify:** `! rg -n '\bclients\b|std/sets' server/src/pocketsocketpkg/broadcast.nim`
  succeeds, and `cd server && nimble test` passes.

- [x] **B4. Remove the unused lock from `service.nim`.** Delete its
  initialization and import only if no other lock usage remains.
  **Verify:** `! rg -n '\b(lock|initLock|withLock)\b' server/src/pocketsocketpkg/service.nim`
  succeeds, and `cd server && nimble test` passes.

- [x] **B5. Replace the commented-out declaration graveyard.** Remove stale
  Nim template boilerplate, commented imports, and abandoned declarations from
  the service header.
  **Verify:** inspect the first 26 lines of
  `server/src/pocketsocketpkg/service.nim` and confirm they contain only the
  live module header/imports and no commented-out abandoned declarations.

## Working but Fragile

- [x] **C1. Make the greeting frame opt-in or remove it.** The normal protocol
  must not send request headers as an unsolicited first frame; update clients
  and documentation for the chosen behavior.
  **Verify:** connect with the raw benchmark client and confirm no unsolicited
  frame arrives before an application send; run the no-greeting regression test
  and the demo/client smoke test.

- [ ] **C2. Replace hashed WebSocket IDs with monotonic IDs.** Allocate an ID at
  open time and maintain both ID-to-socket and socket-to-ID mappings without
  casting `hash(websocket)`.
  **Verify:** `! rg -n 'hash\(websocket\)|cast\[uint64\]\(hash' server/src`
  succeeds; connect, close, and reconnect clients and confirm IDs are unique
  and old IDs cannot address the new connection.

- [x] **C3. Snapshot broadcast targets before sending.** Hold the registry lock
  only while copying target sockets, then release it before calling `send`.
  **Verify:** inspect `send_all` and confirm every `websocket.send` occurs after
  the `withLock` block; run the fan-out benchmark and confirm it completes with
  multiple receivers.

- [x] **C4. Remove stale header-marshalling comments from `hook.nim`.** Keep
  header access in the connection context rather than rebuilding headers per
  message.
  **Verify:** `! rg -n 'Extract headers|headersDict|messageDict\["headers"\]' server/src/pocketsocketpkg/hook.nim`
  succeeds, and `cd server && nimble test` passes.

- [x] **C5. Move the `quick_demo.nim` test out of `src/`.** Fold its coverage
  into the appropriate test file and delete the source entry point.
  **Verify:** `test ! -e server/src/quick_demo.nim`, the equivalent assertion or
  test exists in `server/tests/test_socket_tools.nim`, and `cd server && nimble test`
  passes.

## Final Validation

- [ ] Run the full server validation after the selected cleanup items:
  `cd server && nimble test && nimble buildPyd && nimble build`.
- [ ] Run a quick benchmark from the repository root:
  `python3 benchmarks/run_all.py --quick --tag cleanup-check`.
- [ ] Review the diff and confirm no generated benchmark results or unrelated
  changes were accidentally included.
  **Verify:** `git status --short` and `git diff --check` show only intended
  cleanup changes.
