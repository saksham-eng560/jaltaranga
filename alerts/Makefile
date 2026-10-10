# Alerts (Saksham). predraft/test/halluc-eval run offline under $(JT_LOCAL_DATA) (SHARED §11.5).
ROOT          := $(abspath ..)
SCENARIO      ?= yamuna-2023-07
WINDOW        ?= demo
N             ?= 20
PYTHON        ?= python3
export JT_LOCAL_DATA ?= $(ROOT)/data
export PYTHONPATH := $(ROOT)/shared/py:$(ROOT)/routing:$(ROOT)/alerts$(if $(PYTHONPATH),:$(PYTHONPATH))

.PHONY: predraft test halluc-eval halluc-live probe publish

predraft:
	$(PYTHON) -m jt_alerts.predraft --scenario $(SCENARIO) --window "$(WINDOW)" $(if $(AUDIO),--audio)

test:
	$(PYTHON) -m pytest -q tests

# Replays tests/recorded/*.json through the validator (CI). halluc-live records N real Nova drafts.
halluc-eval:
	$(PYTHON) scripts/halluc_eval.py --scenario $(SCENARIO) -n $(N)

halluc-live:
	$(PYTHON) scripts/halluc_eval.py --scenario $(SCENARIO) -n $(N) --live --report halluc_report.json

probe:
	$(PYTHON) scripts/probe_bedrock.py

publish:
	@test -n "$(BUCKET)" || (echo "set BUCKET=jt-<env>-data-<acct>" && exit 1)
	aws s3 sync $(JT_LOCAL_DATA)/scenarios/$(SCENARIO)/dispatch_cache s3://$(BUCKET)/scenarios/$(SCENARIO)/dispatch_cache
