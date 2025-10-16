# SETUP (Bitcoin Core, Airgap & Regtest)

This doc explains how to obtain Bitcoin Core, verify it, and run a local regtest node for offline verification.

## 1. Download Bitcoin Core

Get official releases from:  
https://bitcoincore.org/en/download/

Pick the binary tarball that matches your OS and CPU architecture (e.g. `bitcoin-25.x-x86_64-linux-gnu.tar.gz`).

## 2. Verify the download (recommended)

1. Download the checksum file and its PGP signature (`SHA256SUMS` and `SHA256SUMS.asc`) from the same page.
2. Verify checksums:
   ```bash
   sha256sum -c SHA256SUMS
   ```

3. Verify the PGP signature of SHA256SUMS.asc against the maintainer keys. (Optional if you already trust the checksum source.)
Verifying prevents tampered binaries from being used on your air-gapped machine.

## 3. Unpack and prepare
Extract the tarball on the air-gapped machine (or on a clean staging machine and copy binaries to the air-gapped box):

```
tar xf bitcoin-25.x-x86_64-linux-gnu.tar.gz
# Optionally add to PATH for the current shell:
export PATH="$PWD/bitcoin-25.x/bin:$PATH" 
```

You do not need to "install" anything system-wide; the binaries are portable.

## 4. Run a quick regtest sanity check (manual)
Start a regtest node (no internet required):

```
bitcoind -regtest -daemon
bitcoin-cli -regtest createwallet "master"
ADDR=$(bitcoin-cli -regtest getnewaddress)
bitcoin-cli -regtest generatetoaddress 101 "$ADDR"
bitcoin-cli -regtest getbalance 
```
If you see a positive balance, regtest is up and mining. Now you can run the automated harness:

``` bash scripts/regtest_check.sh "<REGTEST_WIF>" "<REGTEST_P2PKH_ADDR>" out/<your-run-dir> ```

## Notes & best practices

- Use a Live USB OS for the air-gapped machine if possible (Debian Live or Ubuntu Live are recommended).
- Use a second USB for payloads (your cold-brew-small/ repo, wordlist.txt, and the Core tarball).
- Physically disable network hardware (Wi-Fi / Bluetooth) if the machine allows it.
- Shutdown the Live OS when finished to clear RAM.