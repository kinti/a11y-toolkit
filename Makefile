# Solidez con una orden. Los targets que usa el día a día.
.PHONY: test fast hooks visual release help

test:            ## todas las suites (dom/scroll se auto-omiten sin Playwright)
	python3 test_contrast.py && python3 test_audit.py && python3 test_v32.py \
	  && python3 test_dom.py && python3 test_cli.py && python3 test_solido.py && python3 test_mcp.py

fast:            ## suites rápidas (lo que guarda el pre-push)
	python3 test_contrast.py && python3 test_audit.py && python3 test_v32.py \
	  && python3 test_solido.py && python3 test_mcp.py

hooks:           ## activa el guardián de push (una vez por clon)
	git config core.hooksPath .githooks

visual:          ## regenera GIF e imagen social (tras cambiar tools/contajes)
	python3 docs/gen-visuals.py

release:         ## VERSIONA = make release V=3.9.5 (bump atómico + suites + tag + push)
	@test -n "$(V)" || (echo 'uso: make release V=X.Y.Z'; exit 1)
	python3 scripts/versionar.py $(V) --tag

help:
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[1m%-12s\033[0m %s\n",$$1,$$2}'
