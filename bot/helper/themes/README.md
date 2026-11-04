## Custom Themes

Copy [cloudbot_minimal.py](cloudbot_minimal.py) to a new file in this folder, such as `cloudbot_custom.py` or `cloudbot_futuristic.py`, and edit its values.

- Keep the class name `CloudBotStyle` and the existing variable names, such as `ST_BN1_NAME`.
- Preserve the names inside formatting braces, such as `{sb1n}`. Do not use f-strings for theme values.
- `REPO_STATS` accepts only `{last_commit}`, `{version}` and `{changelog}`.

```python
class CloudBotStyle:
    ST_BN1_NAME = "It's {sb1n}"
```

Themes are discovered automatically from filenames beginning with `cloudbot_`; no manual registration in `AVL_THEMES` is needed. Set `BOT_THEME` to the filename suffix, such as `custom` for `cloudbot_custom.py`.
