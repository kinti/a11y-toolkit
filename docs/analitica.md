# Usage analytics — without any telemetry

a11y-toolkit contains **zero telemetry**. It never phones home: the URLs you
audit and the files you touch are nobody's business, and the project's entire
brand is honesty. Everything worth knowing is available from public/owner-only
sources:

## PyPI downloads (public, updated daily, ~1 day lag)

```bash
curl -s https://pypistats.org/api/packages/a11y-toolkit/recent | python3 -m json.tool
# last day / week / month; also .../overall for per-version history
```

Live badge in README (shields.io/pypi/dm). Honest caveat: counts downloads, not
people — CI, bots and uvx's fresh-environment installs all count. The *trend*
is the signal, not the absolute number.

## GitHub traffic (owner-only, 14-day rolling window)

```bash
gh api repos/kinti/a11y-toolkit/traffic/views   # {count, uniques} page views
gh api repos/kinti/a11y-toolkit/traffic/clones  # {count, uniques} repo clones
gh api repos/kinti/a11y-toolkit/traffic/popular/referrers  # where visitors came from
```

Check it every week or two: the window slides. Registry crawlers (Glama,
PulseMCP, mcp.so…) inflate clones — watch the *uniques* trend instead.

## What we deliberately do NOT have

No telemetry, no analytics, no crash reporting, no update pings in the MCP
server. A local accessibility tool that phones home with the URLs its users
audit would leak exactly the data its users trust it with — and the first
person to read the source would end the project's credibility. Trust is the
product; the public numbers above are enough to steer by.
