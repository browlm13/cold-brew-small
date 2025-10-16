# Regtest (Peace-of-Mind Test)

**Goal:** Prove your key can receive and spend on a local Bitcoin network (regtest), with instant blocks and no internet.

### Requirements
- Bitcoin Core: `bitcoind`, `bitcoin-cli`
- `jq` for JSON parsing (used by the harness)

### Inputs (from `SECRET_DO_NOT_EXPORT.txt`)
- `WIF (regtest)` — private key in WIF format for regtest use (only for test)
- `P2PKH (regtest)` — the legacy address used in the regtest flow

> Keep these values offline. The harness writes a `regtest_result.txt` in your run dir and exits non-zero on any failure.

### Run the harness (fast path — Path A)
This mode imports the regtest WIF on the regtest node (so the WIF briefly exists on the Core machine). It is the simpler flow and the default for Cold Brew (Small).

```bash
chmod +x scripts/regtest_check.sh
scripts/regtest_check.sh "<REGTEST_WIF>" "<REGTEST_P2PKH_ADDR>" out/<your-run-dir>
```
#### The script will:

1. Start a temporary bitcoind -regtest instance in a fresh datadir.
2. Create a wallet and mine 101 blocks (gives spendable balance).
3. Import your regtest WIF into that temporary wallet.
4. Fund your regtest address and create a spend transaction.
5. Sign the spend with your WIF, broadcast it, mine a confirming block.
6. Write regtest_result.txt which begins with either: ` REGTEST_STATUS: PASS ` or `REGTEST_STATUS: FAIL`

	It also includes `FUNDING_TXID`, `SPENDING_TXID`, `BLOCKHASH`, `ADDR_IN`, and `DATE_UTC`.

If the script exits non-zero or `REGTEST_STATUS` is `FAIL`, do not trust those keys on mainnet.


### Strict air-gap variant (optional — PATH B)

If you *must* never have the WIF on the Core machine, use the strict offline-sign flow:

1. On the Core machine: create and fund a UTXO to your regtest address and export an unsigned transaction (plus prevout details).
2. Move the unsigned tx and prevout JSON to the air-gapped box.
3. Sign the transaction offline with the private key (your preferred offline sign tool); produce the signed hex.
4. Move the signed hex back to the Core machine and broadcast it.
5. Mine a block to confirm.

This flow is more complex to automate; Cold Brew (Small) uses the fast path to minimize complexity and help you validate quickly.

