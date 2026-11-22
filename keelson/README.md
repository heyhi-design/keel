<!-- origin: keel -->

# keelson -- the separability convention

A keel instance is a firm's own operating layer built on top of the keel base. Over time an
instance proves things: a check, a schema field, a small mechanism that turns out to be
generic rather than specific to that firm. Some of those are worth binding back down into the
keel base so every instance gets them. keelson is the convention that keeps that lift honest.

In shipbuilding the keelson is the timber fastened along the keel that binds the frames into
it. Here it names the same move: a proven structure from an instance is bound *into* the keel
base, cleanly, without dragging the instance's private content along with it.

This directory ships the generic half of that convention -- the part that travels to every
instance. It is two things: a tag you put on files, and a check that enforces what the tag
promises.

## The tag

A file that is part of the generic, shareable base declares `origin: keel`. A file that is
specific to your instance -- your filled-in profile, your client work, your calibrated values
-- declares `origin: instance`. A file with no tag makes no claim, and the check leaves it
alone.

Where the tag goes depends on the file type, because it has to sit somewhere the file's own
tooling already ignores:

- **Markdown**: an HTML comment on the first non-empty line, so it stays invisible when the
  document is rendered.

  ```
  <!-- origin: keel -->

  # My document
  ```

- **Python, YAML, and other text files**: a comment in the header, in the first lines of the
  file.

  ```
  # origin: keel
  ```

Tag the files you intend to keep liftable. You do not have to tag everything at once; tag a
file when you are about to lift it, or tag your base files as you touch them, and the check
grows teeth as you go.

## The check

`separability_check.py` reads the tree and, for every `origin: keel` file, verifies it carries
no reference to a path you have declared private to your instance.

```
python3 keelson/separability_check.py             # scan the current directory
python3 keelson/separability_check.py . --private clients/ --private financial/
```

The one path it treats as private by default is the `examples` directory, which is where keel
keeps its own worked instance. Add your own instance-private trees with `--private` (it
repeats). A firm running keel might add its client folder, its financial models, anything that
is yours and not the base's.

A *reference* is the path used as a path -- an import, a quoted string, or a Markdown link
that points into it. A file naming the path in prose or a backticked span is describing the
boundary, not crossing it, so it is left alone. This document mentions the examples directory
several times and passes its own check for exactly that reason.

Exit 0 means every tagged base file is clean. Exit 1 lists the references it found; each one is
either a sign the file is not actually liftable (retag it `origin: instance`) or a reference
that should not be there (fix it).

## What this does not do

It does not decide whether a file *should* be base or instance -- that is your call, and the
tag is where you record it. It does not judge whether a mechanism is worth lifting at all, or
whether it is genuinely generic once the private references are gone. It reads no code
semantically. It checks one narrow, mechanical thing: that a file claiming to be liftable base
does not quietly depend on content that cannot travel with it. The judgment stays yours; this
just makes the one part a machine can be trusted with automatic.
