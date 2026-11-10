# Security Policy

## Reporting a vulnerability

Use **GitHub's private vulnerability reporting** (Security tab → Report a
vulnerability): no public issue, no disclosure until we ship the fix.

You can also write to **hola@a11y.es** (subject: `[security]`) if you prefer
email. Either channel reaches the maintainer directly.

## What counts

Anything that makes the toolkit misreport, leak, or trust something it
should not: a finding the engine misses BY DESIGN is not a vulnerability
(the honesty note in every report covers what automation cannot see);
an injection via a scanned URL, a tampered evidence pack, or a way to
bypass the sha256 canonicalization IS.

## Supported versions

The latest tagged release (and the npm launcher of the same version). We
ship fixes fast: the engine is the product's core and every release goes
out the same day the fix does.

## Scope note

The toolkit is a zero-dependency CLI/library. There is no server, no
session, no secret handling in-repo: the SaaS layer (a11y.es) keeps its own
security process and is a separate codebase.
