# SETUP (Bitcoin Core, Airgap & Regtest)

## Bitcoin Core binaries
Download from the official site:
- https://bitcoincore.org/en/download/

Verify:
1. Download `SHA256SUMS` and `SHA256SUMS.asc`
2. Verify checksums: `sha256sum -c SHA256SUMS`
3. Verify PGP signature of `SHA256SUMS.asc` against maintainer keys.

Extract `bitcoind` and `bitcoin-cli` and put them in your PATH on the machine you’ll use for regtest.  
No internet is required to run regtest.

## Quick regtest sanity (manual)
```bash
bitcoind -regtest -daemon
bitcoin-cli -regtest createwallet "master"
ADDR=$(bitcoin-cli -regtest getnewaddress)
bitcoin-cli -regtest generatetoaddress 101 "$ADDR"
bitcoin-cli -regtest getbalance

If you see a positive balance, regtest is up and mining.
Now use scripts/regtest_check.sh to run the automated PASS/FAIL flow.


---

# docs/REGTEST.md  (how to use the harness)

```markdown
# Regtest (Peace-of-Mind Test)

**Goal:** Prove your key can receive and spend on a local Bitcoin network (regtest), with instant blocks, no internet.

## Requirements
- Bitcoin Core: `bitcoind`, `bitcoin-cli`
- `jq` for JSON parsing

## Inputs (from SECRET_DO_NOT_EXPORT.txt)
- `WIF (regtest)`
- `P2PKH (regtest)`

## Run
```bash
chmod +x scripts/regtest_check.sh
scripts/regtest_check.sh "<REGTEST_WIF>" "<REGTEST_P2PKH_ADDR>" out/<your-run-dir>

Outputs:
regtest_result.txt with:

REGTEST_STATUS: PASS
FUNDING_TXID:  ...
SPENDING_TXID: ...
BLOCKHASH:     ...
ADDR_IN:       ...
DATE_UTC:      ...

Exit code is non-zero on FAIL. If it fails, do not use those keys until you resolve the issue.
Strict air-gap variant (optional, not included here)
Build an unsigned tx on the Core machine, sign offline with the key on your air-gapped box, then broadcast.
We keep the small kit on Path A to minimize complexity.


---

# README.md  (big, clean, “beautiful” doc)

```markdown
# Cold Brew (Small)

**Minimal, auditable cold wallet generator + local regtest verifier.**

- **Air-gapped generator** (`scripts/coldgen.py`): input **23 or 24 BIP-39 words** *or* **64-hex** (32 bytes), outputs mainnet address(es) + tidy pubkey + clean files.  
- **Regtest harness** (`scripts/regtest_check.sh`): single-node Bitcoin Core regtest that proves your key can **receive and spend** (PASS/FAIL), no internet.  
- **No external Python deps.** All consensus-critical crypto in the test is validated by **Bitcoin Core (libsecp256k1)**.

---

## Table of Contents

1. [Security Model](#security-model)
2. [What This Mnemonic Is (and Is Not)](#what-this-mnemonic-is-and-is-not)
3. [Requirements](#requirements)
4. [Quick Start](#quick-start)
5. [Files & Outputs](#files--outputs)
6. [Flags Reference](#flags-reference)
7. [Integrity & Audit (Manifest)](#integrity--audit-manifest)
8. [Regtest Guide](#regtest-guide)
9. [Watch-Only Monitoring (How-To)](#watchonly-monitoring-howto)
10. [Curve & Encodings Appendix](#curve--encodings-appendix)
11. [Minimum Essentials to Recover Funds](#minimum-essentials-to-recover-funds)
12. [Reproducible Setup Notes](#reproducible-setup-notes)
13. [License](#license)

---

## Security Model

- Run the generator on an **air-gapped machine** (e.g., Live USB OS).
- The script sets **`umask 077`** so new files are owner-only. Secrets are written to a **SECRET** file and **not printed** unless you ask (`--print-secrets`).
- Output separation:
  - `PUBLIC_EXPORT.txt` → ✅ safe to copy/QR
  - `SECRET_DO_NOT_EXPORT.txt` → ❌ never copy/photo/network
  - `MANIFEST.SHA256` → hashes of outputs + script self-hash + wordlist hash (for audit)
- Regtest needs **Bitcoin Core**, but **no internet** (local single-node chain).

---

## What This Mnemonic Is (and Is Not)

**Is:** A 24-word BIP-39 English mnemonic that **encodes the raw 32-byte private key**.  
**Is Not:** The usual BIP-39 → PBKDF2 “seed” used by hierarchical deterministic (HD) wallets.  
- If you later feed these 24 words into an HD wallet expecting a seed, you will get **different keys/addresses**.  
- We document this clearly in outputs. Engrave that note on your plate if you use the 24 words.

---

## Requirements

- **Python 3.8+** (generator and verifier use only stdlib).
- **wordlist.txt** (BIP-39 English, 2048 words) + **wordlist.txt.sha256**.  
  You include it once; the generator verifies its hash each run for tamper-resistance.
- **Bitcoin Core** (`bitcoind`, `bitcoin-cli`) and `jq` for the regtest harness.  
  No internet needed. See `docs/SETUP.md`.

---

## Quick Start

### 0) Prepare wordlist
```bash
sha256sum wordlist.txt > wordlist.txt.sha256

1) Generate (air-gapped)
23 words → compute 24th

python3 scripts/coldgen.py --words23 "word1 ... word23" --no-stdout-secrets --hex-group 8 --hex-grid

24 words (checksum verified)

python3 scripts/coldgen.py --words "word1 ... word24" --no-stdout-secrets --hex-group 8 --hex-grid

64 hex (32 bytes) → 24 words

python3 scripts/coldgen.py --hex 0123...abcd --no-stdout-secrets --hex-group 8 --hex-grid

Outputs go to out/<YYYY-mm-dd_HH-MM-SS_RUNXXXX>/.
2) Consistency check (optional)
Prove mnemonic and hex represent the same private key / pubkey:

python3 scripts/verify_consistency.py --mnemonic "24 words..." --hex 0123...abcd
# expect: OK (exit 0)

3) Peace-of-mind regtest (Core box, no internet)
From the SECRET file, take WIF (regtest) and P2PKH (regtest):

chmod +x scripts/regtest_check.sh
scripts/regtest_check.sh "<REGTEST_WIF>" "<REGTEST_P2PKH_ADDR>" out/<same-run-dir>

You’ll get regtest_result.txt with REGTEST_STATUS: PASS and txids/blockhash.
Exit code is non-zero on FAIL.
4) What to carry on USB
PUBLIC_EXPORT.txt
regtest_result.txt (optional proof)
MANIFEST.SHA256 (optional audit trail)
Do NOT copy SECRET_DO_NOT_EXPORT.txt or regtest_expected.json.

Files & Outputs
Inside out/<timestamp>_RUN<id>/:
PUBLIC_EXPORT.txt (✅ Safe)
bc1 address (P2WPKH)
legacy P2PKH (Base58)
compressed pubkey hex
QR payload lines (qr/bc1.txt, qr/pubkey.txt)
snippet showing how to import watch-only (see below)
SECRET_DO_NOT_EXPORT.txt (❌ Secret)
Minimum Essentials banner (either 24 words or 64-hex)
24-word mnemonic (encodes raw 32-byte private key)
32-byte private key hex (grouped; plus optional 8×4 hex grid)
compressed pubkey hex
mainnet addresses + WIF (mainnet, compressed)
Regtest helpers (WIF + P2PKH) unless disabled
MANIFEST.SHA256
SHA-256 of the above files
self-hash of coldgen.py
SHA-256 of wordlist.txt
regtest_expected.json (SECRET, contains regtest WIF, used by harness—keep offline)
qr/ (✅ public payloads)
bc1.txt, pubkey.txt
Flags Reference
Flag	Meaning
--words23 "..."	Provide 23 words (English). Tool computes the 24th word.
--words "..."	Provide 24 words; checksum is validated.
--hex HEX64	Provide 64-hex (32-byte private key). Encodes to 24 words.
--no-stdout-secrets	Default ON. Do not print mnemonic/hex to terminal.
--print-secrets	Override to print secrets to stdout. Use sparingly.
--no-regtest-helpers	Omit regtest WIF/address from outputs.
--hex-group {2,4,8,16,32}	Group hex output for readability (default 8).
--hex-grid	Add an 8×4 hex grid of the private key to the SECRET file (great for stamping).
--outdir DIR	Override the timestamped run directory path.
You may provide both --words/--words23 and --hex; they must match.
Integrity & Audit (Manifest)
The generator writes MANIFEST.SHA256 containing:
SHA-256 of PUBLIC_EXPORT.txt, SECRET_DO_NOT_EXPORT.txt, regtest_expected.json
SHA-256 of the exact scripts/coldgen.py used (self-hash)
SHA-256 of wordlist.txt
Why it helps:
You can prove which exact artifacts were produced and by which script version and wordlist.
On your online box, you can verify PUBLIC_EXPORT.txt and MANIFEST.SHA256 match (without touching secrets).
Optional: sign the manifest with an offline GPG key if you want provenance.
Regtest Guide
See docs/REGTEST.md.
Summary: A local single-node blockchain that needs no internet. The harness:
starts bitcoind -regtest,
mines spendable coins,
funds your regtest address,
creates & signs a spend with your WIF,
broadcasts, mines a confirmation,
writes PASS/FAIL + txids + blockhash.
Failure = do not use these keys on mainnet until resolved.
Watch-Only Monitoring (How-To)
We don’t ship a script for this in Small to keep it lean. Here’s the exact CLI:

# Create a watch-only wallet (no private keys)
bitcoin-cli createwallet "watchonly" true

# Import your mainnet bc1 address (from PUBLIC_EXPORT.txt)
bitcoin-cli -rpcwallet=watchonly importaddress "bc1qYourAddr" "" false

# Monitor
bitcoin-cli -rpcwallet=watchonly getbalance
bitcoin-cli -rpcwallet=watchonly listtransactions "*" 100

This lets you (or a parent) track deposits safely. The node cannot spend because it has no keys.
Curve & Encodings Appendix
Curve: secp256k1 over Fp where
p = 2^256 − 2^32 − 977, equation y^2 = x^3 + 7, generator G of order
n = FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFE BAAEDCE6 AF48A03B BFD25E8C D0364141.
Compressed pubkey (33 bytes): prefix 0x02 or 0x03 (y-parity) + 32-byte x-coordinate.
Bech32 P2WPKH (bc1): bc1 + data for version 0 witness program (20-byte HASH160(pubkey)), encoded per BIP-0173.
Legacy P2PKH (Base58): version 0x00 + HASH160(pubkey) + 4-byte checksum, Base58Check.
WIF (mainnet, compressed): Base58Check of 0x80 + 32-byte privkey + 0x01.
(Regtest/Testnet WIF uses 0xEF instead of 0x80.)
Minimum Essentials to Recover Funds
You need ONE of the following (either is sufficient):
The 24 BIP-39 words (English, exact order) — this mnemonic encodes your raw 32-byte private key (NOT the standard BIP-39 seed)
OR
The 32-byte private key (64 hex characters)
Do not lose them. Do not copy/photograph the SECRET file.
Reproducible Setup Notes
We ship no Python deps. Everything uses the stdlib.
The regtest proof relies on Bitcoin Core’s libsecp256k1.
The wordlist is checked against wordlist.txt.sha256 each run. If you replace the list, update the hash file.
License
MIT


cold-brew-small/
├─ LICENSE
├─ README.md
├─ .gitignore
├─ wordlist.txt                 # (BIP-39 English list you include once)
├─ wordlist.txt.sha256          # (sha256sum of wordlist.txt)
├─ Makefile
├─ scripts/
│  ├─ coldgen.py
│  ├─ verify_consistency.py
│  └─ regtest_check.sh
├─ docs/
│  ├─ REGTEST.md
│  └─ SETUP.md
└─ out/                         # created at runtime
