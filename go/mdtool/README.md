# mdtool

mdtool is a tool for rendering markdown files as HTML.

## Usage

There are two modes: conversion mode and server mode. Conversion mode is a batch
process, server mode does realtime conversions.

### Conversion Mode

In conversion mode, it takes either a single file or a directory of files to
convert.

```
mdtool [flags] <inpath> [outpath]
```

If `outpath` is omitted:

- When `inpath` is a file, the `outpath` becomes the `inpath` with `.md`
  replaced by `.html`.
- When `inpath` is a directory, each `.md` file is treated as above within the
  `inpath` directory.

If `outpath` is specified:

- When `inpath` is a file, if `outpath` specifies a non-existent path or a path
  to a file, it is written to that path. Directories are not created. If
  `outpath` specifies a directory, then the base name of `inpath` is used with
  `.html` replacing `.md`. If `.md` is missing, then `.html` is just appended.
- When `inpath` is a directory, `outpath` must be a directory. Markdown files
  will be created with the same directory structure, creating subdirectories as
  necessary.

### Server Mode

In server mode, we run a local webserver to serve a directory structure of
markdown files.

```
mdtool [flags] -serve [directory]
```

By default, we bind to `127.0.0.1:7768`. If no directory is specified, we use
the current working directory. Files ending in `.md` are rendered as HTML when
requested. Any other files in the directory are served directly, unless the
`-only-md` flag is passed, in which case only `.md` files will be served.

You can use the `-listen host:port` flag to change the bind address.

## Supported Markdown Features

- code blocks (inline and fenced) with syntax highlighting
- mermaid.js diagrams
- Github-Flavored Markdown Features
  - Checklists
  - Tables
- Dark Mode (automatically enabled via system media query)
