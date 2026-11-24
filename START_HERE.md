# A simple guide for your team

**Company:** Northstar Cabinets (fictional). **Product:** industrial electrical control cabinets. **Departments:** Sales and Production.

## First demonstration

1. Open Sales simulator from the sidebar.
2. Enter **ORD-001**. Its Production data loads automatically: 50 cabinets ordered, 30 assembled and 20 still to assemble.
3. Select **Add sensors** and affect all 50 cabinets.
4. Leave **Recover additional cost** selected. This keeps the original euro profit.
5. Click **Evaluate customer request**.
6. Read the recommendation, proposed total price, average cabinet price, extra cost and profit.
7. Open Work and schedule to see where the hours came from.

Every value is an assumption in a fictional exercise. Known changes use saved profiles. Their results are immediate, but still require commercial agreement.

## Show all five decisions

Use the combined sensors + remote monitoring profile affecting all 50, with the seeded records:

| Example | Inputs | Expected recommendation |
| --- | --- | --- |
| Keep price and date | ORD-001; Keep original order price; minimum margin 20% | Accept without price or date changes |
| Change price only | ORD-001; Recover additional cost | Accept with a new price |
| Change date only | ORD-002; Keep original order price; allow up to 10 extra days | Accept with a new delivery date |
| Change both | ORD-002; Recover additional cost; allow up to 10 extra days | Accept with a new price and delivery date |
| Reject under the current constraints | ORD-003; original deadline fixed | Do not accept the new request |

If you edit Production records or policy inputs, results can change. New price/date recommendations are proposals pending customer agreement.

## Explain the different requests

- **Add sensors / remote monitoring:** affects existing cabinets, so already-assembled cabinets may need rework.
- **Replace a component / size or layout / machine connection / protection:** uses a specific, fictional technical example. Read the blue explanation before evaluating. It is not a universal estimate for every design.
- **Increase quantity:** add 10 cabinets to ORD-001. The order becomes 60. Added cabinets need assembly, testing, materials and full base cost. Already-assembled original cabinets do not need rework for this request.
- **Earlier delivery:** select a weekday earlier than the original date. The app checks the existing remaining schedule. It does not add workers or delay other orders.
- **Other changes:** enter a description. Without matching saved Production estimates, the result is Production assessment needed. The team can then act as Production, save estimates, and return to Sales to evaluate the matching request.

## Simple meanings

**Capacity:** working hours available for this order per day, not the total hours needed.

**Assembly progress:** cabinets assembled ÷ cabinets ordered. Testing may still remain.

**Simulation start date:** the date from which remaining work is calculated, matching the saved Production snapshot.

**Revision:** version of the saved Production information. Saving creates the next version.

**Margin:** estimated profit as a percentage of total selling price. The initial 20% minimum is a fictional company policy.

**Profit change:** how much more or less estimated profit the proposal makes compared with the original order. Less profit can still be a positive profit.

## Version 7.2: original order date and earlier delivery

Original order date is when the customer placed the order. It now appears in the Production order table, editable Production form and Sales-loaded details. All six seed orders use 1 November 2026 as an explicit fictional example. It must be on or before the simulation start date. The simulation still starts from the Production snapshot date, not the order date.

For Request earlier delivery, later-date flexibility is disabled and zero additional days are allowed. The model enforces this even if an earlier scenario had permitted an extension. If the earlier requested date can be met, acceptance with a new delivery date means the earlier date. If it cannot be met, the request is not accepted and the earliest estimated completion is displayed for discussion. Other request types retain their own flexibility settings.

## Version 7.2 — connected validation rules

This release adopts a fictional no-discount policy: a proposed total order price cannot be below the original total order price. This is a team choice for the prototype, not an industry rule. The negotiated price field has the original total as its minimum; the calculation engine enforces the same rule.

Original price, proposed price and extra charge appear together before evaluation. The proposed price is an offer, not the customer's maximum budget. The customer's maximum additional charge is a separate constraint: it can exceed the proposal, but a proposal above that limit cannot receive an acceptance recommendation.

When no increase is proposed, price-increase controls are unticked, disabled and effectively zero. When a price increase is not permitted, its effective extra-charge limit is zero, even if a previous scenario contained another number. When a later date is not permitted, the effective extra-day limit is zero. Earlier-delivery requests always have a fixed date.

Invalid quantities, dates, prices, non-finite values, negative source costs or missing required lead times cannot produce an acceptance. Essential input errors disable evaluation with an explanation. Valid proposals that exceed customer price/date limits or fail the minimum margin remain evaluable but receive Do not accept, with the conflict explained. Changing inputs hides an old recommendation until a fresh evaluation.

Production can now explicitly mark a replenishment time unknown. Saving does not turn an unknown lead time into zero. If stock is short and replenishment time is unknown, evaluation waits for that information. An unresolvable shortage or zero required capacity blocks acceptance.

See VALIDATION_RULES.md for the cross-field rules checked in this release.

## 20-order expansion — Version 7.3

Order numbers now run from ORD-001 to ORD-020. Northstar Cabinets remains the one manufacturer; all named customers are fictional. The initial six test records are retained. Fourteen added records vary quantity, assembly progress, original order date, delivery deadline, daily capacities, price/cost, queue, dispatch, technical support and component stock/lead times.

Sales has an Order number dropdown containing all 20 order IDs. Selecting a new order loads that example's default change, pricing approach and date flexibility; price allowance and minimum margin reset to demo defaults. Changing those inputs lets you explore other outcomes. ORDER_TEST_GUIDE.md lists each default example and useful manual variations.

The new ZIP starts a fresh dataset in a new folder. Keep the old folder if you need its previous edits. Advanced option for Version 7.2 users: before starting this version, copy ONLY the old data/production.sqlite into the new data folder to retain saved Production edits. The app inserts missing order IDs without overwriting existing records. Do not copy an older version's database or virtual environment. Expected guide results assume unchanged seed records.

All order snapshots use the same fictional simulation start date, 19 November 2026. The records remain independent what-if scenarios, with reserved capacities and stock per order. This expansion does not add shared-resource scheduling across 20 orders.

## Version 7.4: simpler order selection

Choose ORD-001 through ORD-020 in the Order number dropdown. The previous introductory instruction line and Find an order or test scenario section have been removed. Selecting another order loads its saved Production data and default request settings. Existing calculations and validation rules remain the same.
