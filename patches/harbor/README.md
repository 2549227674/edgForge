# Harbor local patch

The parent repository pins Harbor as a submodule. The M0 experiment used a small
local change to Harbor's `hello-world` example: the environment image includes
`tmux` and `asciinema`, and the verifier checks the produced file directly.

The submodule remains pinned to the unmodified upstream commit. Apply the saved
change only when reproducing that experiment:

```bash
git -C third_party/harbor apply ../../patches/harbor/hello-world-m0.patch
```

The current local Harbor checkout may already contain this patch. In that case,
do not apply it a second time.
