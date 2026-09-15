# Installing a11y-toolkit in your MCP client

The server speaks **standard MCP over stdio** (JSON-RPC, zero dependencies,
Python 3.9+), so it runs anywhere MCP runs. The only thing that changes per
client is where the config lives. Verified formats below — if your client
accepts a `command` + `args` stdio server, it works.

The universal block every client ultimately stores:

- **command**: `uvx`
- **args**: `--from a11y-toolkit a11y-toolkit-mcp`

(`pipx install a11y-toolkit` + command `a11y-toolkit-mcp` works too.)
Add `timeoutMs: 60000` where the client supports it — rendered audits,
snapshots and scroll walks start a browser.

## Claude Code

```bash
claude mcp add a11y-toolkit -- uvx --from a11y-toolkit a11y-toolkit-mcp
```

## Claude Desktop / Cursor / Windsurf / Cline / Continue / ZCode / any JSON-config client

```json
{
  "mcpServers": {
    "a11y-toolkit": {
      "command": "uvx",
      "args": ["--from", "a11y-toolkit", "a11y-toolkit-mcp"]
    }
  }
}
```

- Claude Desktop: `claude_desktop_config.json`
- Cursor: `~/.cursor/mcp.json` (or run `cursor mcp add a11y-toolkit -- uvx --from a11y-toolkit a11y-toolkit-mcp`)
- Windsurf: `~/.codeium/windsurf/mcp_config.json`
- ZCode: paste the block in your MCP settings

## VS Code (Copilot / Insiders)

`.vscode/mcp.json` in the workspace:

```json
{
  "servers": {
    "a11y-toolkit": {
      "command": "uvx",
      "args": ["--from", "a11y-toolkit", "a11y-toolkit-mcp"]
    }
  }
}
```

## Codex CLI (OpenAI)

`~/.codex/config.toml` ([configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)):

```toml
[mcp_servers.a11y-toolkit]
command = "uvx"
args = ["--from", "a11y-toolkit", "a11y-toolkit-mcp"]
```

## OpenCode

`opencode.json` ([config docs](https://opencode.ai/docs/config/)):

```json
{
  "mcp": {
    "a11y-toolkit": {
      "type": "local",
      "command": ["uvx", "--from", "a11y-toolkit", "a11y-toolkit-mcp"],
      "enabled": true
    }
  }
}
```

## Kimi Code CLI (Moonshot)

`~/.kimi-code/mcp.json` ([configuration files](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/config-files.html))
uses the standard `mcpServers` JSON shape:

```json
{
  "mcpServers": {
    "a11y-toolkit": {
      "command": "uvx",
      "args": ["--from", "a11y-toolkit", "a11y-toolkit-mcp"]
    }
  }
}
```

## Zed

`settings.json` → `context.servers`:

```json
{
  "context": {
    "servers": {
      "a11y-toolkit": {
        "command": "uvx",
        "args": ["--from", "a11y-toolkit", "a11y-toolkit-mcp"]
      }
    }
  }
}
```

## DeepSeek

DeepSeek does not ship its own MCP client. To use DeepSeek models with MCP,
run them through a client that does — OpenCode and Claude Code both accept
custom OpenAI-compatible endpoints — and add a11y-toolkit there with the
configs above.

## Verifying the install

Any client, one question to the agent:

> use a11y_toolkit: contrast of #999999 on white

You should get ratio 2.85:1 with a suggested fix. For the rendered tools
(`a11y_audit_dom`, `a11y_reflow`, `a11y_keyboard`, `a11y_scroll`,
`a11y_snapshot`), the machine running the client needs
`pip install playwright && playwright install chromium` — everything else
works with zero dependencies.
