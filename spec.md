# DOTP

Dank One Time Password

Is a CLI and TUI application to serve as a TOTP/Authenticator storage.

## Usage

### CLI

Create a vault on local directory or passing `--path` to specify location 

```
$ dotp init 
starting new vault on .vault.dotp
Type a 6 digit password to encrypt your vault:
Repeat:
Vault started and encrypted
```

Add a new secret

```
$ dotp add --label AppName --digits 6 --algo sha1 --period 30 --secret 0985734583425
# or passing subset of parameter and being interactively asked
$ dotp add --label AppName
Type the Secret:
# digits, algo, period assumes default.
```

Import secret

```
dotp import full_vault.txt  # default format, see @full_vault.txt
dotp import aegis.json --aegis  # see @aegis_sample.json
```

(same with export path.txt or path.json)


List all secrets and its 30 second valid token

```
$ DOTP_PASSWD=123456 dotp list
Valid until: 15:34:12
Dropbox  123456
Google   345678
...

$ dotp list
Type your pass word to decrypt:
```

Get a single entry

```
$ dotp get Dropbox
Type your password to decrypt: *****
123456



# clean stdout, can use envvar

$DOTP_PASSWD=123456 dotp get DropBox
123456

$DOTP_PASSWD=123456 dotp get DropBox | wl-copy
```

### TUI


TUI is opened using simply `dotp` or `dotp --path vaultpath.dotp`
The file `~/.config/dotp/config.toml` has a `vault_path:` that allows overriding default vault path
By default the `dotp` will look for a `.vault.dotp` on localdir or `~/.config/dotp/`
 
TUI is simple, it has only a datagrid showing each entry, [label, code] fields
user can use arrow keys to move to selected entry and when hitting enter it copies to clipboard
it must support using configured clipboard engine from the config.toml
by default it uses `wl-copy`

on TUI user can press `Ctrl+a` to add a new entry, then a modal opens asking for
label, secret and other default fields.

If user starts typing anything other than mod keys (ctrl, shift, alt, mod) or arrow keys
then it is considered search. so user can simply start typing `Drop` and it real time filters 
datagrid items to show only the labels containing Drop and the first is selected.

If user then press enter, it is copied to clipboard.

On the config file the user can specify `close_on_copy = true` and then the program imediatelly
closes after copying to clipboard.

The TUI must also respect the DOTP_PASSWD if existing to decrypt the vault.



## Implementation details

### Stack

- UV
- Python
- https://github.com/pyauth/pyotp 
- cyclopts for CLI
- Rich for columns, tables, printing
- Textual for TUI

### Encryption

Derive a secret key from the given password and salt.

- cryptography lib
- Fernet
- PBKDF2HMAC
