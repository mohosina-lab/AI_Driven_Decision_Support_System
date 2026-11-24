"""Order-number-driven Sales simulator with a shared synthetic Production dashboard."""
from copy import deepcopy
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import streamlit as st
from model import validate_order, add_working_days, working_days_between
from decision import assess, DECISIONS, PRICE_MODES, validate_custom, snapshot_signature, price_quote
from repository import initialise, list_orders, get_order, update_order, RevisionConflict

BASE = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('SIMULATOR_DATA_DIR', BASE / 'data'))
DB = DATA_DIR / 'production.sqlite'
CATALOG = json.loads((BASE / 'data/change_catalog.json').read_text())
PROFILES = {item['id']: item for item in CATALOG['profiles']}
initialise(DB, BASE / 'data/synthetic_orders.json')
st.set_page_config(page_title='Sales & Production Order Simulator', page_icon='🏭', layout='wide')
st.caption('ORDER SIMULATOR · VERSION 7.4 · SYNTHETIC COMPANY DATA')
st.caption('Northstar Cabinets · Industrial electrical control cabinets · Sales and Production')
st.title('Should Sales accept the customer’s change?')
view = st.sidebar.radio('Workspace', ['Sales simulator', 'Production dashboard', 'Model assumptions'], key='workspace')
st.sidebar.caption('The order number loads a stored synthetic Production snapshot. Saved dashboard changes are shared within this local app. Original order records are preserved during simulations.')
st.sidebar.write('**Demo order numbers (sensors + remote, recover extra cost)**\n- ORD-001 · accept\n- ORD-002 · discuss a later date\n- ORD-003 · fixed deadline prevents acceptance\n- ORD-004 · before assembly\n- ORD-005 · component unavailable\n- ORD-006 · late-stage / low capacity')
st.sidebar.caption('More tests: ORD-007–ORD-020. Open the order examples below or see ORDER_TEST_GUIDE.md in the extracted folder.')
orders = list_orders(DB)
ids = [item['order_id'] for item, _ in orders]


def money(value):
    return f'€{value:,.2f}'


def assembly_progress(order):
    remaining = order['quantity'] - order['assembled']
    fraction = order['assembled'] / order['quantity']
    st.progress(fraction, text=f"Assembly progress: {fraction:.0%} — {order['assembled']} of {order['quantity']} cabinets assembled")
    st.caption('This measures assembly only. Testing and delivery preparation may still remain.')
    hours = remaining * order['base_assembly_hours_per_remaining_unit']
    st.write(f"**Original assembly work left:** {remaining} cabinets × {order['base_assembly_hours_per_remaining_unit']:g} hours = **{hours:g} person-hours**.")


def snapshot_panel(order, revision):
    st.subheader('Production details loaded automatically')
    st.caption(f"Order {order['order_id']} · record revision {revision} · updated {order['last_updated']}")
    st.write('**Customer** ' + order['customer'])
    st.write('**Product** ' + order['product'])
    a, b, c = st.columns(3)
    a.metric('Order quantity', order['quantity'])
    b.metric('Already assembled', order['assembled'])
    c.metric('Still to assemble', order['quantity'] - order['assembled'])
    assembly_progress(order)
    st.write('**Original order date** ' + order['order_date'])
    st.write('**Original delivery date** ' + order['original_delivery_date'])
    st.write('**Simulation start date** ' + order['snapshot_date'])
    st.table([
        {'Production information': 'Assembly / wiring capacity', 'Loaded value': f"{order['assembly_capacity_per_day']:g} person-hours per working day"},
        {'Production information': 'Checking / testing capacity', 'Loaded value': f"{order['test_capacity_per_day']:g} person-hours per working day"},
        {'Production information': 'Planning / setup capacity', 'Loaded value': f"{order['planning_capacity_per_day']:g} person-hours per working day"},
        {'Production information': 'Normal assembly per remaining cabinet', 'Loaded value': f"{order['base_assembly_hours_per_remaining_unit']:g} hours"},
        {'Production information': 'Normal checking still required', 'Loaded value': f"{order['base_test_hours_remaining']:g} hours"},
    ])
    st.caption('These are demonstration snapshots. Parts, cost rates and permitted change types also load from this Production record. The same stock is assessed independently in each what-if scenario.')


if view == 'Production dashboard':
    st.subheader('Production order dashboard')
    st.write('Northstar Cabinets has one Production department and several customer orders. Select an order to review or update its saved information.')
    st.subheader('1. Orders and assembly progress')
    a, b, c = st.columns(3)
    a.metric('Orders in this demo', len(orders))
    b.metric('Cabinets ordered', sum(o['quantity'] for o, _ in orders))
    c.metric('Cabinets still to assemble', sum(o['quantity'] - o['assembled'] for o, _ in orders))
    st.dataframe([
        {'Order': record['order_id'], 'Customer': record['customer'], 'Quantity': record['quantity'],
         'Assembled': record['assembled'], 'Still to assemble': record['quantity'] - record['assembled'],
         'Assembly progress': f"{record['assembled'] / record['quantity']:.0%}", 'Reserved assembly hours/day': record['assembly_capacity_per_day'],
         'Original order date': record['order_date'], 'Original delivery': record['original_delivery_date'], 'Revision': revision}
        for record, revision in orders
    ], hide_index=True)
    selected = st.selectbox('Production order number', ids, key='production_order')
    current_order, current_revision = get_order(DB, selected)
    assembly_progress(current_order)
    st.caption(f'Saved data version (revision): {current_revision}. Each successful save creates the next version. This is the data version, not a cabinet design revision.')
    st.subheader('2. Available time and normal work')
    st.info('Capacity means person-hours reserved for this order each working day, after other commitments. For example, two people working five hours each provide 10 person-hours/day. It is not the total time needed to finish the order.')
    st.caption('Planning, assembly and testing are activities within Production. Capacities are assessed separately for each order; this demo does not schedule all orders together.')
    if st.button('Reload this Production record', key='reload_production'):
        st.session_state.pop('production_form_order', None)
    if st.session_state.get('production_form_order', {}).get('order_id') != selected:
        st.session_state['production_form_order'] = deepcopy(current_order)
        st.session_state['production_form_revision'] = current_revision
        for key in list(st.session_state):
            if key.startswith('prodedit_'):
                del st.session_state[key]
    editing = st.session_state.production_form_order
    expected_revision = st.session_state.production_form_revision
    if current_revision != expected_revision:
        st.warning('This record was changed in another session. Reload before saving your edits.')
    if st.session_state.pop('production_saved', False):
        st.success('Production record saved. Sales will load the updated revision when the order is selected or the page refreshes.')
    with st.form('production_form'):
        a, b, c = st.columns(3)
        assembled = a.number_input('Already assembled', min_value=0, max_value=editing['quantity'], value=editing['assembled'], step=1, key='prodedit_assembled')
        assessment = b.date_input('Simulation start date', value=date.fromisoformat(editing['snapshot_date']), key='prodedit_assessment')
        order_date = a.date_input('Original order date', value=date.fromisoformat(editing['order_date']), key='prodedit_order_date', help='Date the customer originally placed this order. This is separate from the simulation start date.')
        due = c.date_input('Original delivery date', value=date.fromisoformat(editing['original_delivery_date']), key='prodedit_due')
        assembly_capacity = a.number_input('Assembly time available · person-hours/day', min_value=0.0, value=float(editing['assembly_capacity_per_day']), key='prodedit_capacity')
        test_capacity = b.number_input('Testing time available · person-hours/day', min_value=0.0, value=float(editing['test_capacity_per_day']), key='prodedit_test_capacity')
        planning_capacity = c.number_input('Planning time available · person-hours/day', min_value=0.0, value=float(editing['planning_capacity_per_day']), key='prodedit_planning_capacity')
        baseline_assembly = a.number_input('Normal assembly hours per remaining cabinet', min_value=0.0, value=float(editing['base_assembly_hours_per_remaining_unit']), key='prodedit_baseline_assembly')
        baseline_test = b.number_input('Normal checking hours still required', min_value=0.0, value=float(editing['base_test_hours_remaining']), key='prodedit_baseline_test')
        queue = c.number_input('Production queue · working days', min_value=0, value=editing['production_queue_days'], step=1, key='prodedit_queue')
        dispatch = a.number_input('Dispatch allowance · working days', min_value=0, value=editing['dispatch_days'], step=1, key='prodedit_dispatch')
        supported = st.multiselect('Technically supported change types', list(PROFILES), default=editing['supported_change_ids'], format_func=lambda key: PROFILES[key]['name'], key='prodedit_supported')
        st.subheader('3. Extra components available')
        st.caption('These quantities are compared with the selected request. Enough stock means no extra parts wait. A shortage uses the replenishment time below.')
        edited_materials = {}
        for key, component in CATALOG['materials'].items():
            st.write(component['name'])
            stock = editing['materials'][key]
            a, b, c = st.columns(3)
            count = a.number_input('Available quantity', min_value=0, value=stock['available'], step=1, key=f'prodedit_stock_{key}')
            replenish = b.checkbox('Shortages can be replenished', value=stock['can_replenish'], key=f'prodedit_replenish_{key}')
            lead_known = c.checkbox('Replenishment time known', value=stock['lead_days'] is not None, key=f'prodedit_known_{key}')
            lead = c.number_input('Replenishment · working days after setup', min_value=0, value=stock['lead_days'] or 0, step=1, key=f'prodedit_lead_{key}')
            edited_materials[key] = {'available': count, 'can_replenish': replenish, 'lead_days': lead if replenish and lead_known else None}
        st.subheader('4. Assessment for an Other change (optional)')
        st.caption('The team acts as Production in this fictional exercise. Enter total extra hours for this exact request, not hours per cabinet. Saving estimates does not approve a customer order. Reconfirm the assessment whenever Production data changes.')
        ca = editing.get('custom_assessment', {})
        custom_complete = st.checkbox('I have reviewed this custom assessment against the Production data above', value=False, key='prodedit_custom_complete')
        custom_description = st.text_area('Exact custom request description', value=ca.get('description',''), key='prodedit_custom_description')
        x, y = st.columns(2)
        custom_affected = x.number_input('Custom: cabinets affected', min_value=1, max_value=editing['quantity'], value=ca.get('affected',editing['quantity']), step=1, key='prodedit_custom_affected')
        custom_assembled = y.number_input('Custom: affected cabinets already assembled', min_value=0, max_value=editing['quantity'], value=ca.get('assembled_affected',editing['assembled']), step=1, key='prodedit_custom_assembled')
        custom_feasible = st.checkbox('This exact custom change is technically feasible (fictional assessment)', value=ca.get('feasible',False), key='prodedit_custom_feasible')
        custom_values = {}
        for key, label in [('setup_hours','Total extra planning / setup hours'),('installation_hours','Total extra installation hours'),('rework_hours','Total extra rework hours'),('testing_hours','Total extra testing hours'),('material_cost','Total extra materials cost (€)')]:
            custom_values[key] = st.number_input(label, min_value=0.0, value=float(ca.get(key,0)), key='prodedit_custom_'+key)
        custom_wait = st.number_input('Custom: parts waiting time after setup · working days', min_value=0, value=ca.get('parts_wait_days',0), step=1, key='prodedit_custom_wait')
        st.caption('Custom material cost is an aggregate estimate. Production is responsible for its parts availability and full waiting-time estimate; there is no separate stock deduction for this request.')
        submitted = st.form_submit_button('Save Production data')
    if submitted:
        updated = deepcopy(editing)
        updated.update(assembled=assembled, order_date=order_date.isoformat(), snapshot_date=assessment.isoformat(), original_delivery_date=due.isoformat(),
                       assembly_capacity_per_day=assembly_capacity, test_capacity_per_day=test_capacity,
                       planning_capacity_per_day=planning_capacity, base_assembly_hours_per_remaining_unit=baseline_assembly,
                       base_test_hours_remaining=baseline_test, production_queue_days=queue, dispatch_days=dispatch,
                       supported_change_ids=supported, materials=edited_materials)
        try:
            custom_data = dict(custom_values, complete=custom_complete, description=custom_description.strip(), affected=custom_affected,
                               assembled_affected=custom_assembled, feasible=custom_feasible, parts_wait_days=custom_wait)
            if custom_complete:
                validate_custom(custom_data, updated)
                custom_data['snapshot'] = snapshot_signature(updated)
            updated['custom_assessment'] = custom_data
            validate_order(updated, CATALOG)
            update_order(DB, updated, expected_revision)
        except (ValueError, RevisionConflict) as error:
            st.error(str(error))
        else:
            st.session_state.pop('production_form_order', None)
            st.session_state.production_saved = True
            st.rerun()
    st.subheader('5. How Sales gets the assessment')
    st.write('Save the Production information above. Sales enters the order number, selects a change and clicks Evaluate customer request. The simulator uses the latest saved data to calculate extra work, materials, cost and the recommended decision.')
    st.caption('Saving data does not accept a customer request. Open Sales simulator to assess a specific change. A simulation does not consume stock or reserve people.')
    st.stop()

if view == 'Model assumptions':
    st.subheader('Our fictional company rules — in simple words')
    st.write('Northstar Cabinets makes industrial electrical control cabinets. Sales and Production are the two departments. All orders, prices, hours and rules are synthetic assumptions, with no company validation.')
    st.markdown('**What the five recommendations mean**')
    st.table([{'Recommendation':d} for d in DECISIONS])
    st.write('A recommendation requires technical support, sourceable materials, reserved capacity, an acceptable date and a price meeting the entered minimum profit margin. Price and date changes need customer agreement.')
    st.write('A no-discount rule prevents a new total price below the original order total. Customer price limits are separate from proposals. Inactive flexibility limits are zero. Minimum margin is an editable fictional company rule, initially 20%. Margin = (selling price − modelled total cost) / selling price. Recover additional cost preserves the original euro profit; maintain original margin preserves its percentage. Values are before tax. Estimated profit excludes any costs outside the model.')
    st.markdown('**Available requests and their assumptions**')
    for pr in CATALOG['profiles']:
        with st.expander(pr['name']):
            st.write(pr['explanation'])
            if pr['kind']=='product':
                st.table([{'Once per request: setup hours':pr['setup_hours'],'Per affected cabinet: installation hours':pr['extra_assembly_hours'],'Per affected assembled cabinet: rework hours':pr['rework_hours_per_assembled'],'Per affected cabinet: testing hours':pr['extra_test_hours']}])
                st.table([{'Component':CATALOG['materials'][k]['name'],'Per affected cabinet':v,'Unit cost (€)':CATALOG['materials'][k]['unit_cost']} for k,v in pr['materials_per_unit'].items()])
    st.markdown('**Important modelling limits**')
    st.write('One request type is assessed at a time. Each order has constant daily capacity reserved after other commitments. Simulations do not consume inventory, reserve people, move other orders or confirm delivery. No live ERP connection or AI model is used; explanations follow visible rules.')
    st.write('The remaining original order work is included. Queue, setup, parts wait, assembly, testing and dispatch run sequentially. Work phases round up to whole days. Dates count Monday–Friday, excluding the simulation start day. Public holidays are not modelled. An earlier-delivery request does not create overtime or a shared schedule.')
    st.write('Quantity increases use full original-configuration base cost for each added cabinet, including its labour and materials once. Added testing is 0.5 hour per new cabinet. The complete materials-set valuation is the residual base cost after its scheduled labour. No upgrades to new cabinets are combined in the same request.')
    st.write('Other changes need a matching saved Production assessment. A new description, quantity or Production snapshot invalidates the old assessment. Unknown data produces a pending assessment, rather than an acceptance or a guessed rejection.')
    st.stop()

order_id = st.selectbox('Order number', ids, key='sales_order_id')
record = get_order(DB, order_id)
if record is None:
    st.error('Order number not found. Try: '+', '.join(ids))
    st.stop()
order, revision = record
try:
    validate_order(order, CATALOG)
except ValueError as error:
    st.error('Production data needs correction: '+str(error))
    st.stop()
if st.session_state.get('sales_loaded_record') != (order_id,revision):
    st.session_state.update(sales_loaded_record=(order_id,revision),change_id=order['default_change'],affected=order['quantity'],
        assembled_affected=order['assembled'],allow_extension=order['default_allow_extension'],max_extra=order['default_max_extra_days'],
        custom_description=order.get('custom_assessment',{}).get('description',''),
        price_mode=order.get('default_price_mode',PRICE_MODES[1]),allow_price=True,max_charge=50000.0,min_margin=20.0)
    for key in ('earlier_date','added_quantity','negotiated'):
        st.session_state.pop(key,None)
left,right=st.columns([1.15,1],gap='large')
with right:
    with st.expander('Production details loaded automatically',expanded=True):
        snapshot_panel(order,revision)
    st.caption('One request type per scenario. No stock or other orders are changed by a simulation.')
    st.write('**Try this scenario:** '+order.get('example_note','Change the request and compare the result.'))
with left:
    st.subheader('1. What does the customer want?')
    change_id=st.selectbox('Requested change',list(PROFILES),format_func=lambda key:PROFILES[key]['name'],key='change_id')
    profile=PROFILES[change_id]
    kind=profile['kind']
    st.info(profile['explanation'])
    affected=order['quantity']; assembled_affected=order['assembled']; added_quantity=1; requested_date=None; custom_description=''
    if kind in ('product','custom'):
        affected=st.number_input('Cabinets requiring the change',min_value=1,max_value=order['quantity'],step=1,key='affected')
        low=max(0,affected-(order['quantity']-order['assembled']));high=min(affected,order['assembled'])
        st.session_state.assembled_affected=max(low,min(st.session_state.assembled_affected,high))
        if low==high:
            assembled_affected=low
            st.caption(f'{low} affected cabinets are already assembled. Rework applies only to these cabinets.')
        else:
            assembled_affected=st.number_input('Of these, how many are already assembled?',min_value=low,max_value=high,step=1,key='assembled_affected')
    if kind=='quantity':
        added_quantity=st.number_input('Additional cabinets requested',min_value=1,max_value=10000,value=10,step=1,key='added_quantity')
        st.write(f"New order quantity: **{order['quantity']+added_quantity} cabinets**. New cabinets use the original configuration.")
    if kind=='earlier':
        default_days=max(0,working_days_between(order['snapshot_date'],order['original_delivery_date'])-5)
        requested_date=st.date_input('Customer’s requested earlier delivery date',value=date.fromisoformat(add_working_days(order['snapshot_date'],default_days)),key='earlier_date').isoformat()
        st.caption('Uses existing reserved capacity. It cannot calculate delays to other orders or assume extra staff.')
    if kind=='custom':
        custom_description=st.text_area('Describe the exact other change',key='custom_description')
        st.caption('Production must save matching estimates under Production dashboard → Assessment for an Other change. For this demo your team acts as Production. No request is sent to another person.')
    st.subheader('2. Customer flexibility and price')
    if kind=='earlier':
        st.checkbox('Customer can consider a later date',value=False,disabled=True,key='earlier_no_extension')
        st.number_input('Maximum extra working days beyond the requested date',min_value=0,value=0,step=1,disabled=True,key='earlier_no_extra')
        allow_extension=False
        max_extra=0
        st.caption('For an earlier-delivery request, the requested earlier date is fixed. If the estimated completion misses it, the simulator will not recommend accepting that request. Other request types keep their date-flexibility settings.')
    else:
        allow_extension=st.checkbox('Customer can consider a later date',key='allow_extension')
        if allow_extension:
            max_extra=st.number_input('Maximum extra working days beyond the requested date',min_value=0,step=1,key='max_extra')
        else:
            st.number_input('Maximum extra working days beyond the requested date',min_value=0,value=0,step=1,key='no_date_extra',disabled=True)
            max_extra=0
    price_mode=st.selectbox('How should we price the change?',PRICE_MODES,key='price_mode')
    st.caption('Recover additional cost keeps the original euro profit. Maintain original margin keeps its percentage. The original total price stays fixed only when Keep original order price is selected.')
    original_total=round(order['quantity']*order['unit_price'],2)
    st.write(f"**Original total order price: {money(original_total)}**")
    st.caption('Company rule for this prototype: the new total price cannot be below the original total. This is a chosen demo policy, not a rule for every business.')
    negotiated=0.0
    if price_mode==PRICE_MODES[3]:
        negotiated=st.number_input('Proposed negotiated TOTAL order price (€), before tax',min_value=original_total,value=original_total,step=100.0,key='negotiated',help='Price for the whole order, not the extra charge or a maximum budget. The minimum is the original total order price.')
    # Calculate a preview with the same engine. This does not save or accept an order.
    preview=None
    preview_error=None
    try:
        preview=assess(order,profile,CATALOG,affected=affected,assembled_affected=assembled_affected,
                       added_quantity=added_quantity,requested_date=requested_date,custom_description=custom_description,
                       allow_extension=allow_extension,max_extra_days=max_extra,price_mode=price_mode,
                       negotiated_price=negotiated,minimum_margin=0.0,allow_price_change=True,max_extra_charge=0.0)
    except (ValueError,KeyError) as error:
        preview_error=str(error)
    proposed=preview['proposed_price'] if preview and preview['status']=='ready' else None
    # Original-price and manual-price modes have known prices even while Production data is pending.
    if proposed is None and price_mode in (PRICE_MODES[0],PRICE_MODES[3]):
        try:
            proposed=price_quote(order,0,price_mode,negotiated)
        except ValueError as error:
            preview_error=str(error)
    extra_charge=None if proposed is None else round(proposed-original_total,2)
    if proposed is not None:
        a,b=st.columns(2)
        a.metric('Proposed total order price',money(proposed))
        b.metric('Additional charge above original',money(extra_charge))
    if extra_charge is not None and extra_charge>0:
        st.session_state.setdefault('allow_price',True)
        allow_price=st.checkbox('Customer can consider a price increase',key='allow_price')
        if allow_price:
            st.session_state.setdefault('max_charge',50000.0)
            max_charge=st.number_input('Customer’s maximum acceptable ADDITIONAL charge (€)',min_value=0.0,key='max_charge',help='This is a customer budget above the original order total. It is separate from the proposed price.')
            st.caption(f"Customer's maximum total price: {money(original_total+max_charge)}. Required additional charge: {money(extra_charge)}.")
            if extra_charge>max_charge:
                st.warning('The proposed increase exceeds the customer’s limit. Evaluation will not recommend accepting this proposal. Change the proposed price or discuss a higher limit.')
        else:
            st.number_input('Customer’s maximum acceptable ADDITIONAL charge (€)',min_value=0.0,value=0.0,key='no_price_extra',disabled=True)
            max_charge=0.0
            st.warning('This proposal increases the price, but the customer has not allowed an increase. Evaluation will not recommend acceptance.')
    else:
        st.checkbox('Customer can consider a price increase',value=False,disabled=True,key='no_price_increase')
        st.number_input('Customer’s maximum acceptable ADDITIONAL charge (€)',min_value=0.0,value=0.0,disabled=True,key='no_price_extra')
        allow_price=False
        max_charge=0.0
        st.caption('Price-increase controls are not applicable when there is no increase, or the price is awaiting Production estimates.')
    if preview_error:
        st.error('Correct this information before evaluation: '+preview_error)
    with st.expander('Fictional company profit rule'):
        minimum_margin=st.number_input('Minimum estimated order margin (%)',min_value=0.0,max_value=99.0,key='min_margin')
        st.caption('Editable synthetic policy, not an industry standard. Margin = profit ÷ total selling price. A reduction in profit is not automatically a loss.')
    run=st.button('Evaluate customer request',type='primary',key='evaluate',disabled=preview_error is not None)

args=dict(affected=affected,assembled_affected=assembled_affected,allow_extension=allow_extension,max_extra_days=max_extra,
          added_quantity=added_quantity,requested_date=requested_date,custom_description=custom_description,
          price_mode=price_mode,minimum_margin=minimum_margin,negotiated_price=negotiated,
          allow_price_change=allow_price,max_extra_charge=max_charge)
fingerprint=hashlib.sha256(json.dumps(dict(order=order,revision=revision,profile=profile,catalog=CATALOG,args=args),sort_keys=True).encode()).hexdigest()
if run:
    st.session_state.pop('evaluated',None)
    try:
        result=assess(order,profile,CATALOG,**args)
    except (ValueError,KeyError) as error:
        st.error('Assessment needs corrected information: '+str(error))
    else:
        st.session_state.evaluated={'fingerprint':fingerprint,'result':result}
saved=st.session_state.get('evaluated')
if not saved or saved['fingerprint']!=fingerprint:
    st.caption('Click Evaluate customer request for the displayed information. Changing any input requires a fresh evaluation.')
    st.stop()
r=saved['result']
if r['status']=='pending':
    st.warning(r['message'])
    st.write('Sales should wait for the missing Production assessment. This is a pending status, not a rejection.')
    st.stop()
st.divider()
st.subheader('3. Recommended decision for Sales')
if r['decision']==DECISIONS[4]:st.error(r['decision'])
elif r['decision']==DECISIONS[0]:st.success(r['decision'])
else:st.warning(r['decision'])
st.write(r['reason'])
st.write('**Sales next action:** '+r['next_action'])
st.caption('Price and delivery are proposals until agreed. All estimates use fictional assumptions. The simulator does not commit or change the original order.')
a,b,c,d=st.columns(4)
a.metric('Proposed total order price',money(r['proposed_price']))
b.metric('Additional customer charge',money(r['additional_charge']))
c.metric('Estimated order profit',money(r['estimated_profit']))
d.metric('Estimated completion' if kind=='earlier' and r['decision']==DECISIONS[4] else 'Proposed delivery date',r['revised_completion_date'] if kind=='earlier' and r['decision']==DECISIONS[4] and r['revised_completion_date'] else (r['proposed_delivery'] or 'Blocked'))
a,b,c,d=st.columns(4)
a.metric('Additional modelled cost',money(r['total_extra_cost']))
b.metric('Average price per cabinet',money(r['average_unit_price']))
c.metric('Profit change vs original',money(r['profit_change']))
d.metric('New total order quantity',r['new_quantity'])
st.caption('Average cabinet price = total order price ÷ new total quantity. Changed and unchanged cabinets may have different costs; the displayed figure is an order average. All prices exclude tax.')
with st.expander('Explain this result in simple words',expanded=True):
    if r['blockers']:
        st.write('Production cannot complete this request under the current conditions: '+' '.join(r['blockers']))
    else:
        st.write(f"The remaining order without this request takes {r['baseline_days']} working days. With the request it takes {r['revised_days']} working days. There are {r['available_days']} working days until the requested date ({r['target_date']}).")
    st.write(f"Original estimated profit: {money(r['margin_before_change'])}. Proposed estimated profit: {money(r['estimated_profit'])}. Margin: {r['profit_margin_percent']:.2f}% of the proposed selling price. Demo minimum: {minimum_margin:g}%.")
    if r['estimated_profit']<0:st.write('The proposal makes an estimated loss under the included costs.')
    elif r['profit_change']<0:st.write('The proposal still makes an estimated profit, but less than the original order.')
    st.caption('This explanation follows the visible calculations. No API key or AI service is used.')
options,work,parts,costs=st.tabs(['Compare five decisions','Work and schedule','Materials','Price and profit'])
with options:
    st.dataframe(r['options'],hide_index=True)
    st.caption('Alternatives use the selected pricing proposal and current customer flexibility. Do not accept keeps the original scope. Some alternatives are unnecessary when no price or date change is proposed.')
with work:
    st.table([{'Work item':name,'Person-hours':value} for name,value in [
        ('Remaining normal assembly',r['original_assembly_hours_remaining']),('Remaining normal testing',r['original_test_hours_remaining']),
        ('Extra planning/setup',r['setup_hours']),('Extra installation / assembly',r['extra_install_hours']),
        ('Rework on assembled cabinets',r['rework_hours']),('Extra testing',r['extra_test_hours'])]])
    if r['revised_timeline']:
        st.dataframe(r['revised_timeline'],hide_index=True)
    st.caption('Person-hours measure work. Working days depend on daily reserved capacity. Each work phase rounds up separately; activities run sequentially. Weekends are skipped; public holidays are not modelled.')
with parts:
    rows=[]
    for row in r['material_requirements']:
        status='Production aggregate estimate' if 'Shortage' not in row else ('Enough stock' if not row['Shortage'] else ('Cannot replenish shortage' if row['Ready after setup (working days)']=='Unavailable' else 'Shortage — replenish'))
        rows.append(dict(row,Status=status))
    if rows:st.dataframe(rows,hide_index=True)
    else:st.write('No extra materials are included for this request.')
    st.write(f"Additional parts wait after setup: {r['material_wait_days']} working days.")
with costs:
    st.table([{'Cost item':name,'Amount (€)':value} for name,value in [
        ('Extra materials',r['additional_material_cost']),('Extra planning/setup labour',r['setup_cost']),
        ('Extra assembly/rework labour',r['assembly_cost']),('Extra testing labour',r['test_cost']),('Total extra cost',r['total_extra_cost']),
        ('Original total order cost',r['original_order_cost']),('New total order cost',r['new_total_cost'])]])
    st.table([{'Measure':name,'Amount (€)':value} for name,value in [
        ('Original total selling price',r['original_order_value']),('Proposed total selling price',r['proposed_price']),
        ('Additional customer charge',r['additional_charge']),('Original estimated profit',r['margin_before_change']),
        ('Estimated profit if original total price is kept',r['margin_if_cost_absorbed']),
        ('Proposed estimated profit',r['estimated_profit']),('Minimum price for entered margin rule',r['minimum_total_price'])]])
    st.caption('Profit = selling price − included costs. Original unit cost already includes original materials/labour. Additional costs are charged once. Wider overheads, taxes, penalties, salvage and impact on other orders are outside this prototype.')
report=dict(project='Northstar Cabinets — Version 7.4',basis='Synthetic assumptions, no company validation; rule-based recommendation',
    order=order,revision=revision,request_type=profile,args=args,result=r)
st.download_button('Download decision and assumptions',json.dumps(report,indent=2,ensure_ascii=False),f'{order_id}_decision.txt',mime='text/plain')
