# wakepy Docker Sandbox kit

Install [Docker Sandboxes](https://docs.docker.com/ai/sandboxes/). From the repository root, create a sandbox with one of these workloads and the wakepy kit.

## Shell (No AI)

```bash
sbx create docker.io/docker/sbx-kit-shell:1.0.0 . --name wakepy --kit ./.sbx-kit
```

## Claude

```bash
sbx create docker.io/docker/sbx-kit-claude:2.1.267 . --name wakepy --kit ./.sbx-kit
```

## Codex

```bash
sbx create docker.io/docker/sbx-kit-codex:0.155.1 . --name wakepy --kit ./.sbx-kit
```

## Antigravity

```bash
sbx create docker.io/sbx/antigravity:latest . --name wakepy --kit ./.sbx-kit
```

## OpenCode

```bash
sbx create docker.io/docker/sbx-kit-opencode:1.18.31 . --name wakepy --kit ./.sbx-kit
```

## Copilot

```bash
sbx create docker.io/sbx/copilot:latest . --name wakepy --kit ./.sbx-kit
```

## Kiro

```bash
sbx create docker.io/sbx/kiro:latest . --name wakepy --kit ./.sbx-kit
```

## Cursor

```bash
sbx create docker.io/docker/sbx-kit-cursor:2026.09.18-9a7762b . --name wakepy --kit ./.sbx-kit
```

## Start a shell

```bash
sbx exec -it wakepy bash
```

These references resolved in Docker Hub when checked. Docker's short names (`shell`, `claude`, `codex`) currently select v2 kits and cannot use this v3 kit. See [Docker's published v3 workloads](https://docs.docker.com/ai/sandboxes/customize/use-kits/#published-v3-workloads) for more options, though some references in that listing no longer resolve.

To test your sandbox configuration, run

```bash
just test-cli
```

inside a sandbox.

## Network access

The kit declares no network rules. Docker's selected [local network policy](https://docs.docker.com/ai/sandboxes/security/policy/) applies. Check it with `sbx policy ls`; if dependency installation is blocked, allow the needed package host using `sbx policy allow network HOST`. See [network access policies](https://docs.docker.com/ai/sandboxes/governance/access-controls/network/) for details.

For more examples, see [Docker Sandboxes](https://docs.docker.com/ai/sandboxes/) and [Use kits](https://docs.docker.com/ai/sandboxes/customize/use-kits/).
