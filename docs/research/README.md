# Research Directory

This directory contains experimental and proof-of-concept work for pocketsocket.

---

## Active Research

### Multi-Process IPC Architecture

**Location:** `multiprocess-ipc/`  
**Status:** ✅ Proof of Concept Complete  
**Date:** November 9, 2025

A working implementation of a multi-process architecture where:
- Nim WebSocket server runs in separate process
- Python hooks called via IPC (Unix domain sockets)
- Solves all threading/GIL issues
- **Proven working** - hooks successfully receive events!

**Key Files:**
- `ARCHIVE_SUMMARY.md` - Quick reference
- `README.md` - Complete analysis
- `IMPLEMENTATION_GUIDE.md` - Step-by-step reimplementation
- Working code files included

**When to use:** If threading issues block development and 1ms IPC latency is acceptable.

---

## How to Use This Research

1. **Read first:** Start with `ARCHIVE_SUMMARY.md` in each project
2. **Understand why:** Read related investigation docs (PYTHON_CALLBACK_INVESTIGATION.md, etc.)
3. **Implement if needed:** Follow IMPLEMENTATION_GUIDE.md
4. **Test thoroughly:** Use included test files

---

## Research Process

Each research project should include:
- README.md - Overview and analysis
- IMPLEMENTATION_GUIDE.md - How to reimplement
- ARCHIVE_SUMMARY.md - Quick reference
- Working code examples
- Test files

---

## Integration Guidelines

Before integrating research into main codebase:

1. **Validate approach** - Ensure it solves the problem
2. **Consider tradeoffs** - Performance, complexity, maintainability
3. **Test thoroughly** - Don't rely on proof-of-concept testing
4. **Document decisions** - Why this approach vs alternatives
5. **Plan migration** - How to transition existing users

---

## Related Documentation

In main directory:
- `PYTHON_CALLBACK_INVESTIGATION.md` - Threading issues analysis
- `POLLING_INVESTIGATION.md` - Event queue approach
- `THREADING_ISSUE.md` - Original problem description

These explain the "why" behind the research.

---

**Remember:** Research is about exploration. Not all research should be integrated. The goal is to understand possibilities and make informed decisions.
