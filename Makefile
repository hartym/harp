NAME ?= harp-proxy
VERSION ?= $(shell git describe 2>/dev/null || git rev-parse --short HEAD)
HONCHO ?= $(shell which honcho || echo "honcho")
PRE_COMMIT ?= $(shell which pre-commit || echo "pre-commit")
PYTEST ?= $(shell which pytest || echo "pytest")

DOCKER ?= $(shell which docker || echo "docker")
DOCKER_IMAGE ?= $(NAME)
DOCKER_IMAGE_DEV ?= $(NAME)-dev
DOCKER_TAGS ?=
DOCKER_TAGS_SUFFIX ?=
DOCKER_BUILD_OPTIONS ?=
DOCKER_BUILD_TARGET ?= runtime

SED ?= $(shell which gsed || which sed || echo "sed")


########################################################################################################################
# Local development
########################################################################################################################
.PHONY: start install install-frontend install-backend install-ui reference

start: install-frontend install-backend
	$(HONCHO) start

install: install-frontend install-backend

install-frontend: install-ui
	cd frontend; pnpm install

install-backend:
	poetry install

install-ui:
	cd vendors/mkui; pnpm install

reference: harp
	rm -rf docs/reference/python
	mkdir -p docs/reference/python
	sphinx-apidoc --tocfile index --separate -f -o docs/reference/python -t docs/_api_templates harp
	$(SED) -i "1s/.*/Python Package/" docs/reference/python/index.rst


########################################################################################################################
# QA, tests and other CI/CD related stuff
########################################################################################################################

.PHONY: qa types format test test-ui test-ui-update test-back lint-frontend test-frontend test-full

qa: types format reference test-full

types:
	bin/generate_types

format: install-frontend
	cd frontend; pnpm prettier -w src
	$(PRE_COMMIT)

test: test-back test-frontend

test-full: test test-ui

test-ui: install-ui
	cd vendors/mkui; pnpm test:prod

test-ui-update: install-ui
	cd vendors/mkui; pnpm test:update

test-back:
	$(PYTEST) harp tests

lint-frontend: install-frontend
	cd frontend; pnpm build

test-frontend: install-frontend lint-frontend
	cd frontend; pnpm test

########################################################################################################################
# Docker builds
########################################################################################################################

.PHONY: build build-dev push release run

build:
	poetry export -f requirements.txt --output requirements.$@.txt
	$(DOCKER) build --progress=plain --target=$(DOCKER_BUILD_TARGET) $(DOCKER_BUILD_OPTIONS) -t $(DOCKER_IMAGE) $(foreach tag,$(VERSION) $(DOCKER_TAGS),-t $(DOCKER_IMAGE):$(tag)$(DOCKER_TAGS_SUFFIX)) .

build-dev:
	poetry export --with=dev -f requirements.txt --output requirements.$@.txt
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) DOCKER_BUILD_TARGET=development $(MAKE) build

push:
	for tag in $(VERSION) $(DOCKER_TAGS); do \
		$(DOCKER) image push $(DOCKER_IMAGE):$$tag$(DOCKER_TAGS_SUFFIX); \
	done

push-dev:
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) push

release:
	DOCKER_IMAGE=makersquad/$(NAME) DOCKER_TAGS=latest bin/sandbox $(MAKE) test-full build push

run:
	$(DOCKER) run -it -p 4080:4080 --rm $(DOCKER_IMAGE)

run-shell:
	$(DOCKER) run -it -p 4080:4080 --rm $(DOCKER_IMAGE) ash -l

run-dev:
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) run

run-dev-shell:
	DOCKER_IMAGE=$(DOCKER_IMAGE_DEV) $(MAKE) run-shell
