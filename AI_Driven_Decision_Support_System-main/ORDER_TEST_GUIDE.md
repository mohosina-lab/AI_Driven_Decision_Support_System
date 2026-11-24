# Test guide — 20 fictional orders

Use the Sales simulator with the saved default change and pricing approach for each order. Affect the full order. Quantity increase defaults to ten added cabinets. Margin starts at 20%; maximum additional price allowance is €50,000. All results assume unchanged seed data.

## Find an example

| Order | Quantity | Assembled | What to test |
| --- | ---: | ---: | --- |
| ORD-001 | 50 | 30 | Accept the new request. Default revised plan takes 29 days within 30 days available. |
| ORD-002 | 50 | 30 | Accept with a changed delivery date. The default plan needs 9 extra working days. |
| ORD-003 | 50 | 30 | Do not accept under the current deadline. The default plan needs 9 extra working days. |
| ORD-004 | 50 | 0 | Before-assembly comparison. No already-assembled units require rework. |
| ORD-005 | 50 | 30 | Do not accept. Forty additional communication modules are unavailable and replenishment is not possible in this scenario. |
| ORD-006 | 50 | 45 | Late-stage change with limited Production capacity. Explore the extra rework and the revised date. |
| ORD-007 | 20 | 0 | Small order before assembly; absorb change cost while meeting minimum margin. |
| ORD-008 | 80 | 40 | Large order with higher daily capacity; new price but original date. |
| ORD-009 | 12 | 12 | All original cabinets assembled; component replacement creates rework and repeat testing. |
| ORD-010 | 40 | 20 | Date extension with original total price; compare profit before and after. |
| ORD-011 | 60 | 45 | Later delivery and higher price for a predefined protection upgrade. |
| ORD-012 | 25 | 10 | Fixed short deadline; requested layout change does not fit. |
| ORD-013 | 30 | 10 | Sensor shortage with known replenishment time shifts the schedule. |
| ORD-014 | 15 | 5 | Replacement part shortage cannot be replenished. |
| ORD-015 | 35 | 20 | No testing capacity allocated; additional connection cannot be scheduled. |
| ORD-016 | 45 | 15 | Sensor shortage with unknown replenishment time; needs information. |
| ORD-017 | 100 | 25 | Quantity increase; add ten base cabinets and maintain original margin percentage. |
| ORD-018 | 10 | 8 | Only sensors and quantity increases supported; other technical scopes should fail. |
| ORD-019 | 24 | 12 | Matching saved custom assessment for additional identification labels. |
| ORD-020 | 18 | 3 | Other change has no saved assessment; shows assessment needed. |

## Expected default results

| Order | Default request | Expected recommendation / state | Proposed total price |
| --- | --- | --- | ---: |
| ORD-001 | Additional sensors and remote monitoring | Accept with a new price | €110,012.50 |
| ORD-002 | Additional sensors and remote monitoring | Accept with a new price and delivery date | €110,012.50 |
| ORD-003 | Additional sensors and remote monitoring | Do not accept the new request | €110,012.50 |
| ORD-004 | Additional sensors and remote monitoring | Accept with a new price | €108,812.50 |
| ORD-005 | Additional sensors and remote monitoring | Do not accept the new request | €110,012.50 |
| ORD-006 | Additional sensors and remote monitoring | Accept with a new price and delivery date | €110,612.50 |
| ORD-007 | Add sensors | Accept without changes to price or delivery date | €40,000.00 |
| ORD-008 | Add remote monitoring | Accept with a new price | €200,400.00 |
| ORD-009 | Replace a component | Accept with a new price | €36,098.00 |
| ORD-010 | Add sensors | Accept with a new delivery date | €80,000.00 |
| ORD-011 | Change the protection requirements | Accept with a new price and delivery date | €150,140.00 |
| ORD-012 | Change cabinet size or layout | Do not accept the new request | €59,375.00 |
| ORD-013 | Add sensors | Accept with a new price | €63,225.00 |
| ORD-014 | Replace a component | Do not accept the new request | €32,597.50 |
| ORD-015 | Add another machine connection | Do not accept the new request | €74,447.50 |
| ORD-016 | Add sensors | Information needed: sensor replenishment lead time | Not calculated |
| ORD-017 | Increase the order quantity | Accept with a new price | €242,000.00 |
| ORD-018 | Add sensors | Accept with a new price | €21,435.00 |
| ORD-019 | Other changes | Accept with a new price | €48,570.00 |
| ORD-020 | Other changes | Production assessment needed | Not calculated |

## Four useful comparisons

1. Load ORD-007: the default sensor change is absorbed at the original total price and still meets the margin rule.
2. Load ORD-010: the same original-price policy needs a later date. Compare it with ORD-011, which needs a new price and date.
3. Load ORD-018: evaluate Add sensors first, then select Change the protection requirements. Only the first is supported for that order.
4. Compare ORD-019 and ORD-020 using Other changes. ORD-019 has a matching saved assessment; ORD-020 needs one. Changing the custom description or quantities requires a new assessment.

## Earlier delivery

Select ORD-009, then Request earlier delivery. Try a weekday after the simulation start and before original delivery. The original cabinets are already assembled and normal testing is finished. Then try ORD-012 with a very short earlier date: remaining work and the queue prevent meeting it. Earlier requests never allow a later-date extension.

## Preserve the meaning of each test

ORD-016 is intentionally incomplete. Enter a known sensor replenishment lead time and save Production data to see how the result changes. Unknown does not mean zero. ORD-015 needs testing capacity before its additional connection can be scheduled. These are test conditions, not defects in the app.

Each record has its own reserved daily capacity and assumed stock. The app does not schedule all 20 orders together or calculate one order displacing another. Every customer and value is fictional.

## Version 7.4: simpler order selection

Choose ORD-001 through ORD-020 in the Order number dropdown. The previous introductory instruction line and Find an order or test scenario section have been removed. Selecting another order loads its saved Production data and default request settings. Existing calculations and validation rules remain the same.
