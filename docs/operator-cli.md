# Operator Playbook — Dogecoin Wallet for the Gumball Machine (CLI)

Everything you need to set up the dedicated `doge-gumball` wallet using the
Dogecoin Core **CLI** (first time moving off the GUI — this is the same
underlying node, just driven from the terminal).

All commands assume Dogecoin Core is installed on Linux and the data dir is
the default `~/.dogecoin/`.

---

## 0. One-time: enable the RPC server (so `dogecoin-cli` can talk to the node)

`dogecoin-cli` needs the node to expose its JSON-RPC interface.

**If you run the GUI (`dogecoin-qt`)** — it's what's been syncing:
1. Open `Settings > Options > Main tab`
2. Tick **"Enable RPC server"**
3. Click OK and **restart** the wallet.

**If you prefer headless** (stop the GUI first, then):
```bash
dogecoind -daemon -server=1
```
(It shares the same `~/.dogecoin/` data dir, so your sync progress carries over.)

Either way, Core now writes a cookie file at `~/.dogecoin/.cookie`, and
`dogecoin-cli` authenticates with it automatically — no username/password to
create or store.

## 1. Verify the node is up and check sync

```bash
dogecoin-cli getblockchaininfo
```
Look at:
- `verificationprogress` — `1.0` = fully synced (keep syncing in the background;
  **not required** for receiving or for the machine to verify payments)
- `blocks` vs `headers` — when equal (and progress ≈ 1.0) you're caught up

## 2. Create the dedicated wallet (one wallet file, just for this project)

```bash
dogecoin-cli createwallet "doge-gumball"
```
Expected output: `{"name": "doge-gumball", "warning": "..."}`

(If it says the wallet already exists — e.g. you created it before —
just load it: `dogecoin-cli loadwallet "doge-gumball"`)

## 3. Generate the machine's receiving address

```bash
dogecoin-cli -rpcwallet=doge-gumball getnewaddress "gumball-machine"
```
This prints the address (starts with `D`). The label `gumball-machine` is
just for your bookkeeping inside Core.

## 4. Validate the address before wiring it up

```bash
dogecoin-cli -rpcwallet=doge-gumball validateaddress <THE_ADDRESS>
```
You want `"isvalid": true`. (Also note the `address` field — that's the one
to use.)

## 5. Plug it into the Space (two options — pick one)

**A. Web UI (simplest):**
1. https://huggingface.co/spaces/jkorstad/doge-gumball/settings
2. Scroll to **Repository secrets** → **New secret**
3. Key: `DOGE_ADDRESS` · Value: `<THE_ADDRESS>`
4. Save → the Space auto-restarts with the secret.

**B. CLI (if you prefer):**
```bash
curl -X POST "https://huggingface.co/api/spaces/jkorstad/doge-gumball/secrets" \
  -H "Authorization: Bearer $HF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key":"DOGE_ADDRESS","value":"<THE_ADDRESS>"}'
```
Then restart the Space:
```bash
curl -X POST "https://huggingface.co/api/spaces/jkorstad/doge-gumball/restart" \
  -H "Authorization: Bearer $HF_TOKEN"
```

**Verify it took:** open the Space's UI — the address box should now show
your real `D...` address and the badge should read LIVE/open. Or:
```bash
curl -s https://jkorstad-doge-gumball.hf.space/gumball/machine
```
Look for `"open": true`.

## 6. Send a real test payment (1 DOGE, blind)

From a **second wallet** (an exchange, a phone wallet, or a second Core
wallet) send exactly 1 DOGE to the machine address. If you want to test
from Core itself, first create/load a second wallet with funds:
```bash
dogecoin-cli createwallet "personal"          # if you don't have one yet
dogecoin-cli -rpcwallet=personal sendtoaddress <THE_ADDRESS> 1.0 "gumball test"
```
`sendtoaddress` prints the **txid** — that's your tx hash. Save it.

(If the wallet isn't loaded: `dogecoin-cli loadwallet "personal"`)

## 7. Watch it confirm, then redeem

```bash
dogecoin-cli gettransaction <TXID>
```
Wait until `"confirmations": 1`. Then paste the TXID into the machine UI
(or POST it):
```bash
curl -s -X POST "https://jkorstad-doge-gumball.hf.space/gumball/dispense" \
  -H "Content-Type: application/json" \
  -d '{"tx_hash":"<TXID>"}'
```
A real gumball pops. Your receipt id comes back in the response.

## 8. Day-to-day operator checks

```bash
dogecoin-cli -rpcwallet=doge-gumball getbalance                 # machine's balance
dogecoin-cli -rpcwallet=doge-gumball listunspent                # individual receipts
dogecoin-cli -rpcwallet=doge-gumball getreceivedbyaddress <THE_ADDRESS>
dogecoin-cli getblockchaininfo | grep -E "blocks|verificationprogress"
```

## 9. Moving collected doge out (only once synced)

```bash
dogecoin-cli -rpcwallet=doge-gumball sendtoaddress <YOUR_EXCHANGE_OR_COLD_ADDRESS> <AMOUNT> "gumball sweep"
```
> ⚠️ Only send from a wallet whose node is fully synced (`verificationprogress` ≈ 1.0),
> or Core may refuse/queue the tx. Keep the wallet.dat backed up offline — it
> holds the keys to every gumball ever sold.

---

## Security notes

- Only the **address** ever goes into the HF Space. Private keys stay in
  `~/.dogecoin/` — never upload wallet.dat anywhere.
- The machine address is public by design (it's on the site). Anyone can
  pay it; the tx-hash ledger guarantees one gumball per payment.
- Back up `~/.dogecoin/wallets/doge-gumball/wallet.dat` after creating it
  and after any large balance change.
