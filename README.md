# DOTP

**Dank One Time Password** - A CLI and TUI application for secure TOTP/Authenticator storage.

[![Tests](https://github.com/rochacbruno/dotp/actions/workflows/test.yml/badge.svg)](https://github.com/rochacbruno/dotp/actions/workflows/test.yml)
[![Lint](https://github.com/rochacbruno/dotp/actions/workflows/lint.yml/badge.svg)](https://github.com/rochacbruno/dotp/actions/workflows/lint.yml)


![TUI](https://raw.githubusercontent.com/rochacbruno/dotp/main/assets/tui.png)


![Cli List](https://raw.githubusercontent.com/rochacbruno/dotp/main/assets/list.png)

## Features

- Encrypted vault storage with password protection
- CLI commands for managing TOTP entries
- Interactive TUI for quick access
- Import/Export support for Aegis and otpauth URI formats
- Real-time token generation with auto-refresh
- Search and filter capabilities with fuzzy matching
- Clipboard integration
- Clean, modern terminal UI with progress indicators

## Installation

### Using uvx (Recommended)

Run DOTP without installation:

```bash
uvx dotp --help
```

Global install

```bash
uv tool install dotp
```

Pip install

```
pip install dotp
```


### Using uv (for development)

```bash
git clone https://github.com/rochacbruno/dotp.git
cd dotp
uv sync
uv run dotp --help
```

## Quick Start

### Initialize a vault

```bash
uvx dotp init
```

This creates an encrypted vault at `~/.config/dotp/.vault.dotp` (or `$XDG_CONFIG_HOME/dotp/.vault.dotp`).

### Add an entry

```bash
uvx dotp add --label GitHub --secret YOURBASE32SECRET
```

Or interactively:

```bash
uvx dotp add --label GitHub
# You'll be prompted for the secret
```

### List all entries

```bash
uvx dotp list
```

### Get a specific token

```bash
uvx dotp get GitHub
```

For scripting (clean output):

```bash
DOTP_PASSWD=123456 uvx dotp get GitHub | wl-copy
```

#### Scripting tip

`~/.local/bin/o`
```bash

#!/usr/bin/bash
DOTP_PASSWD=1234 uvx dotp get $@ | wl-copy
```

Then you can simply run on terminal 

```bash
o Google
```

and get the code copied to clipboard.

If you are running on DMS, you can add the command runner plugin
and then open the launcher and do `>o dropbox` -> run in bg.

### Import from file

DOTP supports importing from various formats. See the sample files in the repository:
- [`otpauth_sample.txt`](./otpauth_sample.txt) - Example otpauth URI format
- [`aegis_sample.json`](./aegis_sample.json) - Example Aegis export format

```bash
# From otpauth URI format
uvx dotp import otpauth_sample.txt

# From Aegis JSON format
uvx dotp import aegis.json --aegis
```

### Export to file

```bash
# To otpauth URI format
uvx dotp export backup.txt

# To Aegis JSON format
uvx dotp export backup.json --aegis
```

![CLI](https://raw.githubusercontent.com/rochacbruno/dotp/main/assets/cli.png)


## TUI Mode

Launch the interactive TUI by running `dotp` without arguments:

```bash
uvx dotp
# or with password from environment
DOTP_PASSWD=123456 uvx dotp
# or with custom vault path
uvx dotp --path /tmp/my-vault.dotp
# or with environment variable
DOTP_VAULT=/tmp/my-vault.dotp uvx dotp
```

### TUI Features

- **Type to search**: Start typing to filter entries in real-time
- **Enter in search**: Focus results to navigate with arrow keys
- **Enter on item**: Copy selected token to clipboard
- **Ctrl+Enter**: Copy token and close application
- **Ctrl+A**: Add a new entry
- **Ctrl+Q**: Quit
- **Escape**: Clear search
- **Backspace**: Return to search when navigating results

## Configuration

Create a config file at `~/.config/dotp/config.toml`:

```toml
# Path to your vault file (optional)
vault_path = "/path/to/.vault.dotp"

# Close TUI immediately after copying (default: false)
close_on_copy = true

# Clipboard command to use (default: wl-copy)
clipboard_command = "wl-copy"
```

## Environment Variables

- `DOTP_PASSWD`: Set vault password (useful for scripting)
- `DOTP_VAULT`: Set vault file path (alternative to `--path` or config file)

## Vault Location Priority

DOTP looks for the vault in this order:

1. `--path` argument
2. `DOTP_VAULT` environment variable
3. `vault_path` in config file
4. `.vault.dotp` in current directory
5. `~/.config/dotp/.vault.dotp`

## Security

- Vault is encrypted using Fernet (symmetric encryption)
- Password is derived using PBKDF2HMAC with SHA256
- 480,000 iterations (OWASP recommended minimum)
- 16-byte random salt per vault

## Development

### Running tests

```bash
uv sync --extra dev
uv run pytest
```

### Running with coverage

```bash
uv run pytest --cov=src/dotp --cov-report=html
```

### Linting

```bash
uvx ruff check src/
uvx ruff format src/
```

## Stack

- [UV](https://github.com/astral-sh/uv) - Package management
- [pyotp](https://github.com/pyauth/pyotp) - TOTP generation
- [cyclopts](https://github.com/BrianPugh/cyclopts) - CLI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [Textual](https://github.com/Textualize/textual) - TUI framework
- [cryptography](https://github.com/pyca/cryptography) - Encryption
- [xdg-base-dirs](https://github.com/srstevenson/xdg-base-dirs) - XDG Base Directory support

## License

AGPL License - See LICENSE file for details
