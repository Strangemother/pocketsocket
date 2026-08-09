"""
Run:

python tool.py --test
python tool.py --test --compile
python tool.py --test --compile --benchmark --tag 2-0-4-2-cleanup --strip-prefix
python tool.py --test --compile --benchmark --tag 2-0-4-2-cleanup --strip-prefix --coverage-nim --coverage-c

1. Tests are all tests
    nimble test

2. compile is 'build' all the things
    python server/compile.py 

3. benchmark is run the full suite
    python benchmarks/run_all.py --tag 2-0-4-2-cleanup --strip-prefix

4. coverage is run the coverage suite
    server/scripts/coverage.sh #nim 
    server/scripts/c_coverage.sh #c 
"""