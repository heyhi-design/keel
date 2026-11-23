"""
Fence parity across the tools that read Markdown structure.

Four tools skip what sits inside a fenced code block: the start-load import parser, the
handoff entry splitter, the close check's slot reader, and the cold-start path finder. They
carry the same fence rule in four places (a fence closes only on a marker of the same character
at least as long as the opener), so this test feeds all four the same tricky document and
fails if any one of them drifts: a four-backtick fence holding a three-backtick line, then a
tilde fence holding a backtick line.
"""

from conftest import load_tool

slc = load_tool("os/start_load_check.py", "fence_slc")
hr = load_tool("os/handoff_rotate.py", "fence_hr")
cc = load_tool("keelson/close_check.py", "fence_cc")
csc = load_tool("os/cold_start_check.py", "fence_csc")

TRICKY = """\
## 2026-03-02 · real entry

````
```
## not an entry
### Fixes Applied
@hidden-import.md
`hidden/path.md`
```
still inside
````

~~~
```
## still not an entry
~~~

### Fixes Applied

- @real-import.md and `real/path.md`
"""


def test_every_parser_skips_the_same_fenced_lines():
    assert slc.imports_in(TRICKY) == ["real-import.md"]
    assert len(hr.split_entries(TRICKY)[1]) == 1
    names = [name for name, _ in cc.sections(TRICKY, 3)]
    assert names == ["Fixes Applied"]
    assert [t for _, _, t in csc.path_refs(TRICKY)] == ["real/path.md"]
