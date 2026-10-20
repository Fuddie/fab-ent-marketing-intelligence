# Fab ENT Growth Intelligence



## Business context

Fab ENT is a fictional UK direct-to-consumer fashion brand. This portfolio uses a fixed, entirely synthetic dataset, not real customer data. Paid channels are Meta Paid Social, Google Paid Search and TikTok Paid Social; website traffic also includes Direct and Organic.



## Problem

Campaign, website and order data are stored separately, making it difficult for the marketing team to compare spend with attributed orders and evaluate performance consistently.



## Dashboard users

The marketing manager and channel owners will use the dashboard.



## Decisions

* Allocate budget across marketing channels.
* Identify campaigns that are underperforming.
* Compare channel performance using consistent metrics.
* Decide which campaigns to scale, pause or improve.



## Business questions

Which channel has the highest attributed order amount?

Which campaigns produce the strongest ROAS?

Which campaigns spend budget without generating attributed orders?

How do CTR, CPC and conversion rate compare by channel?

How much does it cost to acquire a new customer by channel?

Which campaigns are approaching or exceeding their budgets?



## Attribution rule

Each order is assigned to the customer's most recent non-direct campaign interaction within the seven days before purchase. An order can be attributed to only one campaign. If no qualifying interaction exists, the order remains unattributed.



## Reporting boundaries

Attributed order amount is the recorded value of orders connected to marketing campaigns. It is not net revenue because it does not account for every refund, cancellation, fee, tax, or business cost. Attribution shows that a campaign interaction occurred before an order, but it does not prove that the campaign caused the purchase.



## Success criteria

How will we know the project works correctly?
Dashboard metrics must match independently calculated SQL results.

Joining campaign and order data must not duplicate order amounts.

Every attributed order must follow the seven-day last-touch rule.

The dashboard must answer all six agreed business questions.

Metrics must handle zero clicks, orders, or spend safely.

Wren must produce consistent, read-only answers.

Another person must be able to reproduce the project from its documentation.


## Synthetic source boundaries

The fixed reporting period is 2025-01-01 through 2025-12-31, with GBP amounts, UTC raw timestamps and Europe/London reporting dates. Seven CSV sources include campaign budgets, daily media performance, sessions, customers, orders, order lines and products. See `DATA_DICTIONARY.md` for physical fields, reproducible generation, attribution fixtures and limitations.

Campaigns have one paid channel and one lifetime budget each. Identified paid website sessions supply campaign interactions; Direct and Organic sessions have no campaign IDs. Customer IDs match exactly between orders and known sessions. Raw orders retain cancellations and final full/partial refunds; gross, refund/reversal and net amounts reconcile to order lines. Raw availability does not settle metric status eligibility or redefine attributed order amount as net revenue.

History is limited to 2025, so customer acquisition is first observed rather than confirmed lifetime acquisition. No pre-period lookback or post-period conversion tail is supplied. Attribution demonstrates sequence, not marketing causation.
