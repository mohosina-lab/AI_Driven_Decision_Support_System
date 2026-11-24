# Northstar Cabinets — Sales and Production Simulator, Version 7.4

A fictional manufacturer of industrial electrical control cabinets. Sales selects an order and a customer request. The app loads saved Production facts and calculates a proposed price, estimated profit, schedule and recommendation. All data and policy values are synthetic assumptions, not validated manufacturing estimates.

## Start on Windows — no API key needed

1. Stop the old app: click its running terminal and press **Ctrl+C**.
2. Download and extract the entire Version 7.4 ZIP into a **new folder**.
3. In VS Code, choose File → Open Folder. Select the extracted folder containing `app.py`, `decision.py` and `Run_Simulator.bat`.
4. Choose Terminal → New Terminal. Enter:

```powershell
.\Run_Simulator.bat
```

The launcher uses `py` to create a new environment and install Streamlit. Python must be installed. Internet is needed for initial package installation. Keep the terminal open and open the Local URL it prints if the browser does not open automatically.

You can also double-click `Run_Simulator.bat` in Windows File Explorer. If setup fails, keep the error visible for troubleshooting. The launcher must be run, rather than opened as text in the editor.

Extract into a new folder so the new seed data is used. Do not copy an old version's `production.sqlite` or `venv` into this release. The new catalogue requires additional component stock records. Your old folder retains its previous saved edits.

## Requests included

| Request | How this prototype handles it |
| --- | --- |
| Add sensors | Saved extra parts, installation, rework and testing per affected cabinet |
| Add remote monitoring | Saved communication equipment and work estimates |
| Add sensors and remote monitoring | Keeps the existing combined example |
| Replace a component | One predefined compatible Component A → B example, with removal/rework allowance and no salvage credit |
| Change cabinet size or layout | One predefined larger-enclosure/layout example; assembled cabinets require extra rebuilding work |
| Add another machine connection | One predefined supported connection, terminals and wiring |
| Change the protection requirements | One predefined upgrade kit and testing allowance; no safety or regulatory certification is performed |
| Increase the order quantity | Enter the additional quantity. Adds original-configuration cabinets and their complete base costs, normal assembly and 0.5 testing hour each |
| Request earlier delivery | Enter an earlier weekday. Checks the original remaining work against it, with unchanged reserved capacity and no assumed overtime |
| Other changes | Requires a matching saved Production assessment; otherwise displays Assessment needed |

One request type is evaluated at a time. The predefined product examples do not cover arbitrary components, dimensions, machine interfaces or protection ratings. Different technical specifications require a separate assessment.

## Five Sales recommendations

1. Accept without changes to price or delivery date.
2. Accept with a new price.
3. Accept with a new delivery date.
4. Accept with a new price and delivery date.
5. Do not accept the new request.

The recommendation depends on technical support, materials, reserved capacity, customer price/date flexibility and a fictional minimum profit margin. Price and date changes require customer agreement. A pending assessment is not one of the five decisions; it means information is missing.

## How prices and profit work

Select an approach:

- **Keep original order price:** keep the original TOTAL price, even if quantity increases. Sales must review whether that is sensible.
- **Recover additional cost:** add modelled incremental costs to the original price. This preserves original euro profit, not original margin percentage.
- **Maintain original profit margin:** new total cost ÷ (1 − original margin fraction). Rounded up to cents.
- **Enter negotiated total price:** evaluate a total entered by Sales.

Minimum margin initially equals **20%**, an editable demo company rule, not an industry standard. A proposed price below the minimum margin or outside customer price flexibility leads to Do not accept under the current inputs. The app shows the minimum total price that would meet the selected margin, so Sales can adjust the proposal and rerun it.

New total cost = original total cost + incremental cost.
Estimated profit = proposed total selling price − new total cost.
Profit change = new estimated profit − original estimated profit.
Average price per cabinet = proposed total price ÷ new total quantity.

A fall in profit does not necessarily mean a loss. Prices exclude tax. Profit means profit from included costs; overheads not in the unit costs, taxes, penalties, salvage and effects on other orders are not added.

### Quantity increase — avoid double-counting

Additional cabinets use the order's complete unit base cost (initially €1,200) once. This includes labour and materials. The model separates that cost into normal assembly labour, 0.5 hour testing labour and residual material-set cost. It checks stock as complete base-cabinet material sets. It never adds the full base cost and the same labour twice.

At 4 assembly hours × €40 and 0.5 testing hour × €35, the residual material set is €1,022.50. Ten additional cabinets cost €12,000 in total. No new sensor/remote upgrade is combined with those cabinets in the same request.

## Production and Other changes

In the sidebar, open Production dashboard. Edit an order's facts and component stock, then Save Production data. Each save increments its data revision. Sales loads the updated version when selecting the order or refreshing the page. There is no background push update across browser sessions.

To assess an Other change:

1. In Production dashboard, select the order.
2. Scroll to Assessment for an Other change.
3. Enter an exact description, affected quantity and affected already-assembled quantity.
4. Select technical feasibility. Enter TOTAL extra setup, installation, rework and testing hours, total materials cost and the complete parts wait after setup.
5. Tick the review confirmation and Save Production data.
6. Return to Sales, select the same order and Other changes. The saved description loads when the new revision is loaded. Use the matching quantities, then Evaluate.

Your team acts as Production and enters explicit synthetic assumptions for the exercise. Nothing is sent to another person. Custom stock/feasibility is represented by Production's aggregate assessment; materials are not individually deducted. Only one current custom assessment is stored per order. A changed request description, affected quantities or Production snapshot requires a fresh assessment. Any new Production save requires the review box to be reconfirmed to keep that custom assessment complete.

## Schedule assumptions and limits

- Simulation start date is the date of the Production snapshot. Seed date is 19 November 2026; it does not automatically become today's date. Review dates and progress together before saving.
- Normal assembly remaining = (order quantity − assembled quantity) × normal hours/cabinet.
- Rework applies only to affected already-assembled cabinets.
- Daily capacities are person-hours reserved for the selected order AFTER other commitments. Do not reduce them again by an unrelated workload percentage.
- Queue, setup, parts wait, assembly, testing and dispatch are sequential. This is conservative: original remaining work waits during setup and additional parts readiness.
- Work phases round up to whole days. Dates skip weekends; public holidays are not modelled.
- Additional stock shortages use the longest replenishment wait after setup. Original-order materials are assumed ready.
- Orders and inventory are assessed independently. Scenarios do not consume stock, allocate people or move other orders. No company-wide scheduling, order-expediting priority or displaced-job cost is calculated.
- No ERP/Odoo connection, production authorisation, real safety verification or generative AI is included. Explanations are based on the visible calculations. No API key is needed.
- Running a simulation never changes an actual order. Only Save Production data updates the local fictional database.

## Files and validation

`app.py` is the interface, `decision.py` handles expanded requests and commercial decisions, `model.py` provides core workload/cost/schedule calculation, and `repository.py` stores Production records with revision conflict protection. JSON files in `data` seed a new database. `START_HERE.md` is a simple demonstration guide.

From the project directory after installing requirements:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -q
```

Tests cover calculation rules, five decisions, costs, quantity changes, earlier dates, pending/stale custom assessments, database revision checks and Streamlit interactions. The Windows launcher requires a Windows machine for execution.

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
