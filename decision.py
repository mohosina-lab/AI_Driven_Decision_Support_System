"""Expanded request types and transparent five-outcome commercial assessment."""
from copy import deepcopy
from datetime import date
import math
from model import simulate, validate_order, working_days_between, add_working_days

DECISIONS = [
    'Accept without changes to price or delivery date',
    'Accept with a new price',
    'Accept with a new delivery date',
    'Accept with a new price and delivery date',
    'Do not accept the new request',
]
PRICE_MODES = ['Keep original order price', 'Recover additional cost', 'Maintain original profit margin', 'Enter negotiated total price']


def nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(name + ' must be a finite non-negative number.')
    return value


def whole(value, name, minimum=0):
    nonnegative(value, name)
    if not isinstance(value, int) or value < minimum:
        raise ValueError(name + f' must be a whole number of at least {minimum}.')
    return value


def price_quote(order, extra_cost, price_mode, negotiated_price=0.0):
    """One pricing rule used by both the live UI preview and final decision."""
    original = order['quantity'] * order['unit_price']
    original_cost = order['quantity'] * order['unit_base_cost']
    nonnegative(extra_cost, 'Additional cost')
    if price_mode not in PRICE_MODES:
        raise ValueError('Select a supported pricing approach.')
    if price_mode == PRICE_MODES[0]:
        price = original
    elif price_mode == PRICE_MODES[1]:
        price = original + extra_cost
    elif price_mode == PRICE_MODES[2]:
        if original <= 0 or original_cost <= 0:
            raise ValueError('A positive original price and cost are needed to maintain the original margin.')
        price = math.ceil((original_cost+extra_cost) * original / original_cost * 100 - 1e-7)/100
    else:
        nonnegative(negotiated_price, 'Negotiated total price')
        if negotiated_price < original:
            raise ValueError(f'The proposed total price cannot be below the original order total of €{original:,.2f}. This prototype uses a no-discount company rule.')
        price = negotiated_price
    nonnegative(price, 'Proposed total price')
    price = round(price, 2)
    if price <= 0:
        raise ValueError('The proposed total price must be greater than zero.')
    if price < original:
        raise ValueError('The proposed total price cannot be below the original order total.')
    return price


def snapshot_signature(order):
    # Custom estimates must be reviewed if Production's work/stock/date facts change.
    return {k: deepcopy(v) for k, v in order.items() if k not in ('custom_assessment', 'last_updated')}


def validate_custom(a, order):
    if not a.get('description', '').strip():
        raise ValueError('Enter the custom request description before saving an assessment.')
    n = whole(a['affected'], 'Custom affected cabinets', 1)
    built = whole(a['assembled_affected'], 'Custom affected assembled cabinets')
    if n > order['quantity'] or not max(0, n - order['quantity'] + order['assembled']) <= built <= min(n, order['assembled']):
        raise ValueError('Custom affected quantities do not match the Production order.')
    if built == 0 and a.get('rework_hours',0):
        raise ValueError('Rework must be zero when no affected cabinets are assembled.')
    if not isinstance(a.get('feasible'), bool):
        raise ValueError('Select technical feasibility.')
    for key in ('setup_hours', 'installation_hours', 'rework_hours', 'testing_hours', 'material_cost'):
        nonnegative(a[key], key)
    whole(a['parts_wait_days'], 'Custom parts wait')


def assess(order, profile, catalog, *, affected, assembled_affected, allow_extension=False,
           max_extra_days=0, added_quantity=1, requested_date=None, custom_description='',
           price_mode='Recover additional cost', minimum_margin=20.0, negotiated_price=0.0,
           allow_price_change=True, max_extra_charge=50000.0):
    validate_order(order, catalog)
    if not isinstance(allow_extension, bool) or not isinstance(allow_price_change, bool):
        raise ValueError('Select the customer date and price flexibility.')
    whole(max_extra_days, 'Maximum additional days')
    nonnegative(minimum_margin, 'Minimum margin')
    if minimum_margin >= 100:
        raise ValueError('Minimum margin must be below 100%.')
    nonnegative(max_extra_charge, 'Maximum additional charge')
    nonnegative(negotiated_price, 'Negotiated price')
    if price_mode not in PRICE_MODES:
        raise ValueError('Select a supported pricing approach.')
    if not allow_extension:
        max_extra_days = 0
    if not allow_price_change:
        max_extra_charge = 0.0
    kind = profile.get('kind', 'product')
    work_order, work_profile, work_catalog = deepcopy(order), deepcopy(profile), deepcopy(catalog)
    target_date = order['original_delivery_date']
    new_quantity = order['quantity']
    custom = None
    if kind == 'custom':
        custom = order.get('custom_assessment')
        if not custom or not custom.get('complete'):
            return {'status': 'pending', 'message': 'Production assessment needed. Save an assessment for this exact request in the Production dashboard.'}
        validate_custom(custom, order)
        if (custom_description.strip() != custom['description'].strip() or affected != custom['affected']
            or assembled_affected != custom['assembled_affected'] or custom.get('snapshot') != snapshot_signature(order)):
            return {'status': 'pending', 'message': 'Production assessment needed. The saved assessment does not match this request, its quantities or the current Production snapshot.'}
        work_profile.update(setup_hours=custom['setup_hours'], extra_assembly_hours=custom['installation_hours']/affected,
                            rework_hours_per_assembled=custom['rework_hours']/assembled_affected if assembled_affected else 0,
                            extra_test_hours=custom['testing_hours']/affected)
        if not assembled_affected and custom['rework_hours']:
            raise ValueError('Custom rework hours must be zero when no affected cabinets are assembled.')
        work_order['supported_change_ids'] = [key for key in work_order['supported_change_ids'] if key != profile['id']]
        if custom['feasible']:
            work_order['supported_change_ids'].append(profile['id'])
    elif kind == 'quantity':
        whole(added_quantity, 'Additional cabinets', 1)
        new_quantity += added_quantity
        # Reuse stock/timeline calculation, but exclude added units from the original baseline.
        work_order['quantity'] = max(order['quantity'], added_quantity)
        work_order['assembled'] = 0
        affected, assembled_affected = added_quantity, 0
        work_profile.update(extra_assembly_hours=order['base_assembly_hours_per_remaining_unit'], extra_test_hours=.5,
                            materials_per_unit={'cabinet_set':1})
        # Incremental base cost includes labour. Residual materials avoid double-counting it.
        labour_unit = order['base_assembly_hours_per_remaining_unit']*order['assembly_hourly_cost'] + .5*order['test_hourly_cost']
        if labour_unit > order['unit_base_cost']:
            raise ValueError('Base cabinet cost is lower than its modelled assembly/testing labour. Production must correct the cost assumptions.')
        work_catalog['materials']['cabinet_set']['unit_cost'] = order['unit_base_cost'] - labour_unit
    elif kind == 'earlier':
        if not requested_date:
            raise ValueError('Select the requested earlier date.')
        target = date.fromisoformat(str(requested_date))
        if target < date.fromisoformat(order['snapshot_date']) or target >= date.fromisoformat(order['original_delivery_date']) or target.weekday() >= 5:
            raise ValueError('Earlier delivery must be a weekday on/after the simulation start and before the original delivery date.')
        target_date = target.isoformat()
        # Earlier delivery is a fixed request, even if stale inputs still permit extensions.
        allow_extension = False
        max_extra_days = 0
        affected, assembled_affected = order['quantity'], order['assembled']
    r = simulate(work_order, work_profile, work_catalog, affected, assembled_affected, allow_extension, max_extra_days)
    # Restore true baseline, and use the actual remaining normal work for every request type.
    from model import timeline
    original_assembly = (order['quantity']-order['assembled'])*order['base_assembly_hours_per_remaining_unit']
    baseline_days, baseline_timeline = timeline(order, original_assembly, order['base_test_hours_remaining'])
    parts_wait = custom['parts_wait_days'] if custom else r['material_wait_days']
    revised_days, revised_timeline = timeline(order, original_assembly+r['extra_install_hours']+r['rework_hours'],
                                             order['base_test_hours_remaining']+r['extra_test_hours'], r['setup_hours'], parts_wait)
    if custom:
        r['additional_material_cost'] = custom['material_cost']
        r['total_extra_cost'] = custom['material_cost'] + r['setup_cost'] + r['assembly_cost'] + r['test_cost']
        r['material_requirements'] = [{'Component': 'Custom materials (Production aggregate estimate)', 'Additional material cost (€)': custom['material_cost'], 'Ready after setup (working days)': str(parts_wait)}]
    original_value = order['quantity'] * order['unit_price']
    original_cost = order['quantity'] * order['unit_base_cost']
    cost = original_cost + r['total_extra_cost']
    original_profit = original_value - original_cost
    original_margin = original_profit / original_value if original_value else 0
    price = price_quote(order, r['total_extra_cost'], price_mode, negotiated_price)
    profit = round(price-cost, 2)
    margin = profit/price*100
    minimum_price = max(original_value, math.ceil(cost/(1-minimum_margin/100)*100-1e-7)/100)
    available = working_days_between(order['snapshot_date'], target_date)
    extra_days = None if revised_days is None else max(0, revised_days-available)
    completion = None if r['blockers'] or revised_days is None else add_working_days(order['snapshot_date'], revised_days)
    proposed_delivery = (target_date if extra_days == 0 else completion) if completion else None
    price_changed = abs(price-original_value) >= .005
    date_changed = proposed_delivery is not None and proposed_delivery != order['original_delivery_date']
    charge = round(price-original_value, 2)
    issues = list(r['blockers'])
    if extra_days and (not allow_extension or extra_days > max_extra_days):
        issues.append(f'The requested earlier date cannot be met: estimated completion is {completion}, {extra_days} working days after the requested date.' if kind == 'earlier' else f'The request needs {extra_days} working days beyond the requested date; customer flexibility does not cover this.')
    if margin + 1e-8 < minimum_margin:
        issues.append(f'Estimated margin {margin:.2f}% is below the demo company minimum of {minimum_margin:g}%. Minimum total price: €{minimum_price:,.2f}.')
    if charge > .005 and (not allow_price_change or charge > max_extra_charge + .005):
        issues.append(f'The additional charge of €{charge:,.2f} exceeds the customer’s entered price flexibility.')
    decision = DECISIONS[4] if issues else DECISIONS[(1 if price_changed else 0)+(2 if date_changed else 0)]
    reason = ' '.join(issues) if issues else f'The change is supported by the synthetic Production assumptions. Estimated completion is {completion}; proposed delivery is {proposed_delivery}. Estimated margin is {margin:.2f}%, meeting the {minimum_margin:g}% minimum.'
    next_action = 'Discuss an alternative scope, price or date before accepting.' if issues else 'Obtain customer agreement to the proposed scope, price and delivery date before confirming. This is a model recommendation.'
    current_margin = (original_value-cost)/original_value*100 if original_value else -math.inf
    options = []
    for i, label in enumerate(DECISIONS[:4]):
        use_price = i in (1,3)
        use_date = i in (2,3)
        row_price = price if use_price else original_value
        row_margin = margin if use_price else current_margin
        row_date = proposed_delivery if use_date else order['original_delivery_date']
        conditions = []
        if r['blockers']: conditions.append('Production constraint')
        if row_margin+1e-8 < minimum_margin: conditions.append('Below minimum margin')
        if not use_date and (kind=='earlier' or (completion and completion>order['original_delivery_date'])): conditions.append('Requested delivery cannot use original date')
        if use_date and extra_days and (not allow_extension or extra_days>max_extra_days): conditions.append('Outside date flexibility')
        if use_price and charge>.005 and (not allow_price_change or charge>max_extra_charge+.005): conditions.append('Outside price flexibility')
        if use_price and not price_changed: conditions.append('No price change proposed')
        if use_date and not date_changed: conditions.append('No delivery-date change proposed')
        options.append({'Option':label,'Total order price (€)':row_price,'Delivery date':row_date or 'Blocked','Estimated profit (€)':round(row_price-cost,2),'Assessment':'; '.join(conditions) if conditions else 'Possible subject to agreement'})
    options.append({'Option':DECISIONS[4],'Total order price (€)':original_value,'Delivery date':order['original_delivery_date'],'Estimated profit (€)':original_profit,'Assessment':'Original scope continues; original schedule '+('cannot be assessed' if baseline_days is None else ('fits' if baseline_days<=working_days_between(order['snapshot_date'],order['original_delivery_date']) else 'already exceeds its deadline'))})
    r.update(status='ready', decision=decision, reason=reason, next_action=next_action, options=options,
             available_days=available, target_date=target_date, revised_days=revised_days, revised_completion_date=completion,
             baseline_days=baseline_days, baseline_completion_date=None if baseline_days is None else add_working_days(order['snapshot_date'],baseline_days),
             baseline_timeline=baseline_timeline,revised_timeline=[] if r['blockers'] else revised_timeline,
             original_assembly_hours_remaining=original_assembly, original_test_hours_remaining=order['base_test_hours_remaining'],
             material_wait_days=parts_wait, extra_days_needed=extra_days, spare_days=None if revised_days is None else available-revised_days,
             original_order_value=original_value,original_order_cost=original_cost,margin_before_change=original_profit,
             margin_if_cost_absorbed=original_value-cost, additional_charge_to_recover_cost=r['total_extra_cost'],
             new_quantity=new_quantity, new_total_cost=cost, proposed_price=price, average_unit_price=price/new_quantity,
             proposed_delivery=proposed_delivery,additional_charge=charge,estimated_profit=profit,profit_change=profit-original_profit,
             profit_margin_percent=margin, minimum_margin=minimum_margin, minimum_total_price=minimum_price, commercial_issues=issues)
    return r
