# Devcontainer Customizations

Wakepy devcontainer comes only with the required tooling. This guide explains how to customize your devcontainer with additional tools like AI agents, extensions, and other development utilities.

## Customization Options

You have four ways to customize your devcontainer environment:

| Method | Extensions | Software | Mounts | Extends Repo Config |
|--------|------------|----------|--------|---------------------|
| 1. Features | ✅ | ✅ | ✅ | ✅ |
| 2. defaultExtensions | ✅ | ❌ | ❌ | ✅ |
| 3. Dotfiles | ❌ | ✅ | ❌ | ✅ |
| 4. repositoryConfigurationPaths | ✅ | ✅ | ✅ | ❌ (replaces) |

**Recommendation:** Use Features (option 1) for most customizations. It's the most flexible and extends the repository configuration.

### 1. Features: `dev.containers.defaultFeatures` (Recommended)

**Use for:** Installing software, adding editor extensions, AND using Docker mounts.

This is the most flexible option. Features can modify the container in any way needed.

**Example:** To add firewall configuration, codex, and claude-code, add to your [settings.json](https://code.visualstudio.com/docs/getstarted/settings#_settingsjson):

```json
{
  "dev.containers.defaultFeatures": {
    "ghcr.io/w3cj/devcontainer-features/firewall@sha256:f8ae63faf64094305ef247befc0a9c66eecd7a01768df0cc826c7d4a81a92bfc": {
      "verbose": true,
      "pypi": true,
      "anthropicApi": true,
      "openaiApi": true,
      "googleAiApi": true,
      "vscodeMarketplace": true
    },
    "ghcr.io/fohrloop/devcontainer-features/codex@sha256:7d78dad69447100e6694d4eb73b4307566c07e678f3f346d06e0c6fe37ef959c": {},
    "ghcr.io/fohrloop/anthropics-devcontainer-features-fork/claude-code@sha256:f76bc7179de085269881172935f6c5541321478f607c129872b0881d7109d5bf": {}
  }
}
```

See also: [Firewall feature documentation](https://github.com/w3cj/devcontainer-features/blob/main/src/firewall/README.md). The codex and claude-code features above are forks of [codex](https://github.com/jsburckhardt/devcontainer-features/tree/main/src/codex) and [claude-code](https://github.com/anthropics/devcontainer-features/tree/main/src/claude-code), respectively with additions like persisting mounts. Using the SHA256 digest instead of a version number is safer, as the contents of installed features is fixed, and you may verify the contents.

### 2. Extensions: (e.g. `dev.containers.defaultExtensions`)

**Use for:** Adding editor-specific extensions only.
**VS Code Example**: Add to your [settings.json](https://code.visualstudio.com/docs/getstarted/settings#_settingsjson):

```json
{
  "dev.containers.defaultExtensions": [
    "ms-python.python",
    "charliermarsh.ruff"
  ]
}
```

### 3. Dotfiles: `dotfiles.repository`

**Use for:** Environment variables, shell settings, dotfiles. Can also install software, but cannot install extensions or add mounts.

**About:** Installation is automatic and runs during the `postStartCommand` [lifecycle script](https://containers.dev/implementors/json_reference/#lifecycle-scripts). With the default [waitFor](https://containers.dev/implementors/json_reference/) value, `install.sh` runs after you have terminal access. Programs installed via dotfiles won't be available until `postStartCommand` completes and you start a new terminal. This is not part of the devcontainers spec, but addition by VS Code. Other editors might have similar functionality.

This option:
- Clones your dotfiles repository into the container
- Runs any `install.sh` script found in the repository
- Is perfect for personal shell configuration and env setup

Add to your [settings.json](https://code.visualstudio.com/docs/getstarted/settings#_settingsjson):

```json
{
  "dotfiles.repository": "your-github-id/your-dotfiles-repo",
  "dotfiles.targetPath": "~/dotfiles",
  "dotfiles.installCommand": "install.sh"
}
```

**Docs**: [code.visualstudio.com/docs/devcontainers/containers](https://code.visualstudio.com/docs/devcontainers/containers#_personalizing-with-dotfile-repositories)

### 4. Repository Configuration Paths: `dev.containers.repositoryConfigurationPaths`

**Use for:** Replacing the entire devcontainer configuration with your own custom configuration.

**⚠️ Important limitation:** This **replaces** (not extends) the repository-specific devcontainer configuration.

**When to use:** Only if you need complete control over the container setup and are willing to maintain the full configuration yourself. For most cases, use Features (option 1) instead.

**Example**: Add to your [settings.json](https://code.visualstudio.com/docs/getstarted/settings#_settingsjson):

```json
{
  "dev.containers.repositoryConfigurationPaths": [
    "/home/user/Dropbox/devcontainers"
  ]
}
```

In this case, the devcontainer folder structure for wakepy should be:

```text
📁 devcontainers/
└─📁 github.com/
  └─📁 wakepy/
    └─📁 wakepy/
      └─📁 .devcontainer/
        ├─📄 Dockerfile
        └─📄 devcontainer.json
```

See also: [Alternative repository configuration folders documentation](https://code.visualstudio.com/docs/devcontainers/create-dev-container#_alternative-repository-configuration-folders)

## Future Customization Options

**Overlaying .devcontainers** - A potential future feature that would allow extending a devcontainer more easily. Track the discussion: [microsoft/vscode-remote-release#3279](https://github.com/microsoft/vscode-remote-release/issues/3279)

## Additional Resources

- [VS Code Devcontainer Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Devcontainer Features](https://containers.dev/features)
