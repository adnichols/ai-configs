---
name: benchmark-checklist
description: "Vet a perf measurement (limiter, tuning, limits, errors, repeatability, relevance, and whether the work happened) before you report or act on it. Use when you run a benchmark or report a speedup or regression you measured."
---

ADN_RUNTIME_MARKER:benchmark-checklist:e43c7ee26e0038c6c1fa8380dd34ce86ff94cb2a

# Benchmark checklist

Use this when you produce a performance number: a PR's before and after, a regression claim, a hillclimb harness, or a library or config choice. The **principle-explain-the-number** skill says why. Answer each question below with evidence from a run, not from a guess about the code.

For a quick ballpark the user asked for, one run is enough. Still check questions 4 and 7, and say that it is one run. Skip the rest unless that run looks wrong. A choice between options is never a ballpark.

## Before you run anything

- Write down the claim you expect to make, in the words you would ship ("export is 30% faster at p50 on the 60k-row dataset"). The questions test that sentence.
- Read the measurement script. Note what it times, what it counts, and what it ignores.
- Run `uname -s` on the machine that runs the benchmark, and take every tool below from that OS's column. Do this per host: a remote runner or container can differ from your shell.
- Check the load average with `uptime` and the core count from the table. If the machine is busy, find out what is running. If you cannot stop it, interleave the sides so both see the same noise, and say so in the report.

## Tools by OS

| Need | Linux | macOS (`Darwin`) |
|---|---|---|
| Cores | `nproc`. In a container, also read the CPU quota in `/sys/fs/cgroup/cpu.max`. | `sysctl -n hw.ncpu`. On Apple silicon, `sysctl hw.perflevel0.logicalcpu hw.perflevel1.logicalcpu` gives performance and efficiency cores; a run scheduled onto efficiency cores is slower. |
| Power and thermal state | `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` where present | `pmset -g` (Low Power Mode, battery) and `pmset -g therm` (throttling). Run on AC power. |
| CPU per process | `top`, `pidstat -u 1` | `top -o cpu`, `ps -o pid,%cpu,rss -p <pid>` |
| Native profiler | `perf record -g`, `perf top` | `sample <pid> 10`, `xctrace record --template 'Time Profiler'` |
| I/O wait and disk | `iostat -x 1`, `vmstat 1`, `pidstat -d 1` | `iostat -w 1`, `vm_stat 1`, `sudo fs_usage -f filesys <pid>` |
| Syscall counts | `strace -c -f -p <pid>` | `sudo dtruss -c -p <pid>` needs SIP relaxed for most binaries. Otherwise use `sudo fs_usage <pid>` or the Instruments System Call Trace template. |
| Network | `ss -s`, `sar -n DEV 1` | `nettop -P`, `netstat -ib` |

Runtime profilers work on both: `node --cpu-prof`, `py-spy record` (needs `sudo` on macOS), `go tool pprof`. On Linux, `pidstat`, `iostat`, and `sar` come from the `sysstat` package and `perf` from the kernel tools package. If a tool is missing or blocked, use the next one in its cell and name the substitution in the report.

## The questions

1. **Why not double?** Name the limiter. Profile in a run you do not report, because profilers and tracers slow the work down. Use CPU per process, a profiler for the runtime or the native profiler, I/O wait, and syscall counts from the table. Then map the hot spot to source. Watch the load generator too. If it saturates first, you measured the load generator. If a change did not move the number, the limiter explains why, so find it before you call the change useless.
2. **Was it tuned?** Run every side the way production runs it: release builds, production flags and env, batching and transaction settings, connection pools, caches as warm or cold as production sees them, and the same versions and data. If one side runs on defaults, you compared configurations, not implementations. A limiter that is a setting, such as a commit per row, a debug build, or a missing index, means that side is untuned. Tune it and measure again before you pick a winner. If you cannot tune it, do not pick a winner from that run. Narrowing the claim to the code as it ships today does not fix this when the user is choosing what to adopt, because they adopt the option, not today's settings. A macOS laptop is not production for a Linux service: say so when the claim is about production.
3. **Did it break limits?** Do the arithmetic. Compare bytes per second with disk and network bandwidth, and operations per second times the cost per operation with the cores you have. Compare the time saved with the time the changed piece took. Removing a piece that takes 10% of the run can make the run at most about 11% faster. A result past a limit means the run measured something other than the work, such as a cache, a no-op, or a bug.
4. **Did it error?** Count failures and non-success responses, and check that the outputs are correct, not just present. Errors behave differently from successes. Rejections are often fast, and timeouts and retries are slow. If the script does not count errors, add the count.
5. **Does it reproduce?** Run each side at least 5 times, and alternate the sides (A, B, A, B, and so on) so that warmup, lazy initialization, caches, and drift do not favor one side. Report the median and the range. Treat a gap smaller than the run-to-run variation as no measurable difference. When the call is close, use a rank-sum test or the harness's own statistics.
6. **Does it matter?** Next to any micro result, measure the end-to-end path a user waits on, with realistic data sizes and concurrency. Report the micro result as a share of the whole. A helper that takes 1% of a request can make the request at most 1% faster, however fast the helper gets.
7. **Did it even happen?** Confirm the work ran inside the timed region. The request reached the server, the rows were written, the bytes were read, and the code used the result. Lazy code (generators nobody iterates, promises nobody awaits, results the JIT can discard) and timeouts all produce numbers for work that never happened.

## Report

- Lead with the verdict: faster, slower, no measurable difference, or inconclusive.
- Give the number with its unit, the run count, the range, the limiter, and the OS and hardware it ran on. For example, "p50 41 ms → 33 ms, median of 7 runs per side, range 32 to 35 ms after, bound by JSON parsing on one core, Linux 8-core VM."
- Call the verdict inconclusive when you claim a difference but cannot name the limiter, when a side ran untuned, or when you could not check questions 4 and 7. Name the gap.
- Keep a PR body to one primary number, per the **Opening a PR** playbook. Put the runs, the range, and the limiter evidence in a linked artifact or a notes file.

## How this fits the other perf material

- The **Perf issue** playbook (`adn-mode/playbooks/perf-issue.md`) finds and fixes slowness, and the performance mantras in its step 2 generate the fixes. This skill vets its baseline before the playbook plans from it, and every number after that.
- The **Hillclimb** playbook (`adn-mode/playbooks/hillclimb.md`) loops on one metric. This skill vets its harness before the harness is frozen. The frozen harness then prints error and work counts, so each keep-or-revert checks questions 4 and 7 for free.
