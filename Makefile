.PHONY: build install

WHEEL := cli/dist/gitx-0.1.0-py3-none-any.whl

build:
	docker compose run --build --rm --remove-orphans --entrypoint ./build.sh --name gitx-build gitx-cli

$(WHEEL): build
	@echo "Wheel generated"

install: $(WHEEL)
	pip install $(WHEEL) --force-reinstall