#!/usr/bin/env python3
# verify_consistency.py — prove mnemonic(24) <-> 32-byte hex produce SAME priv/pub (pure Python)
import sys, argparse, hashlib, os

WORDLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "wordlist.txt")

p  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
a  = 0; b  = 7
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
n  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
INF=None
def inv_mod(x,m): return pow(x,m-2,m)
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
    s=((3*x1*x1+a)*inv_mod((2*y1)%p,p))%p
    xr=(s*s-2*x1)%p; yr=(s*(x1-xr)-y1)%p
    return (xr,yr)
def mul(k,P):
    if k% n==0 or P is INF: return INF
    if k<0: return mul(-k,(P[0],(-P[1])%p))
    R=INF; Q=P
    while k:
        if k&1: R=add(R,Q)
        Q=dbl(Q); k>>=1
    return R
def priv_to_pubc(dbytes: bytes)->bytes:
    d=int.from_bytes(dbytes,'big')
    if not (1<=d<n): sys.exit("private scalar out of range")
    x,y=mul(d,(Gx,Gy))
    return (b'\x02' if (y%2==0) else b'\x03') + x.to_bytes(32,'big')

def load_words():
    with open(WORDLIST_PATH,"r",encoding="utf-8") as f:
        wl=[w.strip() for w in f if w.strip()]
    if len(wl)!=2048: sys.exit("wordlist must have 2048 words")
    return wl
def bytes_to_bits(b): return ''.join(f"{x:08b}" for x in b)
def bits_to_bytes(bs):
    assert len(bs)%8==0
    return bytes(int(bs[i:i+8],2) for i in range(0,len(bs),8))
def checksum_bits(ent):
    return bytes_to_bits(hashlib.sha256(ent).digest())[:len(ent)*8//32]
def mnemonic_to_entropy(mn, wl):
    parts=mn.strip().split()
    if len(parts) not in (12,15,18,21,24): sys.exit("expect 12/15/18/21/24 words")
    bits=""
    for w in parts:
        try: idx=wl.index(w)
        except ValueError: sys.exit(f"bad word: {w}")
        bits+=f"{idx:011b}"
    ent_len=len(parts)*11 - len(parts)*11//33
    ent_bits=bits[:ent_len]; cs_bits=bits[ent_len:]
    ent=bits_to_bytes(ent_bits)
    if checksum_bits(ent)!=cs_bits: sys.exit("mnemonic checksum invalid")
    return ent

ap=argparse.ArgumentParser(description="Verify mnemonic and/or 64-hex yield same key/pubkey")
ap.add_argument("--mnemonic", help="24 words")
ap.add_argument("--hex", help="64 hex chars")
args=ap.parse_args()

wl=load_words()
priv_from_mn=None; priv_from_hex=None

if args.mnemonic:
    e=mnemonic_to_entropy(args.mnemonic, wl)
    if len(e)!=32: print("ERR: not 32-byte entropy for 24 words"); sys.exit(2)
    priv_from_mn=e
if args.hex:
    h=args.hex.strip().lower()
    if len(h)!=64 or any(c not in "0123456789abcdef" for c in h):
        print("ERR: --hex must be 64 hex chars"); sys.exit(2)
    priv_from_hex=bytes.fromhex(h)

if not args.mnemonic and not args.hex:
    print("Provide --mnemonic and/or --hex"); sys.exit(2)

if priv_from_mn and priv_from_hex and priv_from_mn!=priv_from_hex:
    print("FAIL: mnemonic-derived private != hex private"); sys.exit(1)

priv = priv_from_mn or priv_from_hex
pubc = priv_to_pubc(priv)
print("OK")
print("PRIVATE_HEX:", priv.hex())
print("PUBKEY_COMPRESSED_HEX:", pubc.hex())
sys.exit(0)
