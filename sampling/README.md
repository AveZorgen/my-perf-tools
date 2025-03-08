# Sampling profiler
Data collected every 1 ms
## Build
```bash
make
```
## Usage
### Run profiler
- Normal run
```bash
./build/sampling <exe>
```
- Callstack run
```bash
./build/sampling_g <exe>
```
### Generate report
```bash
python3 report.py
```
