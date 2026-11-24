"""Coverage and persistence checks for the 20-order synthetic test set."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from decision import assess,DECISIONS
from model import validate_order
from repository import initialise,get_order,update_order,list_orders
from streamlit.testing.v1 import AppTest
from unittest.mock import patch
import os

BASE=Path(__file__).resolve().parents[1]
ORDERS=json.loads((BASE/'data/synthetic_orders.json').read_text())
CAT=json.loads((BASE/'data/change_catalog.json').read_text())
PROFILES={p['id']:p for p in CAT['profiles']}


def evaluate(o):
    return assess(o,PROFILES[o['default_change']],CAT,affected=o['quantity'],assembled_affected=o['assembled'],
                  allow_extension=o['default_allow_extension'],max_extra_days=o['default_max_extra_days'],
                  added_quantity=10,price_mode=o['default_price_mode'],custom_description=o.get('custom_assessment',{}).get('description',''))


class OrderSetTests(unittest.TestCase):
    def test_unique_valid_varied_records(self):
        self.assertEqual([o['order_id'] for o in ORDERS],[f'ORD-{i:03}' for i in range(1,21)])
        for o in ORDERS:validate_order(o,CAT)
        for field in ('quantity','assembled','unit_price','unit_base_cost','assembly_capacity_per_day','original_delivery_date','order_date'):
            self.assertGreater(len({o[field] for o in ORDERS}),1,field)

    def test_default_examples_cover_five_outcomes_and_pending(self):
        expected={7:0,8:1,9:1,10:2,11:3,12:4,13:1,14:4,15:4,17:1,18:1,19:1}
        for number,outcome in expected.items():
            with self.subTest(number=number):self.assertEqual(evaluate(ORDERS[number-1])['decision'],DECISIONS[outcome])
        with self.assertRaisesRegex(ValueError,'lead time'):evaluate(ORDERS[15])
        self.assertEqual(evaluate(ORDERS[19])['status'],'pending')
        self.assertEqual(evaluate(ORDERS[16])['new_quantity'],110)
        self.assertAlmostEqual(evaluate(ORDERS[16])['profit_margin_percent'],100*(2200-1300)/2200,places=4)
        unsupported=deepcopy(ORDERS[17]);unsupported['default_change']='PROTECTION'
        self.assertEqual(evaluate(unsupported)['decision'],DECISIONS[4])

    def test_expansion_does_not_overwrite_existing_edits(self):
        with tempfile.TemporaryDirectory() as temp:
            old_seed=Path(temp)/'old.json';old_seed.write_text(json.dumps(ORDERS[:6]))
            db=Path(temp)/'production.sqlite'
            initialise(db,old_seed)
            order,rev=get_order(db,'ORD-001');order['assembled']=31
            update_order(db,order,rev)
            initialise(db,BASE/'data/synthetic_orders.json')
            self.assertEqual(len(list_orders(db)),20)
            order,rev=get_order(db,'ORD-001')
            self.assertEqual((order['assembled'],rev),(31,2))
            self.assertEqual(get_order(db,'ORD-020')[1],1)

    def test_ui_loads_order_defaults_and_assessment_states(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'SIMULATOR_DATA_DIR':temp}):
            app=AppTest.from_file(str(BASE/'app.py'),default_timeout=20).run()
            self.assertEqual(app.selectbox(key='sales_order_id').options,[f'ORD-{i:03}' for i in range(1,21)])
            for key,expected in [('ORD-007',DECISIONS[0]),('ORD-010',DECISIONS[2]),('ORD-019',DECISIONS[1])]:
                app.selectbox(key='sales_order_id').set_value(key).run()
                app.button(key='evaluate').click().run()
                self.assertFalse(app.exception,key)
                messages=[m.value for m in app.success]+[m.value for m in app.warning]
                self.assertIn(expected,messages)
            app.selectbox(key='sales_order_id').set_value('ORD-016').run()
            self.assertTrue(app.button(key='evaluate').disabled)
            app.selectbox(key='sales_order_id').set_value('ORD-020').run()
            app.button(key='evaluate').click().run()
            self.assertIn('Production assessment needed',app.warning[0].value)
            app.radio(key='workspace').set_value('Production dashboard').run()
            self.assertEqual(len(app.selectbox(key='production_order').options),20)
            self.assertFalse(app.exception)

if __name__=='__main__':unittest.main()
