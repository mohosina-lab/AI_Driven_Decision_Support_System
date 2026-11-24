# How connected inputs are checked

All business policies below are explicit assumptions for this fictional prototype.

| Inputs linked together | Behaviour |
| --- | --- |
| Original total and negotiated total | Negotiated total cannot be below original total; input minimum and calculation enforce the same no-discount policy |
| Proposed price and original price | Additional charge is calculated automatically as their difference |
| No proposed price increase | Price-increase checkbox is unticked/disabled; effective additional-charge limit is zero |
| Price-increase permission and proposed increase | No acceptance if the proposal requires an increase the customer has not allowed |
| Additional charge and customer maximum | Exact limit is allowed; above it prevents acceptance; the limit is a budget, not the proposed price |
| New cost, price and minimum margin | Below minimum margin prevents acceptance even when the proposed price meets the original-price floor |
| Later-date permission and extra days | No permission means zero effective extra days; stale saved values cannot permit an extension |
| Earlier-delivery request and flexibility | Later-date permission is disabled; the earlier weekday is a fixed requirement |
| Requested earlier date and order dates | Must be on/after simulation start, before original delivery and a weekday |
| Original order, simulation and original delivery dates | Valid dates must follow order date ≤ simulation start ≤ original delivery |
| Affected quantity and original order quantity | At least one affected cabinet, no more than the order quantity |
| Affected assembled quantity and actual progress | Must fit both the changed subset and the assembled/unassembled totals |
| Quantity increase and original work | Positive whole additional quantity; original remaining work retained; added labour/material cost counted once |
| New cabinet cost and its scheduled labour | Total base cost cannot be below included assembly/testing labour |
| Required work and capacity | Zero required capacity blocks acceptance; negative/non-finite capacity is invalid input |
| Required materials and stock | Stock shortage must be sourceable; unsourceable shortage blocks acceptance |
| Required shortage and lead time | Unknown required lead time waits for information; never guessed as zero |
| Saved custom estimates and actual request | Description, affected quantities and Production snapshot must match; otherwise pending assessment |
| Rework and assembled quantity | No custom rework hours when no affected cabinets are already assembled |
| Technical support and selected change | Unsupported change cannot be accepted; a custom negative feasibility assessment cannot be overridden by a generic supported-type setting |
| Production edits and revisions | A stale saved record cannot overwrite a newer revision |
| Results and current inputs | Changed input, saved snapshot, catalogue or pricing policy requires a fresh evaluation |
| Source assumptions | Negative/non-finite rates, costs or operation hours and invalid component quantities are rejected |

A disabled control has no effect on the calculation. The model checks the same restrictions independently of the screen. Infeasible but valid scenarios remain available for what-if exploration and explain why they cannot be accepted. Missing or invalid essential data needs correction first.

Validation covers the implemented model; it does not validate real-world cabinet engineering, certification, delivery or company-wide scheduling.
