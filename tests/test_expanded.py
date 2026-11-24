from copy import deepcopy
from datetime import date
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from decision import assess, DECISIONS, PRICE_MODES, snapshot_signature
from model import add_working_days

BASE=Path(__file__).resolve().parents[1]
CAT=json.loads((BASE/'data/change_catalog.json').read_text())
ORDERS=json.loads((BASE/'data/synthetic_orders.json').read_text())
PROFILES={p['id']:p for p in CAT['profiles']}


def run(key='SENSORS_REMOTE',order=None,**kwargs):
    o=deepcopy(order or ORDERS[0])
    args=dict(affected=o['quantity'],assembled_affected=o['assembled'],allow_extension=True,max_extra_days=100,max_extra_charge=1000000)
    args.update(kwargs)
    return assess(o,PROFILES[key],CAT,**args)


class ExpandedTests(unittest.TestCase):
    def test_all_known_types(self):
        for key,p in PROFILES.items():
            if key in ('OTHER','EARLIER'):continue
            with self.subTest(key=key):
                r=run(key)
                self.assertEqual(r['status'],'ready')
                self.assertEqual(len(r['options']),5)
                self.assertGreaterEqual(r['total_extra_cost'],0)
                self.assertIsNotNone(r['revised_completion_date'])

    def test_five_decisions(self):
        self.assertEqual(run(price_mode=PRICE_MODES[0])['decision'],DECISIONS[0])
        self.assertEqual(run()['decision'],DECISIONS[1])
        self.assertEqual(run(order=ORDERS[1],price_mode=PRICE_MODES[0])['decision'],DECISIONS[2])
        self.assertEqual(run(order=ORDERS[1])['decision'],DECISIONS[3])
        self.assertEqual(run(order=ORDERS[1],allow_extension=False)['decision'],DECISIONS[4])

    def test_profit_and_price(self):
        r=run()
        self.assertAlmostEqual(r['proposed_price'],110012.5)
        self.assertAlmostEqual(r['estimated_profit'],40000)
        self.assertAlmostEqual(r['new_total_cost'],70012.5)
        r=run(price_mode=PRICE_MODES[2])
        self.assertGreaterEqual(r['profit_margin_percent'],40)
        self.assertLess(r['profit_margin_percent'],40.001)
        r=run(price_mode=PRICE_MODES[0])
        self.assertGreater(r['estimated_profit'],0)
        self.assertLess(r['profit_change'],0)

    def test_budget_and_margin(self):
        self.assertEqual(run(allow_price_change=False)['decision'],DECISIONS[4])
        self.assertEqual(run(max_extra_charge=100)['decision'],DECISIONS[4])
        self.assertEqual(run(price_mode=PRICE_MODES[0],minimum_margin=35)['decision'],DECISIONS[4])
        r=run('QUANTITY',added_quantity=100,price_mode=PRICE_MODES[0])
        self.assertLess(r['estimated_profit'],0)
        self.assertEqual(r['decision'],DECISIONS[4])
        for bad in (-1,100,float('nan')):
            with self.assertRaises(ValueError):run(minimum_margin=bad)

    def test_quantity_has_complete_cost_once(self):
        r=run('QUANTITY',added_quantity=10)
        self.assertEqual(r['new_quantity'],60)
        self.assertEqual(r['extra_install_hours'],40)
        self.assertEqual(r['extra_test_hours'],5)
        self.assertEqual(r['rework_hours'],0)
        self.assertAlmostEqual(r['total_extra_cost'],12000)
        self.assertAlmostEqual(r['new_total_cost'],72000)
        self.assertEqual(r['original_assembly_hours_remaining'],80)
        self.assertEqual(r['baseline_days'],11)
        self.assertEqual(r['revised_days'],15)
        r=run('QUANTITY',added_quantity=100)
        self.assertEqual(r['new_quantity'],150)
        self.assertEqual(r['material_requirements'][0]['Shortage'],40)
        self.assertEqual(r['material_wait_days'],5)

    def test_earlier_delivery(self):
        o=deepcopy(ORDERS[0])
        target=add_working_days(o['snapshot_date'],15)
        r=run('EARLIER',requested_date=target)
        self.assertEqual(r['total_extra_cost'],0)
        self.assertEqual(r['revised_days'],11)
        self.assertEqual(r['proposed_delivery'],target)
        self.assertEqual(r['decision'],DECISIONS[2])
        tight=add_working_days(o['snapshot_date'],5)
        self.assertEqual(run('EARLIER',requested_date=tight,allow_extension=False)['decision'],DECISIONS[4])
        r=run('EARLIER',requested_date=tight,max_extra_days=6)
        self.assertEqual(r['extra_days_needed'],6)
        self.assertEqual(r['decision'],DECISIONS[4])
        for invalid in ('2026-11-01','2026-11-21',o['original_delivery_date']):
            with self.assertRaises(ValueError):run('EARLIER',requested_date=invalid)

    def test_custom_pending_and_stale(self):
        o=deepcopy(ORDERS[0])
        self.assertEqual(run('OTHER',order=o)['status'],'pending')
        a=dict(complete=True,description='Add labels',affected=50,assembled_affected=30,feasible=True,
               setup_hours=2,installation_hours=10,rework_hours=3,testing_hours=5,material_cost=100,parts_wait_days=2)
        a['snapshot']=snapshot_signature(o)
        o['custom_assessment']=a
        r=run('OTHER',order=o,custom_description='Add labels')
        self.assertEqual(r['status'],'ready')
        self.assertAlmostEqual(r['total_extra_cost'],895)
        self.assertEqual(r['material_wait_days'],2)
        self.assertEqual(run('OTHER',order=o,custom_description='Bigger cabinet')['status'],'pending')
        self.assertEqual(run('OTHER',order=o,custom_description='Add labels',affected=40)['status'],'pending')
        o['assembly_capacity_per_day']=5
        self.assertEqual(run('OTHER',order=o,custom_description='Add labels')['status'],'pending')
        o['custom_assessment']['snapshot']=snapshot_signature(o)
        o['custom_assessment']['feasible']=False
        o['supported_change_ids'].append('OTHER')
        o['custom_assessment']['snapshot']=snapshot_signature(o)
        self.assertEqual(run('OTHER',order=o,custom_description='Add labels')['decision'],DECISIONS[4])

    def test_original_order_date_validation(self):
        o=deepcopy(ORDERS[0])
        o['order_date']=add_working_days(o['snapshot_date'],1)
        with self.assertRaisesRegex(ValueError,'Original order date'):
            run(order=o)
        o['order_date']=o['snapshot_date']
        self.assertEqual(run(order=o)['status'],'ready')

    def test_stock_support_capacity_and_no_mutation(self):
        o=deepcopy(ORDERS[0]);before=deepcopy(o)
        run('REPLACE',order=o)
        self.assertEqual(o,before)
        o['supported_change_ids'].remove('LAYOUT')
        self.assertEqual(run('LAYOUT',order=o)['decision'],DECISIONS[4])
        o=deepcopy(ORDERS[0]);o['materials']['replacement'].update(available=0,can_replenish=False)
        r=run('REPLACE',order=o)
        self.assertEqual(r['decision'],DECISIONS[4]);self.assertIsNone(r['proposed_delivery'])
        o=deepcopy(ORDERS[0]);o['assembly_capacity_per_day']=0
        self.assertEqual(run('QUANTITY',order=o)['decision'],DECISIONS[4])


class ExpandedUiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'SIMULATOR_DATA_DIR':self.temp.name});self.env.start()
    def tearDown(self):
        self.env.stop();self.temp.cleanup()
    def test_request_inputs_and_stale_results(self):
        app=AppTest.from_file(str(BASE/'app.py'),default_timeout=15).run()
        for key in ('SENSORS','REMOTE','REPLACE','LAYOUT','CONNECTION','PROTECTION','QUANTITY','EARLIER','OTHER'):
            app.selectbox(key='change_id').set_value(key).run()
            app.button(key='evaluate').click().run()
            self.assertFalse(app.exception,key)
        self.assertIn('Production assessment needed',app.warning[0].value)
        app.selectbox(key='change_id').set_value('SENSORS').run()
        app.button(key='evaluate').click().run()
        self.assertTrue(app.warning)
        app.checkbox(key='allow_price').set_value(False).run()
        self.assertNotIn('Estimated order profit',[m.label for m in app.metric])
        app.button(key='evaluate').click().run()
        self.assertEqual(app.error[0].value,DECISIONS[4])

    def test_earlier_disables_extension_and_preserves_other_requests(self):
        app=AppTest.from_file(str(BASE/'app.py'),default_timeout=15).run()
        app.checkbox(key='allow_extension').set_value(True).run()
        app.selectbox(key='change_id').set_value('EARLIER').run()
        self.assertTrue(app.checkbox(key='earlier_no_extension').disabled)
        self.assertFalse(app.checkbox(key='earlier_no_extension').value)
        self.assertTrue(app.number_input(key='earlier_no_extra').disabled)
        app.date_input(key='earlier_date').set_value(date(2026,11,20)).run()
        app.button(key='evaluate').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.error[0].value,DECISIONS[4])
        app.selectbox(key='change_id').set_value('SENSORS').run()
        self.assertFalse(app.checkbox(key='allow_extension').disabled)

    def test_custom_saved_then_loaded_and_invalidated(self):
        app=AppTest.from_file(str(BASE/'app.py'),default_timeout=15).run()
        app.radio(key='workspace').set_value('Production dashboard').run()
        app.checkbox(key='prodedit_custom_complete').set_value(True)
        app.checkbox(key='prodedit_custom_feasible').set_value(True)
        app.text_area(key='prodedit_custom_description').set_value('Add labels')
        app.number_input(key='prodedit_custom_installation_hours').set_value(10)
        next(b for b in app.button if b.label=='Save Production data').click().run()
        self.assertFalse(app.exception)
        app.radio(key='workspace').set_value('Sales simulator').run()
        app.selectbox(key='change_id').set_value('OTHER').run()
        app.button(key='evaluate').click().run()
        self.assertFalse(app.exception)
        self.assertNotIn('Production assessment needed',' '.join(w.value for w in app.warning))
        app.text_area(key='custom_description').set_value('Different request').run()
        app.button(key='evaluate').click().run()
        self.assertIn('Production assessment needed',app.warning[0].value)

if __name__=='__main__':unittest.main()
