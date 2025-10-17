# Cold Brew (Small)

**Minimal, auditable cold wallet generator + local regtest verifier.**

- **Air-gapped generator** (`scripts/coldgen.py`): input **23 or 24 BIP-39 words** or **64-hex** (32 bytes), outputs mainnet address(es), compressed pubkey, and tidy export files.  
- **Regtest harness** (`scripts/regtest_check.sh`): single-node Bitcoin Core regtest that proves the key can **receive and spend** (PASS/FAIL), no internet required.  
- **No external Python deps.** The regtest proof relies on Bitcoin Core's `libsecp256k1`.

---

## Table of Contents

1. [Security Model](#security-model)  
2. [What this mnemonic *is* (and is *not*)](#what-this-mnemonic-is-and-is-not)  
3. [Requirements](#requirements)  
4. [Quick Start](#quick-start)  
5. [Files & Outputs](#files--outputs)  
6. [Flags Reference](#flags-reference)  
7. [Integrity & Audit (Manifest)](#integrity--audit-manifest)  
8. [Regtest Guide](#regtest-guide)  
9. [Watch-Only Monitoring (How-To)](#watch-only-monitoring-how-to)  
10. [Curve & Encodings Appendix](#curve--encodings-appendix)  
11. [Minimum Essentials to Recover Funds](#minimum-essentials-to-recover-funds)  
12. [Reproducible Setup Notes](#reproducible-setup-notes)  
13. [License](#license)

---

## Security Model

- Run `scripts/coldgen.py` on an **air-gapped** machine (prefer a Live USB OS).  
- The script sets `umask 077`, writes secrets to `SECRET_DO_NOT_EXPORT.txt` (owner-only) and prints only public outputs unless you explicitly request secrets.  
- Separation:
  - `PUBLIC_EXPORT.txt` — safe to copy/QR.
  - `SECRET_DO_NOT_EXPORT.txt` — never copy, photograph, or store on networked media.
  - `MANIFEST.SHA256` — cryptographic checksums of outputs and the script used to create them.

---

## What this mnemonic is (and is not)

**This project uses a 24-word BIP-39 mnemonic that encodes the raw 32-byte private key.**  
This is *not* the usual BIP-39 → PBKDF2 seed used by HD wallets. Feeding these words into an HD wallet will generally produce *different* addresses. We clearly warn about that in the output files — engrave that note if you stamp words into metal.

---

## Requirements

- **Python 3.8+** (generator & verifier use stdlib only).  
- `wordlist.txt` (BIP-39 English, 2048 words) and `wordlist.txt.sha256` (you provide once).  
- For regtest: **Bitcoin Core** (`bitcoind`, `bitcoin-cli`) and `jq`. No internet required.

---

## Quick Start

### 0) Prepare the wordlist
```bash
sha256sum wordlist.txt > wordlist.txt.sha256
```

### 1) Generate (air-gapped)

23 words → compute 24th (recommended for manual word entry)

```bash
python3 scripts/coldgen.py --words23 "word1 ... word23" --no-stdout-secrets --hex-group 8 --hex-grid
```

24 words (checksum verified)

```bash
python3 scripts/coldgen.py --words "word1 ... word24" --no-stdout-secrets --hex-group 8 --hex-grid
```

64 hex (32 bytes) → 24 words

```bash
python3 scripts/coldgen.py --hex 0123...abcd --no-stdout-secrets --hex-group 8 --hex-grid
```

Outputs: `out/<YYYY-mm-dd_HH-MM-SS_RUNID>/`

### 2) Consistency check (optional)

Normal verification:

```bash
python3 scripts/verify_consistency.py --mnemonic "24 words..." --hex 0123...abcd
# expected output: OK
```

Extra pubkey check (helpful if someone accidentally copied pubkey into --hex)

```bash
python3 scripts/verify_consistency.py --mnemonic "..." --hex 0000...abcd --pubkey 02...
```

### 3) Regtest (Core box, offline)

From `SECRET_DO_NOT_EXPORT.txt` copy the `WIF (regtest)` and `P2PKH (regtest)` (keep the secret file offline):

```bash
chmod +x scripts/regtest_check.sh
scripts/regtest_check.sh "<REGTEST_WIF>" "<REGTEST_P2PKH_ADDR>" out/<same-run-dir>
```

You’ll get `regtest_result.txt` with `REGTEST_STATUS:` `PASS` or `FAIL` (script exits non-zero on fail).

### 4) Files to carry on USB

`PUBLIC_EXPORT.txt` (addresses, pubkey, QR payloads) — safe to copy.
`regtest_result.txt` (optional proof) — safe to copy.
`MANIFEST.SHA256` (optional audit record).
Do not copy `SECRET_DO_NOT_EXPORT.txt`.

## Files & Outputs

Each run creates a timestamped folder containing:

- `PUBLIC_EXPORT.txt` — safe, human-readable public info & QR payloads.
- `SECRET_DO_NOT_EXPORT.txt` — secret; contains mnemonic, private hex, hex-grid (if requested), pubkey, WIF (mainnet) and regtest helpers (unless disabled).
- `MANIFEST.SHA256` — hashes for audit: public file, secret file, hint json, self-hash, wordlist hash.
- `regtest_expected.json` — contains regtest WIF (secret; keep offline).
- `qr/` — `bc1.txt`, `pubkey.txt`


## Flags Reference

Flag  What it does

- `--words23 "..."` Provide 23 words; the tool computes the 24th (checksum).
- `--words "..."` Provide 24 words; tool verifies checksum.
- `--hex HEX64` Provide 64 hex characters (32 bytes); the tool will encode them to a 24-word mnemonic.
- `--no-stdout-secrets` Default ON: secrets are not printed to stdout.
- `--print-secrets` Override to print secrets to stdout.
- `--no-regtest-helpers`  Omit regtest WIF/address from output files.
- `--hex-group {2,4,8,16,32}` Group hex output (default 8).
- `--hex-grid`  Add an 8×4 hex grid for the private key (handy for stamping).
- `--outdir DIR`  Override run directory path.

You may supply both words and hex; they must encode the same 32 bytes.

## Integrity & Audit (Manifest)

`MANIFEST.SHA256` lists:
- SHA-256 of `PUBLIC_EXPORT.txt`, `SECRET_DO_NOT_EXPORT.txt`, and `regtest_expected.json`
- SHA-256 (self-hash) of `scripts/coldgen.py`
- SHA-256 of `wordlist.txt`

**Usage**: Keep `MANIFEST.SHA256` with the public export and proof files. It documents *exactly* which script and wordlist created that run. Optionally sign the manifest with an offline GPG key.

## Regtest Guide

*(See* `docs/REGTEST.md` *for full details.)*

**Short summary**: the harness runs a local `bitcoind -regtest`, mines blocks, funds your test address, signs and broadcasts a test spend, and reports PASS/FAIL with txids and blockhash. If it fails, do not trust the key for mainnet use until debugged.

## Watch-Only Monitoring (How-To)

To monitor a mainnet address safely (no private keys), run on your node:

```bash
bitcoin-cli createwallet "watchonly" true
bitcoin-cli -rpcwallet=watchonly importaddress "bc1qYourMainnetAddr" "" false
bitcoin-cli -rpcwallet=watchonly getbalance
```

This creates a wallet that stores no private keys and can only monitor activity.

## Curve & Encodings Appendix

- Curve: **secp256k1** (prime field `p = 2^256 − 2^32 − 977`) with `y^2 = x^3 + 7`.
- **Compressed pubkey (33 bytes)**: prefix byte `0x02` or `0x03` (y parity) + 32-byte x coordinate.
- **Bech32 (P2WPKH)**: version 0 witness program with 20-byte HASH160(pubkey) encoded per BIP-0173 -> bc1q....
- **P2PKH (legacy)**: Base58Check of `0x00 || HASH160(pubkey)` + checksum -> `1...`.
- **WIF**: Base58Check of `0x80 || privkey || 0x01` (compressed flag). Regtest/testnet uses `0xEF` instead of `0x80`.

## Minimum Essentials to Recover Funds

You need **one** of the following:

- The **24 BIP-39 words** (English, exact order) — **these words encode your raw 32-byte private key** (not the standard BIP-39 seed), or
- The **32-byte private key** (64 hex characters)

Record one of these reliably and keep it offline. Do not photograph or upload it.

## Reproducible Setup Notes

- The generator uses the Python stdlib only.
- The regtest proof relies on Bitcoin Core (libsecp256k1).
- The wordlist is checked against `wordlist.txt.sha256` on each run.

## License

MIT
