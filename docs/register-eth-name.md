# Register a `.eth` Name

Registering a name takes about three minutes in the [ENS App](https://app.ens.domains/). The process uses two wallet transactions with a 60-second wait between them. You need ETH on Ethereum Mainnet for the registration fee and network gas; ENS does not charge an additional transaction fee.

> **At a glance:** request registration (commit) → wait 60 seconds → complete registration.

## Before you start

- Connect an Ethereum-compatible wallet, such as MetaMask, Rainbow, or Coinbase Wallet.
- Fund it with enough Mainnet ETH for the name fee and both transactions' gas.
- Plan to finish in the same browser. The app stores a secret locally after the commit.
- Allow enough time to finish within 24 hours after the commit confirms.

The commit does **not** reserve the name. Another user who completes registration first can still acquire it.

## 1. Configure the registration

Open the [ENS App](https://app.ens.domains/), connect your wallet, and search for the name. If the name is available, choose either a number of years or **Pick by date** to select a specific expiration date. The minimum term is 28 days and there is no maximum.

The flow also offers two optional setup tasks:

- **Use as primary name:** lets ENS-aware applications display `yourname.eth` instead of your `0x` address. See the [ENS primary-name guide](https://support.ens.domains/en/articles/7890756).
- **Create a profile:** add cryptocurrency addresses, social handles, email, custom text records, a decentralized website content hash, and avatar or header images. These records can also be configured later. Choosing **Upload Image** for an avatar makes that avatar record gasless to change later.

Review the selected term, expiration, and estimated price before continuing.

## 2. Approve the commit transaction

Select **Begin**, then approve the request in your wallet. This is a zero-value transaction: it transfers no ETH, but you pay Ethereum network gas. Your wallet shows the precise gas estimate before approval.

The transaction records a concealed commitment so another party cannot copy the visible name from the mempool and register it first. The browser stores a secret that connects this commitment to your registration request.

> **Important:** do not clear the browser cache, change browsers, or speed up/replace the commit transaction before completing registration. Replacing it can leave the ENS App stuck at “Almost there.” If confirmation is slow, wait for the original transaction.

## 3. Wait 60 seconds

After the commit confirms, the ENS App starts a 60-second timer. This delay is part of the anti-front-running design. Keep the registration page open and proceed as soon as the timer completes.

## 4. Complete registration

Select **Complete registration** and approve the second transaction in your wallet. This transaction pays both the registration price and network gas. It commonly confirms in one or two blocks, although network congestion can make it take longer.

When it confirms, the name belongs to the registering wallet and its NFT appears in that wallet. Any primary-name or profile settings selected earlier become active as part of the flow.

## Pricing

Base annual registration prices are:

| Name length | Base price |
| --- | ---: |
| 3 characters | $640/year |
| 4 characters | $160/year |
| 5 or more characters | $5/year |

Fees are paid in ETH on Ethereum Mainnet. Network gas is additional and varies with activity. A name in temporary premium can be registered by paying its displayed premium in addition to the normal fee. See [ENS pricing](https://support.ens.domains/en/articles/12238910) for the complete pricing policy.

## Common questions

### Can I register a name in its grace period?

No. A name in grace period can only be extended by its current registrant.

### Can I register a name in temporary premium?

Yes. Anyone can register it by paying the displayed premium plus the normal registration price and gas.

### Can I register names other than `.eth`?

The ENS App registration flow only registers `.eth` names. Importing a DNS domain into ENS uses a separate process.

### Can I cancel or receive a refund?

No. ENS registrations are not refundable. The name remains associated with the wallet until it is transferred or expires.

### What happens if I do not finish?

The commitment expires 24 hours after it confirms. Start the process again if that window closes.

### Can I transfer the name later?

Yes. Ownership can be transferred at any time. See [Edit the roles on your ENS name](https://support.ens.domains/en/articles/8825632).

## Troubleshooting

For failed transactions, expired commitments, and registrations stuck in progress, see [Fix `.eth` registration errors](https://support.ens.domains/en/articles/13449264).
