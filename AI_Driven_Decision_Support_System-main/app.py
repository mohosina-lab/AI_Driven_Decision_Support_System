from dataclasses import replace, asdict
import json
import streamlit as st
from model import Scenario, Timing, evaluate, departments, schedule

st.set_page_config(page_title='Customer Change Request Simulator', page_icon='🔄', layout='wide')
st.caption('FICTIONAL COMPANY · SYNTHETIC DATA · VERSION 2')
st.title('Customer Change Request Simulator')
st.write('Explore the work a customer change could create, the departments involved and the checks needed before Sales makes a commitment.')
st.info('Start with the example: replace a component in 50 cabinets, with 30 already wired. The editable assumption of 1 hour per cabinet gives 30 additional rewiring hours.')

with st.sidebar:
    st.header('How to use this demo')
    st.write('1. Enter the request and current conditions.\n2. Review the results.\n3. Compare the timing of the same request.\n4. Take the action list to your team.')
    st.caption('Version 2: open Connected schedule to see the dependency calculations. Results update when you change an input. Nothing is sent to other people. Inputs are not saved between sessions; download the summary to keep a copy.')

st.header('1. Describe the customer request')
request = st.text_area('What does the customer want?', 'Replace Component A with Component B in all 50 electrical cabinets.', key='request')
st.caption('This version models component replacement only. The description is recorded in the summary; it is not automatically interpreted by AI.')
a, b, c = st.columns(3)
total = a.number_input('Total cabinets in order', min_value=1, value=50, step=1, key='total')
affected = b.number_input('Cabinets requiring the change', min_value=1, value=50, step=1, key='affected')
wired = c.number_input('Affected cabinets already wired', min_value=0, value=30, step=1, key='wired', help='Count only already-wired cabinets that require this change.')

st.header('2. Set the current conditions')
a, b = st.columns(2)
stage = a.selectbox('Production stage of affected work', ['Design', 'Assembly', 'Testing'], index=1, key='stage')
availability = b.selectbox('Component availability', ['Available', 'Limited', 'Unavailable'], key='availability')
workload = a.selectbox('Production workload', ['Low', 'Medium', 'High'], key='workload')
deadline = b.selectbox('Delivery deadline', ['Flexible', 'Fixed'], key='deadline')
hours = st.number_input('Assumed rewiring hours per wired cabinet', min_value=0.0, value=1.0, step=0.25, key='hours', help='Person-hours of rewiring only. Editable synthetic assumption; no real company data is required.')
if not request.strip():
    st.error('Please describe the customer request.')
    st.stop()
try:
    scenario = Scenario(total, affected, wired, hours, stage, availability, workload, deadline)
    result = evaluate(scenario)
except ValueError as error:
    st.error(str(error))
    st.stop()

st.header('3. Set the synthetic schedule assumptions')
st.write('Fictional company: Northstar Cabinets. These invented values demonstrate dependencies; they are not measured company data.')
st.caption('Day 0 is the moment the request is assessed. Parts lead time starts AFTER Engineering approval. All stages run sequentially. The window below is reserved for this change only, not the whole order.')
a, b, c = st.columns(3)
engineering_days = a.number_input('Engineering approval · working days', min_value=0.0, value=1.0, step=0.5, key='engineering_days')
parts_days = b.number_input('Parts lead time after approval · working days', min_value=0.0, value=2.0, step=0.5, key='parts_days')
capacity = c.number_input('Rework capacity · person-hours per working day', min_value=0.0, value=10.0, step=1.0, key='capacity')
test_days = a.number_input('Testing + test queue · working days', min_value=0.0, value=1.0, step=0.5, key='test_days')
window = b.number_input('Available window for change · working days', min_value=0.0, value=8.0, step=0.5, key='window')
st.caption('Workload and component availability above drive the qualitative category only. The numeric inputs here independently drive the schedule. “Unavailable” means not in stock now; a known lead time may still describe future supply. A flexible deadline does not automatically enlarge the entered window.')
a, b, c = st.columns(3)
parts_known = a.checkbox('Parts lead time known for this scenario', value=True, key='parts_known')
capacity_known = b.checkbox('Rework capacity known for this scenario', value=True, key='capacity_known')
testing_known = c.checkbox('Testing duration and availability known', value=True, key='testing_known')
timing = Timing(engineering_days, parts_days, capacity, test_days, window, parts_known, capacity_known, testing_known)
plan = schedule(scenario, timing)

st.header('4. Review the result')
a, b, c = st.columns(3)
a.metric('Overall impact · prototype rule', result['level'])
b.metric('Additional rewiring', f"{result['rewiring_hours']:g} person-hours")
c.metric('Synthetic change schedule', plan['status'])
if result['level'] == 'HIGH':
    st.error('High-impact condition: ' + ', '.join(result['drivers']) + '. Explore the department checks in this fictional scenario before considering a commitment.')
elif result['level'] == 'MEDIUM':
    st.warning('Review needed: ' + ', '.join(result['drivers']) + '.')
else:
    st.success('All listed factors are low under the current rules. Department checks are still required.')
st.write(f"**Rewiring calculation:** {wired} affected wired cabinets × {hours:g} hours = **{result['rewiring_hours']:g} person-hours**.")
st.caption('This is additional rewiring effort, not elapsed time or delivery delay. Engineering, procurement, other production work and testing effort are not included. Costs and shipment dates are not calculated.')
propagation, summary, impact, actions, comparison, evidence = st.tabs(['Connected schedule', 'Scenario summary', 'Why this impact?', 'Departments & next steps', 'Compare timing', 'Assumptions & rules'])
with summary:
    st.subheader('Your scenario')
    st.write(request)
    st.table([{'Item': k, 'Value': str(v)} for k, v in {
        'Order quantity': total, 'Affected quantity': affected, 'Affected already wired': wired,
        'Affected not yet wired': affected - wired, 'Production stage': stage,
        'Component availability': availability, 'Production workload': workload, 'Delivery deadline': deadline,
    }.items()])
with impact:
    st.subheader('What contributes to the result?')
    st.dataframe([{k: row[k] for k in ['Factor', 'Condition', 'Impact', 'Reason']} for row in result['rows']], hide_index=True)
    st.write('**Why this overall level?** The highest individual factor determines the overall level. Leading factors: ' + ', '.join(result['drivers']) + '.')
    st.caption('Impact categories identify conditions needing attention. They are not probabilities, financial estimates or validated forecasts.')
with actions:
    st.subheader('Who needs to check what?')
    st.dataframe(departments(scenario), hide_index=True)
    st.subheader('Before Sales confirms the change')
    st.markdown('1. Confirm the exact request and affected quantity.\n2. Obtain Engineering approval and updated instructions.\n3. Confirm replacement quantities and lead times with Procurement.\n4. Ask Production to assess rework and available capacity.\n5. Confirm repeat testing and testing capacity.\n6. Review the shipment date and any price change with the responsible teams.\n7. Escalate unresolved conflicts, then communicate the agreed response to the customer.')
    st.info('These are suggested checks, not completed approvals. The app does not verify or collect department sign-offs.')
with comparison:
    st.subheader('The same request at two different times')
    st.write('Scenario A moves the affected work to Design, before wiring. Scenario B uses your current inputs. Quantities, parts availability, workload, deadline and rewiring assumption stay the same.')
    before = evaluate(replace(scenario, stage='Design', wired=0))
    st.table([
        {'Measure': 'Production stage', 'A · Before wiring': 'Design', 'B · Current scenario': stage},
        {'Measure': 'Affected cabinets already wired', 'A · Before wiring': '0', 'B · Current scenario': str(wired)},
        {'Measure': 'Additional rewiring hours', 'A · Before wiring': '0', 'B · Current scenario': f"{result['rewiring_hours']:g}"},
        {'Measure': 'Overall impact', 'A · Before wiring': before['level'], 'B · Current scenario': result['level']},
        {'Measure': 'Delivery effect', 'A · Before wiring': 'Requires schedule assessment', 'B · Current scenario': 'Requires schedule assessment'},
    ])
    st.write(f"Your current scenario adds **{result['rewiring_hours']:g} rewiring hours** compared with changing the design before wiring begins.")
    st.caption('Zero rewiring does not mean zero work. Both scenarios still require engineering, component and schedule checks. Their overall categories may match if another factor drives the result.')
with evidence:
    st.subheader('What is known, assumed or still unconfirmed?')
    st.table([
        {'Information': 'Request, quantities, stage, parts, workload and deadline', 'Source / status': 'User-entered; not independently verified'},
        {'Information': f'{hours:g} rewiring hours per wired cabinet', 'Source / status': 'Editable synthetic assumption; not measured or externally validated'},
        {'Information': f"{result['rewiring_hours']:g} additional rewiring hours", 'Source / status': 'Calculated from user inputs and the assumption'},
        {'Information': 'Impact levels and department dependencies', 'Source / status': 'Documented synthetic rules; team consistency review only'},
        {'Information': 'Technical suitability, final cost and delivery commitment', 'Source / status': 'Awaiting department assessment; not calculated'},
    ])
    st.markdown('**Transparent rules**\n- Design = Low; Assembly = Medium; Testing = High.\n- Components: Available = Low; Limited = Medium; Unavailable = High.\n- Workload: Low / Medium / High maps to the same impact.\n- Deadline: Flexible = Low; Fixed = High.\n- Wired affected cabinets: none = Low; any = Medium.\n- Overall impact = highest factor. This replaces the original average rule so a high condition remains visible.\n- Rewiring effort = affected wired quantity × assumed hours per cabinet. Effort does not change the category beyond the wired-cabinet rule.')
    st.write('Team review only: role-play the departments, check calculations and compare synthetic scenarios. Do not conduct interviews. These checks do not establish real-world validity. Ask your facilitator what validation method is expected under the no-interview instruction.')

with propagation:
    st.subheader('How the change moves between departments')
    st.write('Engineering approval releases the specification. Procurement then obtains parts. Production then completes rewiring. Testing follows. Delivery reviews the result against the change window.')
    st.info('This model estimates completion of the change activities only. Normal assembly, other order work, transport, costs, holidays and calendar dates are excluded. Rework capacity is assumed constant and reserved. Real delivery remains unconfirmed.')
    def show_plan(p):
        if p['total'] is None:
            st.warning('Schedule cannot be determined: ' + ' '.join(p['reasons']))
            return
        a, b, c = st.columns(3)
        a.metric('Change activities complete by', f"Day {p['total']:g}")
        b.metric('Production rewiring duration', f"{p['production']:g} working days")
        c.metric('Window margin · positive = spare time', f"{p['margin']:g} working days")
        st.table(p['timeline'])
        if p['margin'] >= 0:
            st.success(f"FITS the synthetic {window:g}-day window, with {p['margin']:g} working days to spare.")
        else:
            st.error(f"EXCEEDS the synthetic window by {p['overrun']:g} working days. This is a change-window overrun, not a confirmed shipment delay.")
        if result['rewiring_hours'] > 0:
            st.write(f"Production = round UP ({result['rewiring_hours']:g} person-hours / {capacity:g} person-hours per day) = {p['production']:g} whole working days.")
        st.caption('Engineering and testing days may be fractional. Rewiring is scheduled in whole working-day slots. No rewiring means zero rework days, but design, parts and testing can still require time.')
    show_plan(plan)
    st.subheader('What if parts arrive later?')
    alternative_parts = st.number_input('Alternative parts lead time after approval · working days', min_value=0.0, value=5.0, step=0.5, key='alternative_parts')
    alternate_timing = replace(timing, parts=alternative_parts)
    alternative_plan = schedule(scenario, alternate_timing)
    st.caption('Only parts lead time changes. Unknown-data switches remain in force; entering an alternative value does not mark the lead time as known.')
    def comparison_row(label, p):
        return {'Scenario': label, 'Completion day': 'Undetermined' if p['total'] is None else f"{p['total']:g}",
                'Window margin (working days)': 'Undetermined' if p['margin'] is None else f"{p['margin']:g}", 'Result': p['status']}
    st.table([comparison_row('Current inputs', plan), comparison_row('Alternative parts lead time', alternative_plan)])
    if plan['total'] is not None and alternative_plan['total'] is not None:
        difference = alternative_plan['total'] - plan['total']
        st.write(f"Changing only parts lead time shifts completion by **{difference:+g} working days**. Production and Testing move by the same amount under the sequential rule.")
    st.subheader('Compare a change before wiring begins')
    early_plan = schedule(replace(scenario, stage='Design', wired=0), timing)
    st.table([comparison_row('Before wiring · 0 wired cabinets', early_plan), comparison_row('Current production progress', plan)])
    st.caption('Both cases keep Engineering, parts, Testing and available window unchanged. This isolates rewiring effort; normal first-time assembly is not modelled.')
    st.subheader('Stress test the assumptions')
    st.write('Add an assumed delay to Engineering or Testing. This is sensitivity analysis, not a probability or confidence interval.')
    extra_days = st.number_input('Extra Engineering and Testing days · EACH', min_value=0.0, value=1.0, step=0.5, key='extra_days')
    stress_timing = replace(timing, engineering=timing.engineering + extra_days, testing=timing.testing + extra_days)
    stress_plan = schedule(scenario, stress_timing)
    st.table([comparison_row('Current inputs', plan), comparison_row('Extra days at BOTH stages', stress_plan)])
    st.subheader('Suggested Sales response for the fictional exercise')
    if plan['total'] is None:
        st.write('We cannot estimate the change schedule yet. Resolve: ' + ' '.join(plan['reasons']))
    elif plan['margin'] < 0:
        st.write('The proposed change exceeds the reserved window in this model. Explore earlier parts, additional rework capacity or a revised window before agreeing to the request.')
    else:
        st.write('The proposed change fits the reserved window under these assumptions. Check whether the assumptions and omitted order activities support the original delivery commitment; this result alone does not confirm delivery.')

report = '\n'.join([
    'CUSTOMER CHANGE REQUEST SIMULATOR — PROTOTYPE', request,
    json.dumps(asdict(scenario), indent=2),
    'SYNTHETIC TIMING INPUTS', json.dumps(asdict(timing), indent=2),
    'CURRENT CHANGE SCHEDULE', json.dumps(plan, indent=2),
    'ALTERNATIVE PARTS LEAD TIME', str(alternative_parts), json.dumps(alternative_plan, indent=2),
    'BEFORE WIRING SCHEDULE', json.dumps(early_plan, indent=2),
    'STRESS INPUTS', json.dumps(asdict(stress_timing), indent=2),
    'STRESS RESULT', json.dumps(stress_plan, indent=2),
    f"Overall impact: {result['level']} (highest-factor prototype rule)",
    f"Additional rewiring: {result['rewiring_hours']:g} person-hours",
    'Real delivery: unconfirmed. Change schedule estimated from synthetic inputs; costs and full-order duration not calculated.',
    '\nIMPACT EXPLANATIONS',
    *[f"{r['Factor']}: {r['Impact']} — {r['Reason']}" for r in result['rows']],
    '\nDEPARTMENT CHECKS (not completed approvals)',
    *[f"{d['Department']}: {d['Action']} Depends on: {d['Depends on']}. Status: {d['Status']}." for d in departments(scenario)],
    '\nCOMPARISON: Before wiring has 0 rewiring hours and impact ' + before['level'] + '.',
    'All scenario data are synthetic. Rules and timing assumptions are unvalidated; team checks are not independent validation. Sequential change-window estimates exclude full-order work, transport and costs. No interviews are required or conducted by the app.',
])
st.download_button('Download this scenario summary', report, 'customer_change_summary.txt', mime='text/plain')
st.divider()
st.caption('Synthetic-data prototype using documented, unvalidated assumptions. Team scenario testing only; no interviews. Real delivery remains unconfirmed. No trained AI model is used; the text box does not extract inputs.')
