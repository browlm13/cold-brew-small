#!/usr/bin/env python3
# Cold Brew (Small) - coldgen.py
# Dual-input generator: 23 or 24 words OR 64-hex → mainnet outputs (and regtest helpers unless disabled).
# - Verifies wordlist.txt against wordlist.txt.sha256
# - Writes a timestamped run dir with PUBLIC + SECRET packets, manifest, and QR payloads
# - Self-hash of this script and wordlist hash included in MANIFEST
# - Tight perms: umask 077, SECRET file chmod 600
# Flags:
#   --words23 "w1 ... w23"  |  --words "w1 ... w24"  |  --hex 64HEX
#   [You may pass both --words/--words23 and --hex; they must match the same 32-byte key]
#   --no-stdout-secrets (default ON) | --print-secrets
#   --no-regtest-helpers
#   --hex-group {2,4,8,16,32} (default 8)
#   --hex-grid
#   --outdir DIR

import sys, os, argparse, hashlib, datetime, json

WORDLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "wordlist.txt")
WORDLIST_SHA  = os.path.join(os.path.dirname(__file__), "..", "wordlist.txt.sha256")

os.umask(0o077)

def sha256_hex(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""): h.update(chunk)
    return h.hexdigest()
def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f: return f.read()
def write_text(path: str, s: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: f.write(s)
    return sha256_file(path)
def self_hash() -> str: return sha256_file(os.path.realpath(__file__))

def verify_wordlist():
    if not os.path.exists(WORDLIST_PATH): sys.exit("ERROR: missing wordlist.txt")
    if not os.path.exists(WORDLIST_SHA): sys.exit("ERROR: missing wordlist.txt.sha256 (run: sha256sum wordlist.txt > wordlist.txt.sha256)")
    line = read_text(WORDLIST_SHA).strip().split()
    if len(line) < 2 or line[-1] != "wordlist.txt": sys.exit("ERROR: wordlist.txt.sha256 format is '<sha256>  wordlist.txt'")
    expected = line[0].lower()
    actual = sha256_file(WORDLIST_PATH).lower()
    if actual != expected: sys.exit(f"ERROR: wordlist sha256 mismatch:\n expected {expected}\n   actual {actual}")
    wl = [w.strip() for w in read_text(WORDLIST_PATH).splitlines() if w.strip()]
    if len(wl) != 2048: sys.exit("ERROR: wordlist must have 2048 words")
    return wl, expected

def bytes_to_bits(b: bytes)->str: return ''.join(f"{x:08b}" for x in b)
def bits_to_bytes(bs: str)->bytes:
    assert len(bs)%8==0
    return bytes(int(bs[i:i+8],2) for i in range(0,len(bs),8))
def checksum_bits(ent: bytes)->str: return bytes_to_bits(hashlib.sha256(ent).digest())[:len(ent)*8//32]

def words_to_bits(words, WL):
    out=""
    for w in words:
        try: idx = WL.index(w)
        except ValueError: sys.exit(f"ERROR: bad word: '{w}'")
        out += f"{idx:011b}"
    return out

def find_24th_word(words23, WL):
    if len(words23) != 23: sys.exit("ERROR: need exactly 23 words")
    bits = words_to_bits(words23, WL)  # 253 bits
    for idx in range(2048):
        cand = bits + f"{idx:011b}"     # 264 bits = 256 ent + 8 cs
        ent_bits, cs_bits = cand[:256], cand[256:]
        ent = bits_to_bytes(ent_bits)
        if checksum_bits(ent) == cs_bits:
            return WL[idx]
    sys.exit("ERROR: could not find checksum word")

def mnemonic_to_entropy_full(words_any, WL):
    parts = words_any.strip().split()
    if len(parts) not in (12,15,18,21,24): sys.exit("ERROR: expect 12/15/18/21/24 words")
    bits = words_to_bits(parts, WL)
    ent_len = len(parts)*11 - len(parts)*11//33
    ent_bits, cs_bits = bits[:ent_len], bits[ent_len:]
    ent = bits_to_bytes(ent_bits)
    if checksum_bits(ent) != cs_bits: sys.exit("ERROR: mnemonic checksum invalid")
    return ent

def entropy_to_mnemonic(entropy, WL):
    allbits = bytes_to_bits(entropy) + checksum_bits(entropy)
    out=[]
    for i in range(0, len(allbits), 11):
        out.append(WL[int(allbits[i:i+11],2)])
    return " ".join(out)

# secp256k1 (pure)
p  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
a  = 0; b  = 7
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
n  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
INF=None
def inv_mod(x,m): return pow(x, m-2, m)
def add(P,Q):
    if P is INF: return Q
    if Q is INF: return P
    x1,y1=P; x2,y2=Q
    if x1==x2:
        if (y1+y2)%p==0: return INF
        return dbl(P)
    s=((y2-y1)*inv_mod((x2-x1)%p,p))%p
    xr=(s*s-x1-x2)%p; yr=(s*(x1-xr)-y1)%p
    return (xr,yr)
def dbl(P):
    if P is INF: return INF
    x1,y1=P
    if y1==0: return INF
    s=((3*x1*x1 + a)*inv_mod((2*y1)%p,p))%p
    xr=(s*s-2*x1)%p; yr=(s*(x1-xr)-y1)%p
    return (xr,yr)
def mul(k,P):
    if k % n == 0 or P is INF: return INF
    if k < 0: return mul(-k,(P[0],(-P[1])%p))
    R=INF; Q=P
    while k:
        if k & 1: R=add(R,Q)
        Q=dbl(Q); k >>= 1
    return R
def priv_to_pubc(priv32: bytes) -> bytes:
    d = int.from_bytes(priv32, 'big')
    if not (1 <= d < n): sys.exit("ERROR: private scalar out of range (1..n-1)")
    x,y = mul(d,(Gx,Gy))
    return (b'\x02' if (y%2==0) else b'\x03') + x.to_bytes(32,'big')

def hash160(b:bytes)->bytes: return hashlib.new('ripemd160', hashlib.sha256(b).digest()).digest()
BASE58="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def base58check(payload:bytes)->str:
    chk = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    full = payload + chk
    num = int.from_bytes(full,'big')
    s=[]
    while num: num,r=divmod(num,58); s.append(BASE58[r])
    n_pad = len(full) - len(full.lstrip(b'\x00'))
    return '1'*n_pad + ''.join(reversed(s or ['1']))
CHAR="qpzry9x8gf2tvdw0s3jn54khce6mua7l"
def _poly(vals):
    G=[0x3b6a57b2,0x26508e6d,0x1ea119fa,0x3d4233dd,0x2a1462b3]; chk=1
    for v in vals:
        top=chk>>25; chk=((chk&0x1ffffff)<<5)^v
        for i in range(5):
            if (top>>i)&1: chk^=G[i]
    return chk
def _exp(hrp): return [ord(x)>>5 for x in hrp] + [0] + [ord(x)&31 for x in hrp]
def _cs(hrp,data):
    pm=_poly(_exp(hrp)+data+[0,0,0,0,0,0]) ^ 1
    return [(pm >> 5*(5-i)) & 31 for i in range(6)]
def bech32_encode(hrp, data): return hrp + '1' + ''.join(CHAR[d] for d in data + _cs(hrp,data))
def convertbits(data, frombits, tobits, pad=True):
    acc=0; bits=0; ret=[]; maxv=(1<<tobits)-1
    for b in data:
        acc=(acc<<frombits)|b; bits+=frombits
        while bits>=tobits:
            bits-=tobits; ret.append((acc>>bits)&maxv)
    if pad and bits: ret.append((acc<<(tobits-bits))&maxv)
    elif not pad and (bits>=frombits or ((acc<<(tobits-bits))&maxv)): return None
    return ret

def addr_bech32_main(pubc: bytes) -> str:
    prog = hash160(pubc)
    return bech32_encode("bc", [0] + convertbits(prog,8,5))
def addr_p2pkh_main(pubc: bytes) -> str:
    return base58check(b'\x00' + hash160(pubc))
def wif_main(priv32: bytes) -> str:
    return base58check(b'\x80' + priv32 + b'\x01')
def wif_regtest(priv32: bytes) -> str:
    return base58check(b'\xEF' + priv32 + b'\x01')
def addr_p2pkh_regtest(pubc: bytes) -> str:
    return base58check(b'\x6f' + hash160(pubc))

def format_hex(h: str, group: int, upper: bool) -> str:
    h = h.upper() if upper else h.lower()
    return ' '.join(h[i:i+group] for i in range(0, len(h), group))
def hex_grid(priv_hex: str) -> str:
    chunks = [priv_hex[i:i+4] for i in range(0, 64, 4)]
    rows = []
    for i in range(8): rows.append(f"{i+1}: " + " ".join(chunks[i*4:(i+1)*4]))
    return "\n".join(rows)

def parse_args():
    ap = argparse.ArgumentParser(description="Cold Brew (Small) — 23/24 words OR 64-hex → mainnet outputs")
    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument("--words23", help="23 BIP-39 English words in quotes")
    g.add_argument("--words", help="24 BIP-39 English words in quotes (checksum verified)")
    g.add_argument("--hex", help="64 hex chars (32-byte private key)")
    ap.add_argument("--no-stdout-secrets", action="store_true", default=True,
                    help="Do NOT print mnemonic/private hex to terminal (default ON)")
    ap.add_argument("--print-secrets", action="store_true", help="Override and print secrets to stdout")
    ap.add_argument("--no-regtest-helpers", action="store_true", help="Omit regtest WIF/address from outputs")
    ap.add_argument("--hex-group", type=int, default=8, choices=(2,4,8,16,32), help="Hex grouping (chars)")
    ap.add_argument("--hex-grid", action="store_true", help="Also print 8x4 hex grid in SECRET file")
    ap.add_argument("--outdir", help="Override timestamp folder")
    return ap.parse_args()

def main():
    WL, wl_hash = verify_wordlist()
    args = parse_args()

    # Determine entropy from inputs
    entropy = None
    if args.words23:
        w23 = args.words23.strip().split()
        if len(w23) != 23: sys.exit(f"ERROR: got {len(w23)} words (need 23)")
        w24 = find_24th_word(w23, WL)
        mnemonic = " ".join(w23 + [w24])
        entropy = mnemonic_to_entropy_full(mnemonic, WL)
    elif args.words:
        w = args.words.strip().split()
        if len(w) != 24: sys.exit(f"ERROR: got {len(w)} words (need 24)")
        mnemonic = " ".join(w)
        entropy = mnemonic_to_entropy_full(mnemonic, WL)
    elif args.hex:
        hx = args.hex.strip().lower()
        if len(hx) != 64 or any(c not in "0123456789abcdef" for c in hx): sys.exit("ERROR: --hex must be 64 hex chars")
        entropy = bytes.fromhex(hx)
        mnemonic = entropy_to_mnemonic(entropy, WL)
    else:
        # interactive: prefer 23 words; allow blank to abort
        print("Enter 23 or 24 BIP-39 English words (blank to abort):")
        s = input("> ").strip()
        if not s: sys.exit("aborted")
        parts = s.split()
        if len(parts) == 23:
            w24 = find_24th_word(parts, WL)
            mnemonic = " ".join(parts + [w24])
            entropy = mnemonic_to_entropy_full(mnemonic, WL)
        elif len(parts) == 24:
            mnemonic = " ".join(parts)
            entropy = mnemonic_to_entropy_full(mnemonic, WL)
        else:
            sys.exit(f"ERROR: got {len(parts)} words (need 23 or 24)")

    # If hex also provided, assert match
    if args.hex:
        if entropy != bytes.fromhex(args.hex.strip().lower()):
            sys.exit("ERROR: provided --hex does not match words-derived entropy")

    # Round-trip sanity
    ent2 = mnemonic_to_entropy_full(mnemonic, WL)
    if ent2 != entropy: sys.exit("ERROR: round-trip mnemonic!=entropy")

    # Derive
    priv_hex = entropy.hex()
    pubc = priv_to_pubc(entropy)
    pubc_hex = pubc.hex()
    bc1 = addr_bech32_main(pubc)
    p2pkh = addr_p2pkh_main(pubc)
    wif_m = wif_main(entropy)
    wif_rt = wif_regtest(entropy)
    p2pkh_rt = addr_p2pkh_regtest(pubc)

    # Run dir
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    runid = sha256_hex(entropy)[:8].upper()
    run_dir = args.outdir or os.path.join(os.path.dirname(__file__), "..", "out", f"{ts}_RUN{runid}")
    os.makedirs(run_dir, exist_ok=True)

    print("\n=== COLD BREW (SMALL) ===")
    print(f"Run dir: {run_dir}")
    print(f"Script SHA256: {self_hash()}")
    WL_SHA = sha256_file(WORDLIST_PATH)
    print(f"Wordlist SHA256: {WL_SHA}")
    print("MAINNET Address (bc1):", bc1)
    print("MAINNET Legacy (P2PKH):", p2pkh)
    print("PUBKEY (compressed hex):", pubc_hex)
    if args.print_secrets and not args.no_stdout_secrets:
        print("\n*** SECRETS (printing because --print-secrets) ***")
        print("Mnemonic (24):", mnemonic)
        print("Private HEX:", priv_hex)
    else:
        print("\n(secrets written to SECRET_DO_NOT_EXPORT.txt; not printed)")

    public_txt = f"""# PUBLIC EXPORT (safe to copy)
# Run: {ts}  ID:{runid}
# Purpose: share/QR these; contains no private key.

MAINNET
- Bech32 P2WPKH (bc1): {bc1}
- Legacy P2PKH      : {p2pkh}
- Compressed pubkey : {pubc_hex}
- Pubkey (group g{args.hex_group:02d}): {format_hex(pubc_hex, args.hex_group, False)}

QR payloads
- Address: {bc1}
- Pubkey : {pubc_hex}

# To monitor deposits on a Core node WITHOUT keys (watch-only):
# bitcoin-cli createwallet "watchonly" true
# bitcoin-cli -rpcwallet=watchonly importaddress "{bc1}" "" false
"""
    secret_txt = f"""### SECRET — DO NOT EXPORT / COPY / PHOTOGRAPH / NETWORK
Run: {ts}  ID:{runid}

*** MINIMUM ESSENTIALS TO RECOVER FUNDS ***
EITHER the 24 BIP-39 words (English, exact order)
OR the 32-byte private key (64 hex chars)
These two represent the SAME key.

Mnemonic (encodes RAW 32-byte private key; NOT PBKDF2 seed)
{mnemonic}

Private key (hex, 32 bytes)
raw : {priv_hex}
g{args.hex_group:02d}: {format_hex(priv_hex, args.hex_group, False)}
"""
    if args.hex_grid:
        secret_txt += "\n8x4 HEX GRID (private key)\n" + hex_grid(priv_hex) + "\n"

    secret_txt += f"""
Compressed public key (hex, 33 bytes)
raw : {pubc_hex}
g{args.hex_group:02d}: {format_hex(pubc_hex, args.hex_group, False)}

Addresses (MAINNET)
- bech32 P2WPKH: {bc1}
- legacy P2PKH : {p2pkh}
- WIF (mainnet, compressed): {wif_m}
"""

    if not args.no_regtest_helpers:
        secret_txt += f"""
Regtest helpers (for local verification ONLY)
- WIF (regtest)   : {wif_rt}
- P2PKH (regtest) : {p2pkh_rt}
"""

    pub_path  = os.path.join(run_dir, "PUBLIC_EXPORT.txt")
    sec_path  = os.path.join(run_dir, "SECRET_DO_NOT_EXPORT.txt")
    hint_path = os.path.join(run_dir, "regtest_expected.json")
    qr_dir    = os.path.join(run_dir, "qr")
    os.makedirs(qr_dir, exist_ok=True)

    pub_sha  = write_text(pub_path, public_txt)
    sec_sha  = write_text(sec_path, secret_txt); os.chmod(sec_path, 0o600)

    regtest_json = {"regtest_wif": wif_rt, "regtest_p2pkh": p2pkh_rt,
                    "note": "Contains test WIF. Treat as SECRET. Pass to regtest_check.sh if desired."}
    hint_sha = write_text(hint_path, json.dumps(regtest_json, indent=2))

    write_text(os.path.join(qr_dir, "bc1.txt"), bc1 + "\n")
    write_text(os.path.join(qr_dir, "pubkey.txt"), pubc_hex + "\n")

    manifest_lines = [
        f"{sha256_file(pub_path)}  PUBLIC_EXPORT.txt",
        f"{sha256_file(sec_path)}  SECRET_DO_NOT_EXPORT.txt",
        f"{sha256_file(hint_path)}  regtest_expected.json",
        f"{self_hash()}  SCRIPTS/coldgen.py",
        f"{WL_SHA}  wordlist.txt",
    ]
    man_path = os.path.join(run_dir, "MANIFEST.SHA256")
    man_sha = write_text(man_path, "\n".join(manifest_lines) + "\n")

    print(f"\nWrote: {pub_path}   (sha256 {pub_sha})")
    print(f"Wrote: {sec_path}   (sha256 {sec_sha})")
    print(f"Wrote: {hint_path}  (sha256 {hint_sha})")
    print(f"Wrote: {man_path}   (sha256 {man_sha})")
    print("\nDone.")

if __name__ == "__main__":
    main()
