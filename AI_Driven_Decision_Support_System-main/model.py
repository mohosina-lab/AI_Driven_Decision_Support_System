"""Transparent prototype rules for component replacement; no trained AI model."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Scenario:
    total: int = 50
    affected: int = 50
    wired: int = 30  # Affected cabinets already wired, not all wired cabinets in order.
    hours: float = 1.0
    stage: str = 'Assembly'
    availability: str = 'Available'
    workload: str = 'Low'
    deadline: str = 'Flexible'


def evaluate(s):
    if not (1 <= s.affected <= s.total and 0 <= s.wired <= s.affected):
        raise ValueError('Affected quantity must be within the order; wired quantity must be within affected quantity.')
    if s.hours < 0:
        raise ValueError('Rewiring hours cannot be negative.')
    if s.stage == 'Design' and s.wired:
        raise ValueError('At Design stage, affected cabinets already wired must be zero.')
    stage_score = {'Design': 1, 'Assembly': 2, 'Testing': 3}[s.stage]
    rows = [
        {'Factor': 'Production stage', 'Condition': s.stage, 'Score': stage_score,
         'Reason': {'Design': 'Design can be reviewed before physical work starts.', 'Assembly': 'Work in progress may need revision; check the affected cabinets.', 'Testing': 'A change may require rework and repeat testing.'}[s.stage]},
        {'Factor': 'Component availability', 'Condition': s.availability, 'Score': {'Available': 1, 'Limited': 2, 'Unavailable': 3}[s.availability],
         'Reason': {'Available': 'Procurement must still confirm suitability and sufficient quantity.', 'Limited': 'Check shortages and whether the order can be completed.', 'Unavailable': 'Replacement parts cannot currently be supplied; obtain a sourcing plan.'}[s.availability]},
        {'Factor': 'Production workload', 'Condition': s.workload, 'Score': {'Low': 1, 'Medium': 2, 'High': 3}[s.workload],
         'Reason': {'Low': 'There may be spare capacity; Production must confirm it.', 'Medium': 'Additional work competes with scheduled work.', 'High': 'Additional work may need rescheduling or extra capacity.'}[s.workload]},
        {'Factor': 'Delivery deadline', 'Condition': s.deadline, 'Score': {'Flexible': 1, 'Fixed': 3}[s.deadline],
         'Reason': 'There is room to discuss the shipment date.' if s.deadline == 'Flexible' else 'The shipment date has little flexibility; check the full schedule.'},
        {'Factor': 'Wired affected cabinets', 'Condition': str(s.wired), 'Score': 2 if s.wired else 1,
         'Reason': f'{s.wired} × {s.hours:g} hours = {s.wired * s.hours:g} additional rewiring hours. Hours do not directly determine delivery delay.' if s.wired else 'No rewiring is counted. Design, assembly changes and testing may still require work.'},
    ]
    # New conservative rule: retain any high contributor rather than averaging it away.
    score = max(row['Score'] for row in rows)
    labels = {1: 'LOW', 2: 'MEDIUM', 3: 'HIGH'}
    for row in rows:
        row['Impact'] = labels[row['Score']]
    drivers = [r['Factor'] for r in rows if r['Score'] == score]
    return {'level': labels[score], 'rows': rows, 'drivers': drivers, 'rewiring_hours': s.wired * s.hours}


def departments(s):
    return [
        {'Department': 'Sales', 'Action': 'Confirm the requested replacement and affected quantity with the customer.', 'Depends on': 'Clear customer request', 'Status': 'To check'},
        {'Department': 'Engineering', 'Action': 'Approve technical suitability and issue revised drawings or instructions.', 'Depends on': 'Sales: confirmed request', 'Status': 'Awaiting confirmation'},
        {'Department': 'Procurement', 'Action': f'Confirm enough approved replacement parts for {s.affected} cabinets and obtain lead times.', 'Depends on': 'Engineering: approved specification', 'Status': 'Awaiting confirmation'},
        {'Department': 'Production', 'Action': f'Confirm the work method and capacity for {s.wired * s.hours:g} estimated rewiring hours, plus other changed work.', 'Depends on': 'Engineering approval and Procurement availability', 'Status': 'Awaiting confirmation'},
        {'Department': 'Testing', 'Action': 'Decide repeat-test scope, estimate effort and reserve capacity.', 'Depends on': 'Engineering test requirements and Production completion plan', 'Status': 'Awaiting confirmation'},
        {'Department': 'Delivery', 'Action': 'Assess the shipment plan after production and testing dates are known.', 'Depends on': 'Production and Testing schedule', 'Status': 'Awaiting confirmation'},
        {'Department': 'Management', 'Action': 'Review unresolved capacity, cost or deadline conflicts if escalation is needed.', 'Depends on': 'Department assessments and approval limits', 'Status': 'If needed'},
    ]


@dataclass(frozen=True)
class Timing:
    """All durations are synthetic working days from a shared day zero."""
    engineering: float = 1.0
    parts: float = 2.0  # Starts after engineering approval.
    capacity: float = 10.0  # Person-hours per working day, reserved for rework.
    testing: float = 1.0  # Includes any test queue; starts after rework.
    window: float = 8.0  # Window reserved for the change, not the full order.
    parts_known: bool = True
    capacity_known: bool = True
    testing_known: bool = True


def schedule(s, t):
    """Sequential whole-production-day model; never estimates full-order delivery."""
    import math
    evaluate(s)
    numeric = (t.engineering, t.parts, t.capacity, t.testing, t.window)
    if any(not math.isfinite(v) or v < 0 for v in numeric):
        raise ValueError('Timing and capacity inputs must be finite and non-negative.')
    effort = s.wired * s.hours
    reasons = []
    if not t.parts_known:
        reasons.append('Replacement-part lead time is unknown.')
    if effort > 0 and not t.capacity_known:
        reasons.append('Production capacity for rework is unknown.')
    if effort > 0 and t.capacity_known and t.capacity == 0:
        reasons.append('No Production capacity is allocated to the required rework.')
    if not t.testing_known:
        reasons.append('Testing duration or availability is unknown.')
    if reasons:
        return {'status': 'UNDETERMINED', 'total': None, 'margin': None,
                'overrun': None, 'production': None, 'timeline': [], 'reasons': reasons}
    production = math.ceil(effort / t.capacity - 1e-12) if effort else 0
    durations = [t.engineering, t.parts, production, t.testing]
    labels = ['Engineering approval', 'Procurement / parts arrival', 'Production rewiring', 'Testing and test queue']
    timeline = []
    start = 0.0
    for name, duration in zip(labels, durations):
        timeline.append({'Activity': name, 'Start day': start, 'End day': start + duration,
                         'Working days': duration})
        start += duration
    margin = t.window - start
    return {'status': 'FITS WINDOW' if margin >= -1e-9 else 'EXCEEDS WINDOW',
            'total': start, 'margin': 0.0 if abs(margin) < 1e-9 else margin,
            'overrun': max(0.0, -margin), 'production': production,
            'timeline': timeline, 'reasons': []}
