# Contributing

Add a small, tested capability and explain its scope. The project welcomes
new target profiles, adapter improvements, independent measurements and
clearer instructions.

For a new target include its exact model/package, pinout source, electrical
limits, memory/word/address sizes, transaction ordering, preservation rules,
and what was physically verified. Follow [the method](docs/method.md).
Mark a target supported only after validation on the exact device.

Submit original code and factual MCU parameter definitions. Manufacturer
software and manuals require separate, verified redistribution permission.
Link to official resources instead. Preserve third-party notices where code
is accepted under a compatible license.

Device backups, credentials and serial logs containing private data must
stay local. Public validation should use sanitized summaries and hashes of
the project's own examples. `tools/check_release.py` is a useful release
guard, not a substitute for provenance review.

Before a pull request:

```sh
python -m unittest discover -s tests -v
python tools/check_release.py
```

Describe source-code checks separately from hardware tests. Contributions
of original code/documentation are submitted under the project's MIT license;
do not claim rights you cannot grant. Manufacturer marks remain with their
respective rights holders.
