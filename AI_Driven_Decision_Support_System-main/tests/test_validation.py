"""Cross-field checks: proposals, customer limits, dates and required Production facts."""
from copy import deepcopy
from datetime import date
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from decision import assess, DECISIONS, PRICE_MODES
from model import validate_order

BASE=Path(__file__).resolve().parents[1]
CAT=json.loads((BASE/'data/change_catalog.json').read_text())
ORDER=json.loads((BASE/'data/synthetic_orders.json').read_text())[0]
PROFILE=CAT['profiles'][0]


def check(order=None,**kwargs):
    args=dict(affected=50,assembled_affected=30,allow_extension=True,max_extra_days=10,
              price_mode=PRICE_MODES[3],negotiated_price=120000,max_extra_charge=20000)
    args.update(kwargs)
    return assess(deepcopy(order or ORDER),PROFILE,CAT,**args)


class ValidationTests(unittest.TestCase):
    def test_discount_is_blocked_even_when_profitable(self):
        with self.assertRaisesRegex(ValueError,'below the original'):
            check(negotiated_price=95000)
        self.assertEqual(check(negotiated_price=100000)['decision'],DECISIONS[0])

    def test_customer_budget_and_permission_have_exact_boundary(self):
        self.assertEqual(check()['decision'],DECISIONS[1])
        self.assertEqual(check(max_extra_charge=19999.99)['decision'],DECISIONS[4])
        self.assertEqual(check(allow_price_change=False,max_extra_charge=999999)['decision'],DECISIONS[4])
        self.assertEqual(check(negotiated_price=100000,allow_price_change=False)['decision'],DECISIONS[0])

    def test_date_permission_ignores_stale_limit(self):
        o=deepcopy(ORDER);o['original_delivery_date']='2026-12-17'
        self.assertEqual(check(order=o,allow_extension=False,max_extra_days=100)['decision'],DECISIONS[4])

    def test_quantities_capacity_materials_and_profit_gate_acceptance(self):
        for fields in [dict(affected=51),dict(assembled_affected=31),dict(affected=0)]:
            with self.assertRaises(ValueError):check(**fields)
        o=deepcopy(ORDER);o['test_capacity_per_day']=0
        self.assertEqual(check(order=o)['decision'],DECISIONS[4])
        o=deepcopy(ORDER);o['materials']['module'].update(available=0,can_replenish=False)
        self.assertEqual(check(order=o)['decision'],DECISIONS[4])
        self.assertEqual(check(negotiated_price=100000,minimum_margin=40)['decision'],DECISIONS[4])

    def test_unknown_required_lead_does_not_become_zero(self):
        o=deepcopy(ORDER);o['materials']['module'].update(available=0,can_replenish=True,lead_days=None)
        with self.assertRaisesRegex(ValueError,'lead time'):check(order=o)

    def test_dates_and_invalid_source_assumptions(self):
        for field,value in [('order_date','2026-11-20'),('snapshot_date','invalid'),('original_delivery_date','2026-11-01'),('unit_price',0),('assembly_capacity_per_day',-1)]:
            o=deepcopy(ORDER);o[field]=value
            with self.assertRaises(ValueError):validate_order(o,CAT)
        c=deepcopy(CAT);c['materials']['sensor']['unit_cost']=-1
        with self.assertRaises(ValueError):validate_order(ORDER,c)
        for value in (float('nan'),float('inf'),-1):
            with self.assertRaises(ValueError):check(negotiated_price=value)


class ValidationUiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'SIMULATOR_DATA_DIR':self.temp.name});self.env.start()
    def tearDown(self):
        self.env.stop();self.temp.cleanup()
    def app(self):return AppTest.from_file(str(BASE/'app.py'),default_timeout=15).run()

    def test_manual_price_minimum_and_controls_follow_price(self):
        app=self.app()
        app.selectbox(key='price_mode').set_value(PRICE_MODES[3]).run()
        self.assertEqual(app.number_input(key='negotiated').min,100000)
        self.assertTrue(app.checkbox(key='no_price_increase').disabled)
        self.assertFalse(app.checkbox(key='no_price_increase').value)
        self.assertEqual(app.number_input(key='no_price_extra').value,0)
        app.number_input(key='negotiated').set_value(120000).run()
        self.assertFalse(app.checkbox(key='allow_price').disabled)
        app.number_input(key='max_charge').set_value(15000).run()
        app.button(key='evaluate').click().run()
        self.assertEqual(app.error[0].value,DECISIONS[4])
        app.number_input(key='max_charge').set_value(20000).run()
        app.button(key='evaluate').click().run()
        self.assertEqual(app.warning[0].value,DECISIONS[1])
        app.number_input(key='negotiated').set_value(100000).run()
        self.assertTrue(app.checkbox(key='no_price_increase').disabled)
        self.assertNotIn('Estimated order profit',[m.label for m in app.metric])
        self.assertFalse(app.exception)

    def test_inactive_controls_are_zero_and_invalid_dates_block_evaluation(self):
        app=self.app()
        app.checkbox(key='allow_price').set_value(False).run()
        self.assertTrue(app.number_input(key='no_price_extra').disabled)
        self.assertEqual(app.number_input(key='no_price_extra').value,0)
        self.assertTrue(app.number_input(key='no_date_extra').disabled)
        self.assertEqual(app.number_input(key='no_date_extra').value,0)
        app.selectbox(key='price_mode').set_value(PRICE_MODES[0]).run()
        self.assertTrue(app.checkbox(key='no_price_increase').disabled)
        app.selectbox(key='change_id').set_value('EARLIER').run()
        app.date_input(key='earlier_date').set_value(date(2026,12,31)).run()
        self.assertTrue(app.button(key='evaluate').disabled)
        self.assertFalse(app.exception)

    def test_required_unknown_lead_blocks_preview_and_save_retains_unknown(self):
        app=self.app()
        app.radio(key='workspace').set_value('Production dashboard').run()
        app.number_input(key='prodedit_stock_module').set_value(0)
        app.checkbox(key='prodedit_known_module').set_value(False)
        next(b for b in app.button if b.label=='Save Production data').click().run()
        app.radio(key='workspace').set_value('Sales simulator').run()
        self.assertTrue(app.button(key='evaluate').disabled)
        self.assertIn('lead time',' '.join(e.value for e in app.error))
        self.assertFalse(app.exception)

if __name__=='__main__':unittest.main()
