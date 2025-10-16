PY=python3

# Usage examples:
# make generate WORDS23="abandon ability able ..." OUTDIR=out/test-run
# make generate HEX=0123...abcd
# make verify MNEMONIC="..." HEX="..."
# make regtest WIF=... ADDR=... OUTDIR=out/test-run

generate:
	@if [ -n "$$WORDS23" ]; then \
		$(PY) scripts/coldgen.py --words23 "$$WORDS23" --no-stdout-secrets --hex-group 8 --hex-grid $${OUTDIR:+--outdir $$OUTDIR}; \
	elif [ -n "$$WORDS" ]; then \
		$(PY) scripts/coldgen.py --words "$$WORDS" --no-stdout-secrets --hex-group 8 --hex-grid $${OUTDIR:+--outdir $$OUTDIR}; \
	elif [ -n "$$HEX" ]; then \
		$(PY) scripts/coldgen.py --hex "$$HEX" --no-stdout-secrets --hex-group 8 --hex-grid $${OUTDIR:+--outdir $$OUTDIR}; \
	else \
		echo "Provide WORDS23=... OR WORDS=... OR HEX=..."; exit 2; \
	fi

verify:
	@if [ -z "$$MNEMONIC" ] && [ -z "$$HEX" ]; then echo "Provide MNEMONIC=... and/or HEX=..."; exit 2; fi
	$(PY) scripts/verify_consistency.py $${MNEMONIC:+--mnemonic "$$MNEMONIC"} $${HEX:+--hex "$$HEX"}

regtest:
	@if [ -z "$$WIF" ] || [ -z "$$ADDR" ]; then echo "Provide WIF=... ADDR=..."; exit 2; fi
	bash scripts/regtest_check.sh "$$WIF" "$$ADDR" $${OUTDIR:-.}

.PHONY: generate verify regtest
