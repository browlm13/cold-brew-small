#!/usr/bin/env bash
set -euo pipefail

# Regtest harness (Path A): imports your REGTEST WIF, funds and spends.
# Usage: regtest_check.sh "<REGTEST_WIF>" "<REGTEST_P2PKH_ADDR>" [outdir]
# Writes regtest_result.txt to [outdir]. Exits non-zero on FAIL.

if [ $# -lt 2 ] || [ $# -gt 3 ]; then
  echo "Usage: $0 \"<REGTEST_WIF>\" \"<REGTEST_P2PKH_ADDR>\" [outdir]"
  exit 2
fi
WIF="$1"; ADDR_IN="$2"; OUTDIR="${3:-.}"
mkdir -p "$OUTDIR"

command -v bitcoind >/dev/null || { echo "bitcoind not found"; exit 3; }
command -v bitcoin-cli >/dev/null || { echo "bitcoin-cli not found"; exit 3; }
command -v jq >/dev/null || { echo "jq not found (install jq)"; exit 3; }

RTDIR="$(mktemp -d -t cb-rt-XXXXXXXX)"
trap 'echo "Regtest datadir: $RTDIR"' EXIT
RESULT="$OUTDIR/regtest_result.txt"

fail() {
  echo "REGTEST_STATUS: FAIL" > "$RESULT"
  echo "ERROR: $1" | tee -a "$RESULT" >&2
  exit 1
}

echo "[*] Starting regtest node..."
bitcoind -regtest -daemon -datadir="$RTDIR" >/dev/null 2>&1 || fail "bitcoind failed to start"
sleep 1
bitcoin-cli -regtest -datadir="$RTDIR" createwallet master false >/dev/null || fail "createwallet failed"

echo "[*] Mining 101 blocks for spendable balance..."
FUND=$(bitcoin-cli -regtest -datadir="$RTDIR" -rpcwallet=master getnewaddress) || fail "getnewaddress"
bitcoin-cli -regtest -datadir="$RTDIR" -rpcwallet=master generatetoaddress 101 "$FUND" >/dev/null || fail "mine"
BAL=$(bitcoin-cli -regtest -datadir="$RTDIR" -rpcwallet=master getbalance) || fail "getbalance"
echo "    Balance: $BAL BTC"

echo "[*] Importing your REGTEST WIF..."
bitcoin-cli -regtest -datadir="$RTDIR" -rpcwallet=master importprivkey "$WIF" "coldkey" false >/dev/null || fail "importprivkey"

echo "[*] Funding your address: $ADDR_IN"
RAW=$(bitcoin-cli -regtest -datadir="$RTDIR" -rpcwallet=master createrawtransaction "[]" "{\"$ADDR_IN\":10}") || fail "createrawtransaction fund"
FRD=$(bitcoin-cli -regtest -datadir="$RTDIR" -rpcwallet=master fundrawtransaction "$RAW" | jq -r .hex) || fail "fundrawtransaction"
S1=$(bitcoin-cli -regtest -datadir="$RTDIR" -rpcwallet=master signrawtransactionwithwallet "$FRD" | jq -r .hex) || fail "signrawtransactionwithwallet"
TXID_FUND=$(bitcoin-cli -regtest -datadir="$RTDIR" sendrawtransaction "$S1") || fail "sendrawtransaction fund"
bitcoin-cli -regtest -datadir="$RTDIR" -rpcwallet=master generatetoaddress 1 "$FUND" >/dev/null || fail "mine block"
echo "    Funding TXID: $TXID_FUND"

echo "[*] Locating your UTXO..."
UJSON=$(bitcoin-cli -regtest -datadir="$RTDIR" -rpcwallet=master listunspent 0 9999999 "[\"$ADDR_IN\"]") || fail "listunspent"
CNT=$(echo "$UJSON" | jq 'length')
[ "$CNT" -ge 1 ] || fail "no UTXO found for $ADDR_IN"
TXID=$(echo "$UJSON" | jq -r '.[0].txid'); VOUT=$(echo "$UJSON" | jq -r '.[0].vout')
AMNT=$(echo "$UJSON" | jq -r '.[0].amount'); SCRIPT=$(echo "$UJSON" | jq -r '.[0].scriptPubKey')

echo "[*] Creating unsigned spend back to wallet..."
DEST=$(bitcoin-cli -regtest -datadir="$RTDIR" -rpcwallet=master getnewaddress) || fail "getnewaddress dest"
AMNT_OUT=$(python3 - <<PY
import decimal; print("{:.8f}".format(decimal.Decimal("$AMNT")-decimal.Decimal("0.0001")))
PY
)
UNSIGNED=$(bitcoin-cli -regtest -datadir="$RTDIR" createrawtransaction "[{\"txid\":\"$TXID\",\"vout\":$VOUT}]" "{\"$DEST\":$AMNT_OUT}") || fail "createrawtransaction spend"

echo "[*] Signing with your WIF..."
SIGNED=$(bitcoin-cli -regtest -datadir="$RTDIR" signrawtransactionwithkey "$UNSIGNED" "[\"$WIF\"]" \
  "[{\"txid\":\"$TXID\",\"vout\":$VOUT,\"scriptPubKey\":\"$SCRIPT\",\"amount\":$AMNT}]") || fail "signrawtransactionwithkey"
HEX=$(echo "$SIGNED" | jq -r .hex)

echo "[*] Broadcasting & mining confirmation block..."
TXID_SPEND=$(bitcoin-cli -regtest -datadir="$RTDIR" sendrawtransaction "$HEX") || fail "sendrawtransaction spend"
bitcoin-cli -regtest -datadir="$RTDIR" -rpcwallet=master generatetoaddress 1 "$FUND" >/dev/null || fail "mine block"
BLK=$(bitcoin-cli -regtest -datadir="$RTDIR" getrawtransaction "$TXID_SPEND" true | jq -r .blockhash) || fail "getrawtransaction blockhash"

{
  echo "REGTEST_STATUS: PASS"
  echo "FUNDING_TXID:  $TXID_FUND"
  echo "SPENDING_TXID: $TXID_SPEND"
  echo "BLOCKHASH:     $BLK"
  echo "ADDR_IN:       $ADDR_IN"
  echo "DATE_UTC:      $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
} > "$RESULT"

echo "=== RESULT ==="
cat "$RESULT"
