# OpenSea NFT Launch Playbook (Noble Port)

This playbook turns Noble Port branding/content into a launch-ready OpenSea collection and first NFT drop.

## 1) Prerequisites

- Wallet with enough ETH for gas (if using Ethereum mainnet) or enough native gas token on your chosen chain.
- Access to the official Noble Port social accounts and website.
- Final artwork and metadata for the first NFT.
- A secure private key workflow (hardware wallet strongly recommended).

## 2) Decide Launch Chain

OpenSea supports multiple networks. For fastest go-live and lower fees, teams often use **Base** or **Polygon**; for highest collector liquidity, many choose **Ethereum mainnet**.

Suggested default for first launch:
- **Primary launch:** Base
- **Future premium/1-of-1:** Ethereum mainnet

## 3) Collection Setup on OpenSea

1. Go to OpenSea and connect the project wallet.
2. Create a new collection named `Noble Port`.
3. Use a clear description focused on tokenized real estate + on-chain transparency.
4. Set project links:
   - Website: `https://nobleport.realty`
   - Docs: `https://docs.nobleport.realty`
   - X/Twitter + Discord
5. Set creator earnings and payout wallet.
6. Add traits/categories that match roadmap (property market, asset type, season, membership tier).

## 4) Minting Strategy

### Option A: OpenSea Studio (no-code)
Use when speed matters and collection size is small.

- Upload artwork directly.
- Add metadata traits in UI.
- Set supply and list price.

### Option B: Smart contract mint
Use for long-term control and custom logic.

- Deploy ERC-721 or ERC-1155 contract.
- Verify contract.
- Import collection into OpenSea.
- Mint via contract functions.

## 5) Starter Metadata Template

Use this JSON as a base for the first item:

```json
{
  "name": "Noble Port Genesis #1",
  "description": "Genesis NFT for Noble Port. Represents early supporter status in the Noble Port ecosystem.",
  "image": "ipfs://<CID>/genesis-1.png",
  "external_url": "https://nobleport.realty",
  "attributes": [
    { "trait_type": "Series", "value": "Genesis" },
    { "trait_type": "Tier", "value": "Founding" },
    { "trait_type": "Network", "value": "Base" },
    { "trait_type": "Utility", "value": "Community Access" }
  ]
}
```

## 6) IPFS Upload

- Pin all assets (image/video + metadata JSON).
- Keep a manifest of CIDs in version control.
- Never mutate metadata after reveal unless contract terms explicitly permit it.

## 7) Launch Sequence (T-48h to T+24h)

### T-48h
- Freeze final art + metadata.
- Dry-run mint from a clean wallet.
- Verify collection links and social handles.

### T-24h
- Publish launch thread.
- Share mint time in UTC and US timezones.
- Set moderation coverage in Discord/X.

### T-0
- Mint/list first NFT.
- Confirm OpenSea page renders image, traits, and links correctly.
- Post direct collection URL on all official channels.

### T+24h
- Share transparent post-launch report:
  - items minted
  - floor/volume snapshot
  - next milestone date

## 8) Security Checklist

- Use hardware wallet for creator account.
- Enable 2FA on all social/admin accounts.
- Verify every URL before signing wallet prompts.
- Keep treasury wallet separate from ops wallet.

## 9) “Definition of Done” for Launch

A launch is complete when all are true:

- Collection is public and branded correctly.
- At least one NFT is minted and visible on OpenSea.
- Metadata, image, and external links resolve correctly.
- Launch announcement is posted from official channels.

## 10) What I can/can’t do from this repo

This repository can store launch assets/checklists, but actual OpenSea minting requires:
- a connected wallet,
- signing transactions,
- and account-level actions on OpenSea.

Use this playbook to execute those actions safely and consistently.
