"""Explicit synthetic production, material, cost and three-option decision model."""
from datetime import date, timedelta
import math

ACCEPT = 'Accept new request'
REVISE = 'Accept with changing of delivery date'
REJECT = 'Do not accept the new request'


def working_days_between(start, finish):
    start, finish = date.fromisoformat(str(start)), date.fromisoformat(str(finish))
    days = 0
    while start < finish:
        start += timedelta(days=1)
        days += start.weekday() < 5
    return days


def add_working_days(start, count):
    result = date.fromisoformat(str(start))
    for _ in range(count):
        result += timedelta(days=1)
        while result.weekday() >= 5:
            result += timedelta(days=1)
    return result.isoformat()


def validate_order(order, catalog):
    # Do not allow invalid source assumptions to create plausible-looking results.
    for key, item in catalog['materials'].items():
        value = item.get('unit_cost')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'{key} unit cost must be finite and non-negative.')
    for profile in catalog['profiles']:
        for field in ('setup_hours','extra_assembly_hours','rework_hours_per_assembled','extra_test_hours'):
            value = profile.get(field)
            if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{profile['id']} {field} must be finite and non-negative.")
        for key, count in profile['materials_per_unit'].items():
            if key not in catalog['materials'] or isinstance(count,bool) or not isinstance(count,int) or count < 0:
                raise ValueError('Component requirements must reference known components with non-negative whole quantities.')
    for field in ['quantity', 'assembled']:
        value = order.get(field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f'{field} must be a whole number.')
    if not 0 <= order['assembled'] <= order['quantity'] or order['quantity'] < 1:
        raise ValueError('Assembled quantity must be between zero and the positive order quantity.')
    fields = ['unit_price', 'unit_base_cost', 'base_assembly_hours_per_remaining_unit',
              'base_test_hours_remaining', 'assembly_capacity_per_day', 'test_capacity_per_day',
              'planning_capacity_per_day', 'assembly_hourly_cost', 'test_hourly_cost', 'planning_hourly_cost']
    for field in fields:
        value = order.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'{field} must be a finite number of zero or more.')
    for field in ['production_queue_days', 'dispatch_days']:
        value = order.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f'{field} must be a whole number of zero or more.')
    if order['unit_price'] <= 0:
        raise ValueError('Original unit selling price must be greater than zero.')
    for field in ('order_date','snapshot_date','original_delivery_date'):
        try:
            date.fromisoformat(order.get(field, ''))
        except (TypeError, ValueError):
            raise ValueError(f'{field} must contain a valid date.') from None
    if date.fromisoformat(order['order_date']) > date.fromisoformat(order['snapshot_date']):
        raise ValueError('Original order date must be on or before the simulation start date.')
    if date.fromisoformat(order['original_delivery_date']) < date.fromisoformat(order['snapshot_date']):
        raise ValueError('Original delivery date must be on or after the scenario assessment date.')
    supported = order.get('supported_change_ids')
    if not isinstance(supported, list) or any(item not in {p['id'] for p in catalog['profiles']} for item in supported):
        raise ValueError('Supported change types must be selected from the change catalogue.')
    for key in catalog['materials']:
        record = order.get('materials', {}).get(key)
        if not isinstance(record, dict):
            raise ValueError(f'Missing Production stock record for {key}.')
        available = record.get('available')
        if isinstance(available, bool) or not isinstance(available, int) or available < 0:
            raise ValueError(f'Available {key} stock must be a non-negative whole number.')
        if not isinstance(record.get('can_replenish'), bool):
            raise ValueError(f'Select whether {key} can be replenished.')
        lead = record.get('lead_days')
        if lead is not None and (isinstance(lead, bool) or not isinstance(lead, int) or lead < 0):
            raise ValueError(f'{key} lead time must be a whole number of zero or more, or unknown.')


def duration(hours, capacity, label):
    if hours == 0:
        return 0
    if capacity == 0:
        return None
    value = hours / capacity
    if not math.isfinite(value):
        raise ValueError(f'{label} duration is too large to calculate.')
    return math.ceil(value)


def timeline(order, assembly_hours, test_hours, setup_hours=0, parts_wait=0):
    durations = [
        ('Production queue', order['production_queue_days']),
        ('Production planning and setup', duration(setup_hours, order['planning_capacity_per_day'], 'Planning')),
        ('Wait for additional parts', parts_wait),
        ('Assembly and wiring', duration(assembly_hours, order['assembly_capacity_per_day'], 'Assembly')),
        ('Production checks and testing', duration(test_hours, order['test_capacity_per_day'], 'Testing')),
        ('Dispatch allowance', order['dispatch_days']),
    ]
    if any(days is None for _, days in durations):
        return None, []
    start = 0
    rows = []
    for name, days in durations:
        rows.append({'Activity': name, 'Start day': start, 'Finish day': start + days, 'Working days': days})
        start += days
    return start, rows


def simulate(order, profile, catalog, affected, assembled_affected, allow_extension, max_extra_days):
    validate_order(order, catalog)
    if isinstance(affected, bool) or not isinstance(affected, int) or not 1 <= affected <= order['quantity']:
        raise ValueError('Affected quantity must be between one and the order quantity.')
    if not isinstance(assembled_affected, int) or isinstance(assembled_affected, bool):
        raise ValueError('Affected already-assembled quantity must be a whole number.')
    minimum = max(0, affected - (order['quantity'] - order['assembled']))
    maximum = min(affected, order['assembled'])
    if not minimum <= assembled_affected <= maximum:
        raise ValueError(f'Affected already-assembled quantity must be between {minimum} and {maximum} for this order.')
    if isinstance(max_extra_days, bool) or not isinstance(max_extra_days, int) or max_extra_days < 0:
        raise ValueError('Maximum additional days must be a non-negative whole number.')

    material_rows = []
    material_wait = 0
    blockers = []
    for key, per_unit in profile['materials_per_unit'].items():
        record = order['materials'][key]
        required = per_unit * affected
        short = max(0, required - record['available'])
        lead = 0
        if short:
            if not record['can_replenish']:
                blockers.append(f"{catalog['materials'][key]['name']}: shortage of {short}; replenishment is unavailable.")
                lead = None
            elif record['lead_days'] is None:
                raise ValueError(f"Production must enter a lead time for the shortage of {catalog['materials'][key]['name']}.")
            else:
                lead = record['lead_days']
                material_wait = max(material_wait, lead)
        material_rows.append({
            'Component': catalog['materials'][key]['name'], 'Per changed cabinet': per_unit,
            'Required': required, 'Available': record['available'], 'Shortage': short,
            'Ready after setup (working days)': 'Unavailable' if lead is None else str(lead),
            'Additional material cost (€)': required * catalog['materials'][key]['unit_cost'],
        })
    if profile['id'] not in order['supported_change_ids']:
        blockers.insert(0, 'Production has marked this change type as technically unsupported for this order.')

    rework = assembled_affected * profile['rework_hours_per_assembled']
    additional_install = affected * profile['extra_assembly_hours']
    additional_testing = affected * profile['extra_test_hours']
    setup = profile['setup_hours']
    original_assembly = (order['quantity'] - order['assembled']) * order['base_assembly_hours_per_remaining_unit']
    original_testing = order['base_test_hours_remaining']
    baseline_days, baseline_timeline = timeline(order, original_assembly, original_testing)
    revised_days, revised_timeline = timeline(order, original_assembly + additional_install + rework,
                                              original_testing + additional_testing, setup, material_wait)
    if revised_days is None:
        blockers.append('The required work has no allocated capacity in at least one Production activity.')
    available = working_days_between(order['snapshot_date'], order['original_delivery_date'])
    delay = None if revised_days is None else max(0, revised_days - available)
    if blockers:
        decision = REJECT
        reason = ' '.join(blockers)
        action = 'Sales should discuss a supported or sourceable alternative, or postpone this change.'
    elif delay == 0:
        decision = ACCEPT
        reason = f'The revised order needs {revised_days} working days, with {available} working days available before the original delivery date.'
        action = 'Sales can propose accepting the request with the original delivery date, subject to the entered Production assumptions and commercial agreement.'
    elif allow_extension and delay <= max_extra_days:
        decision = REVISE
        reason = f'The revised order needs {revised_days} working days, exceeding the original allowance by {delay}. This is within the {max_extra_days}-day extension open for discussion.'
        action = 'Sales should obtain customer agreement to the proposed later delivery date and any commercial adjustment before confirming the change.'
    else:
        decision = REJECT
        reason = f'The revised order needs {delay} additional working days beyond the original date. The customer’s entered date constraint does not permit that extension.'
        action = 'Sales should discuss another scope, a revised Production plan or postponement with the customer.'

    material_cost = sum(row['Additional material cost (€)'] for row in material_rows)
    setup_cost = setup * order['planning_hourly_cost']
    assembly_cost = (additional_install + rework) * order['assembly_hourly_cost']
    test_cost = additional_testing * order['test_hourly_cost']
    extra_cost = material_cost + setup_cost + assembly_cost + test_cost
    order_value = order['quantity'] * order['unit_price']
    original_cost = order['quantity'] * order['unit_base_cost']
    completion_date = None if revised_days is None or blockers else add_working_days(order['snapshot_date'], revised_days)
    baseline_date = None if baseline_days is None else add_working_days(order['snapshot_date'], baseline_days)
    outcome_a = 'Blocked by Production constraints' if blockers else ('Fits original date' if delay == 0 else f'Misses original date by {delay} working days')
    outcome_b = 'Blocked by Production constraints' if blockers else ('No later date needed' if delay == 0 else ('Requires customer agreement' if allow_extension and delay <= max_extra_days else 'Outside customer’s entered date constraint'))
    rows = [
        {'Option': 'A · Accept new request', 'Configuration': 'Requested change included', 'Delivery date': order['original_delivery_date'],
         'Extra work (hours)': setup + rework + additional_install + additional_testing, 'Extra cost (€)': extra_cost,
         'Result': outcome_a},
        {'Option': 'B · Accept with changing of delivery date', 'Configuration': 'Requested change included', 'Delivery date': completion_date or 'Cannot schedule',
         'Extra work (hours)': setup + rework + additional_install + additional_testing, 'Extra cost (€)': extra_cost,
         'Result': outcome_b},
        {'Option': 'C · Do not accept the new request', 'Configuration': 'Original order continues', 'Delivery date': order['original_delivery_date'],
         'Extra work (hours)': 0.0, 'Extra cost (€)': 0.0,
         'Result': 'Baseline date cannot be assessed' if baseline_days is None else ('Original order fits its date' if baseline_days <= available else f'Original order already exceeds its date by {baseline_days - available} working days')},
    ]
    return {
        'decision': decision, 'reason': reason, 'next_action': action, 'blockers': blockers,
        'available_days': available, 'baseline_days': baseline_days, 'revised_days': revised_days,
        'baseline_completion_date': baseline_date, 'revised_completion_date': completion_date,
        'extra_days_needed': delay, 'spare_days': None if revised_days is None else available - revised_days,
        'material_wait_days': material_wait, 'rework_hours': rework, 'setup_hours': setup,
        'extra_install_hours': additional_install, 'extra_test_hours': additional_testing,
        'total_extra_hours': setup + rework + additional_install + additional_testing,
        'original_assembly_hours_remaining': original_assembly, 'original_test_hours_remaining': original_testing,
        'additional_material_cost': material_cost, 'setup_cost': setup_cost, 'assembly_cost': assembly_cost,
        'test_cost': test_cost, 'total_extra_cost': extra_cost, 'original_order_value': order_value,
        'original_order_cost': original_cost, 'margin_before_change': order_value - original_cost,
        'margin_if_cost_absorbed': order_value - original_cost - extra_cost,
        'additional_charge_to_recover_cost': extra_cost,
        'material_requirements': material_rows, 'baseline_timeline': baseline_timeline,
        'revised_timeline': [] if blockers else revised_timeline, 'options': rows,
    }
