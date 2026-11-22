# Makefile for pkm. make install PREFIX=DIR copies pkm to DIR/lib/pkm-<version>/ and links DIR/bin/pkm to it.
# PREFIX defaults to $(HOME)/.local. make dist writes DIST/pkm-<version>.tar.gz and its .sha256 (DIST defaults to dist).
# Both copy the example vaults of docs/examples into share/pkm/examples, for pkm example.
VERSION := $(shell cat VERSION)
PREFIX ?= $(HOME)/.local
DIST ?= dist

.PHONY: install uninstall dist check examples

install:
	prefix=$$(mkdir -p "$(PREFIX)" && cd "$(PREFIX)" && pwd) && \
	lib="$$prefix/lib/pkm-$(VERSION)" && \
	rm -rf "$$lib" && mkdir -p "$$lib" "$$prefix/bin" && \
	cp -R bin lib share VERSION "$$lib/" && \
	$(MAKE) --no-print-directory examples TO="$$lib/share/pkm/examples" && \
	ln -sf "$$lib/bin/pkm" "$$prefix/bin/pkm" && \
	echo "pkm $(VERSION) installed in $$lib, linked as $$prefix/bin/pkm"

uninstall:
	prefix=$$(cd "$(PREFIX)" 2>/dev/null && pwd) || exit 0; \
	rm -rf "$$prefix/lib/pkm-$(VERSION)"; \
	if [ -L "$$prefix/bin/pkm" ] && [ "$$(readlink "$$prefix/bin/pkm")" = "$$prefix/lib/pkm-$(VERSION)/bin/pkm" ]; then rm -f "$$prefix/bin/pkm"; fi

dist:
	mkdir -p "$(DIST)" && stage="$(DIST)/pkm-$(VERSION)" && rm -rf "$$stage" && mkdir -p "$$stage" && \
	cp -R bin lib share install.sh LICENSE README.md CHANGELOG.md VERSION "$$stage/" && \
	$(MAKE) --no-print-directory examples TO="$$stage/share/pkm/examples" && \
	tar -C "$(DIST)" -czf "$(DIST)/pkm-$(VERSION).tar.gz" "pkm-$(VERSION)" && rm -rf "$$stage" && \
	cd "$(DIST)" && if command -v sha256sum >/dev/null 2>&1; then sha256sum "pkm-$(VERSION).tar.gz"; else shasum -a 256 "pkm-$(VERSION).tar.gz"; fi > "pkm-$(VERSION).tar.gz.sha256" && \
	echo "wrote $(DIST)/pkm-$(VERSION).tar.gz"

# examples TO=DIR: copies the example vaults of docs/examples into DIR, for pkm example, without the cache and state
# that running pkm in them leaves in .pkm.
examples:
	mkdir -p "$(TO)" && (cd docs/examples && tar -cf - --exclude '*/.pkm/cache' --exclude '*/.pkm/state' */) | (cd "$(TO)" && tar -xf -)

check:
	python3 scripts/check.py
	python3 -m unittest discover -s tests
