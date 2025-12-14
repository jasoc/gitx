.PHONY: build install

WHEEL := cli/dist/gitx_cli-0.1.0-py3-none-any.whl

build:
	COMPOSE_BAKE=true docker compose run --build --rm --remove-orphans --entrypoint ./build.sh --name gitx-build gitx-cli

$(WHEEL): build
	@echo "Wheel generated"

install: $(WHEEL)
	./setup/install.sh ensure-pipx
	pipx install $(WHEEL) --force