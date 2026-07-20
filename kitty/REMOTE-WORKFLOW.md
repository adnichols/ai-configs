# Kitty remote workflow

## Open a remote environment

- `Cmd+Shift+1`: open **mbp** Herdr in a new Kitty OS window
- `Cmd+Shift+2`: open **dever** Herdr in a new Kitty OS window
- `Cmd+Option+1`: open a plain `kitten ssh mbp` shell
- `Cmd+Option+2`: open a plain `kitten ssh dever` shell

Shell equivalents:

```sh
herdr-mbp
herdr-dever
kssh mbp
kssh dever
```

## Paste a screenshot into a remote agent

1. Copy a screenshot to the macOS clipboard with `Control+Cmd+Shift+4`.
2. Focus the remote Kitty pane.
3. Press `Cmd+Shift+V` (or `Control+Option+V`).

The helper detects `mbp` or `dever` from the active SSH process/title, runs
`clipssh`, uploads to `~/.cache/clipssh/` with mode `0600`, and inserts the
remote pathname directly into the prompt.

## Notifications

Herdr uses terminal notification delivery on both remote hosts, allowing Kitty
to surface completion and needs-input notifications on this Mac.
