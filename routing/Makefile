# Routing (Saksham). Every target reads/writes only under $(JT_LOCAL_DATA) and needs no AWS credentials
# (SHARED §11.5), except `publish`.
ROOT          := $(abspath ..)
SCENARIO      ?= yamuna-2023-07
WINDOW        ?= all
STEP          ?= 1
SOLVER        ?= greedy
ENV           ?= demo
REPORTS       ?=
PYTHON        ?= python3
export JT_LOCAL_DATA ?= $(ROOT)/data
export PYTHONPATH := $(ROOT)/shared/py:$(ROOT)/routing:$(ROOT)/alerts$(if $(PYTHONPATH),:$(PYTHONPATH))

.PHONY: help install devworld precompute hero inspect fixtures test publish demo-local clean

help:
	@echo "make devworld                 # synthetic upstream artefacts into \$$JT_LOCAL_DATA (dev/CI only)"
	@echo "make precompute SCENARIO= WINDOW=all|demo|<from>/<to> STEP=1 SOLVER=greedy|ortools [REPORTS=file]"
	@echo "make hero [WRITE_MANIFEST=1]  # T_hero + backup hero (SHARED §11.8-1)"
	@echo "make inspect AT=<ts> | make inspect HERO=1"
	@echo "make fixtures                 # regenerate shared/fixtures from the real writers"
	@echo "make test | make publish ENV=demo | make demo-local"

install:
	$(PYTHON) -m pip install -r requirements-offline.txt

devworld:
	$(PYTHON) -m jt_routing.devworld --scenario $(SCENARIO)

precompute:
	$(PYTHON) -m jt_routing.precompute --scenario $(SCENARIO) --window "$(WINDOW)" --step $(STEP) \
		--solver $(SOLVER) $(if $(REPORTS),--reports $(REPORTS)) --quiet

hero:
	$(PYTHON) -m jt_routing.hero --scenario $(SCENARIO) $(if $(WRITE_MANIFEST),--write-manifest)

inspect:
	$(PYTHON) scripts/inspect_step.py --scenario $(SCENARIO) $(if $(HERO),--hero-candidates,--at "$(AT)")

fixtures:
	$(PYTHON) scripts/make_fixtures.py

test:
	$(PYTHON) -m pytest -q tests

# Upload my artefacts (separate from replay-local; needs AWS credentials).
publish:
	@test -n "$(BUCKET)" || (echo "set BUCKET=jt-$(ENV)-data-<acct>" && exit 1)
	aws s3 sync $(JT_LOCAL_DATA)/scenarios/$(SCENARIO)/roads s3://$(BUCKET)/scenarios/$(SCENARIO)/roads
	aws s3 sync $(JT_LOCAL_DATA)/scenarios/$(SCENARIO)/plans s3://$(BUCKET)/scenarios/$(SCENARIO)/plans
	aws s3 sync $(JT_LOCAL_DATA)/scenarios/$(SCENARIO)/routing s3://$(BUCKET)/scenarios/$(SCENARIO)/routing
	aws s3 cp $(JT_LOCAL_DATA)/static/osm/edge_cutoffs.json s3://$(BUCKET)/static/osm/edge_cutoffs.json

# Whole Saksham chain on the dev world, offline: devworld → precompute → hero → precompute(demo) → predraft.
demo-local: devworld precompute
	$(MAKE) hero WRITE_MANIFEST=1
	$(MAKE) -C ../alerts predraft WINDOW=demo

clean:
	rm -rf $(JT_LOCAL_DATA)/scenarios/$(SCENARIO)/roads $(JT_LOCAL_DATA)/scenarios/$(SCENARIO)/plans \
		$(JT_LOCAL_DATA)/scenarios/$(SCENARIO)/routing
