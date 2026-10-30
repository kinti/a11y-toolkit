# Solidez con una orden. Los targets que usa el día a día.
.PHONY: test fast hooks visual release help

test:            ## todas las suites (dom/scroll se auto-omiten sin Playwright)
	python3 tests/test_contrast.py && python3 tests/test_audit.py && python3 tests/test_v32.py \
	  && python3 tests/test_dom.py && python3 tests/test_cli.py && python3 tests/test_journey.py \
	  && python3 tests/test_png.py && python3 tests/test_vpat.py && python3 tests/test_act.py \
	  && python3 tests/test_wcag3.py && python3 tests/test_route.py && python3 tests/test_mutants.py && python3 tests/test_verify_pack.py && python3 tests/test_npm_wrapper.py && python3 tests/test_wcagem.py && python3 tests/test_plan.py \
	  && python3 tests/test_solido.py && python3 tests/test_mcp.py && python3 tests/test_revision_externa.py \
  && python3 tests/test_naming.py && python3 tests/test_locales.py \
  && python3 scripts/gen_readme.py --check && python3 scripts/gen_llms.py --check

fast:            ## suites rápidas (lo que guarda el pre-push)
	python3 tests/test_contrast.py && python3 tests/test_audit.py && python3 tests/test_v32.py \
	  && python3 tests/test_wcag3.py && python3 tests/test_route.py && python3 tests/test_mutants.py && python3 tests/test_verify_pack.py && python3 tests/test_npm_wrapper.py && python3 tests/test_wcagem.py && python3 tests/test_plan.py \
	  && python3 tests/test_solido.py && python3 tests/test_mcp.py \
	  && python3 scripts/gen_readme.py --check && python3 scripts/gen_llms.py --check

hooks:           ## activa el guardián de push (una vez por clon)
	git config core.hooksPath .githooks

visual:          ## regenera GIF e imagen social (tras cambiar tools/contajes)
	python3 docs/gen-visuals.py

release:         ## VERSIONA = make release V=3.9.5 (bump atómico + suites + tag + push)
	@test -n "$(V)" || (echo 'uso: make release V=X.Y.Z'; exit 1)
	python3 scripts/versionar.py $(V) --tag

help:
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[1m%-12s\033[0m %s\n",$$1,$$2}'
