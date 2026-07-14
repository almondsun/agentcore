Harden the sync-job path that consumes untrusted job specs:

- reject duplicate keys;
- reject absolute paths and `..` traversal segments;
- do not shell-interpolate parsed values;
- do not log the raw token; and
- report uncertainty around the real external `sync-tool` integration.
