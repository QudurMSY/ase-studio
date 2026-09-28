<!-- SPDX-FileCopyrightText: 2026 Behnam Farnaghinejad <behnam.farnaghinejad@polito.it> -->
<!-- SPDX-License-Identifier: GPL-2.0-only -->

# Exam pipeline golden values

These fixtures are the accepted ASE Studio pipeline results for the exam
programs. They are an interface contract: ordinary parser, scheduler, and UI
changes must not alter their CSV output.

Each case contains:

- `config.json`: the effective ASE Studio CPU configuration;
- `source.s`: the assembly source used for source-line mapping;
- `program.dump`: the disassembly used for addresses and the visible code end;
- `trace.log`: the frozen raw gem5 MinorCPU trace;
- `pipeline.csv`: the complete expected table with repeated loop rows.

Run the regression suite from the `ase_studio` directory:

```bash
python3 -m unittest tests.test_pipeline_regressions
```

The test reconstructs every displayed pipeline from the frozen source,
configuration, disassembly, and trace, then compares it with `pipeline.csv`.
It does not require a gem5 installation or the parent repository's `programs`
directory.

Do not regenerate these files as part of a routine code change. A golden CSV
may be replaced only when an intentional architecture correction has been
