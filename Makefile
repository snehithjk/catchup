.PHONY: test eval demo check

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

eval:
	PYTHONPATH=src python3 scripts/eval.py

demo:
	PYTHONPATH=src python3 scripts/demo.py

check:
	PYTHONPATH=src python3 -m compileall -q src tests scripts
	@lines=$$(find src/catchup -name '*.py' -print0 | xargs -0 cat | wc -l | tr -d ' '); \
	if [ "$$lines" -gt 1500 ]; then echo "core LOC $$lines exceeds 1500"; exit 1; fi; \
	echo "core LOC $$lines"
