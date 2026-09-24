# Connect Stripe to a Lovable project

Lovable's built-in Stripe integration provides a guided path from account creation through a test checkout and production onboarding.

## Prerequisites

- A Lovable **Pro plan or higher**.
- A project using Lovable's built-in backend (**Cloud**).

The built-in payments flow does not support projects connected to an external Supabase instance. Those projects require an advanced Stripe integration instead.

## Set up Stripe

1. In the Lovable editor, open **More → Payments**.
2. Select **Explore payments**. Let Lovable analyze the project and recommend a payment provider, then choose **Stripe**.
3. Enter the email address, name, and country requested to register the Stripe account.
4. Use Lovable chat to create the products and prices needed by the application.
5. Deploy the project before testing; payments do not work in preview mode.
6. Enable Stripe test mode and complete a checkout with card number `4242 4242 4242 4242`, any future expiration date, and any CVC.
7. When the integration is ready for production, return to the Payments tab, claim the Stripe account, and complete onboarding in the Stripe dashboard.

## Choose the appropriate integration

- [Built-in payments](/features/payments) — use this for a Lovable Cloud project on a supported plan.
- [Advanced Stripe integration with Supabase](/integrations/stripe) — use this when the project needs a custom or external Supabase-based integration.

## Production checklist

Before accepting real payments:

- Confirm that test and live Stripe credentials are kept separate.
- Verify each product's name, currency, amount, and billing cadence.
- Exercise successful, declined, and canceled checkout paths on the deployed test environment.
- Confirm that fulfillment or account access depends on verified payment state rather than a browser redirect alone.
- Complete Stripe onboarding and confirm the account can accept payments in the intended country.

