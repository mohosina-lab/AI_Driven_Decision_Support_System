from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from decision import DECISIONS
from model import ACCEPT, REVISE, REJECT, add_working_days, simulate, working_days_between
from repository import RevisionConflict, get_order, initialise, list_orders, update_order
from streamlit.testing.v1 import AppTest

BASE = Path(__file__).resolve().parents[1]
CATALOG = json.loads((BASE / 'data/change_catalog.json').read_text())
ORDERS = json.loads((BASE / 'data/synthetic_orders.json').read_text())
PROFILE = CATALOG['profiles'][0]


def run_order(order, **overrides):
    args = dict(affected=order['quantity'], assembled_affected=order['assembled'],
                allow_extension=order['default_allow_extension'], max_extra_days=order['default_max_extra_days'])
    args.update(overrides)
    return simulate(order, PROFILE, CATALOG, **args)


class ModelTests(unittest.TestCase):
    def test_six_examples_cover_decisions(self):
        self.assertEqual([run_order(o)['decision'] for o in ORDERS[:6]], [ACCEPT, REVISE, REJECT, ACCEPT, REJECT, REVISE])

    def test_full_remaining_work_and_cost(self):
        r = run_order(ORDERS[0])
        self.assertEqual((r['baseline_days'], r['revised_days'], r['available_days']), (11, 29, 30))
        self.assertEqual((r['rework_hours'], r['extra_install_hours'], r['extra_test_hours'], r['setup_hours']), (30, 87.5, 37.5, 20))
        self.assertEqual(r['total_extra_hours'], 175)
        self.assertEqual(r['additional_material_cost'], 3000)
        self.assertEqual(r['total_extra_cost'], 10012.5)
        self.assertEqual(r['margin_if_cost_absorbed'], 29987.5)
        self.assertEqual(len(r['options']), 3)
        self.assertEqual(r['options'][2]['Extra cost (€)'], 0)

    def test_extension_constraints(self):
        order = ORDERS[1]
        self.assertEqual(run_order(order)['extra_days_needed'], 9)
        self.assertEqual(run_order(order, allow_extension=False)['decision'], REJECT)
        self.assertEqual(run_order(order, max_extra_days=8)['decision'], REJECT)
        self.assertEqual(run_order(order, max_extra_days=9)['decision'], REVISE)

    def test_shortage_propagation(self):
        order = deepcopy(ORDERS[0])
        order['materials']['module']['available'] = 0
        order['materials']['sensor']['available'] = 0
        r = run_order(order)
        self.assertEqual(r['material_wait_days'], 5)
        self.assertEqual(r['revised_days'], 34)
        self.assertEqual(r['material_requirements'][1]['Shortage'], 50)

    def test_known_blockers(self):
        r = run_order(ORDERS[4])
        self.assertEqual(r['decision'], REJECT)
        self.assertTrue(r['blockers'])
        self.assertIsNone(r['revised_completion_date'])
        self.assertEqual(r['revised_timeline'], [])
        order = deepcopy(ORDERS[0])
        order['supported_change_ids'] = []
        self.assertEqual(run_order(order)['decision'], REJECT)

    def test_missing_lead_time(self):
        order = deepcopy(ORDERS[0])
        order['materials']['module'].update(available=0, lead_days=None)
        with self.assertRaises(ValueError):
            run_order(order)

    def test_zero_capacity(self):
        order = deepcopy(ORDERS[0])
        order['assembly_capacity_per_day'] = 0
        self.assertEqual(run_order(order)['decision'], REJECT)
        order['assembled'] = order['quantity']
        self.assertEqual(run_order(order)['baseline_days'], 3)
        self.assertEqual(run_order(order)['decision'], REJECT)

    def test_subsets(self):
        with self.assertRaises(ValueError):
            run_order(ORDERS[0], affected=50, assembled_affected=0)
        with self.assertRaises(ValueError):
            run_order(ORDERS[0], affected=51)
        r = run_order(ORDERS[0], affected=10, assembled_affected=0)
        self.assertEqual(r['rework_hours'], 0)
        self.assertEqual(r['extra_install_hours'], 17.5)

    def test_no_record_mutation(self):
        order = deepcopy(ORDERS[0])
        before = deepcopy(order)
        run_order(order)
        self.assertEqual(order, before)

    def test_weekdays_and_exact_deadline(self):
        self.assertEqual(add_working_days('2026-11-20', 1), '2026-11-23')
        self.assertEqual(working_days_between('2026-11-20', '2026-11-23'), 1)
        order = deepcopy(ORDERS[0])
        order['original_delivery_date'] = add_working_days(order['snapshot_date'], 29)
        self.assertEqual(run_order(order)['decision'], ACCEPT)
        self.assertEqual(run_order(order)['spare_days'], 0)


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'db.sqlite'
        initialise(self.path, BASE / 'data/synthetic_orders.json')

    def test_seed_preserves_saved_values(self):
        self.assertEqual(len(list_orders(self.path)), 20)
        self.assertIsNone(get_order(self.path, 'BAD'))
        order, rev = get_order(self.path, 'ORD-001')
        order['assembly_capacity_per_day'] = 5
        update_order(self.path, order, rev)
        initialise(self.path, BASE / 'data/synthetic_orders.json')
        self.assertEqual(get_order(self.path, 'ORD-001')[0]['assembly_capacity_per_day'], 5)

    def test_stale_update_rejected(self):
        order, rev = get_order(self.path, 'ORD-001')
        update_order(self.path, order, rev)
        order['assembled'] = 10
        with self.assertRaises(RevisionConflict):
            update_order(self.path, order, rev)
        self.assertEqual(get_order(self.path, 'ORD-001')[0]['assembled'], 30)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        environment = patch.dict(os.environ, {'SIMULATOR_DATA_DIR': self.temp.name})
        environment.start()
        self.addCleanup(environment.stop)
        self.path = Path(self.temp.name) / 'production.sqlite'

    def app(self):
        app = AppTest.from_file(str(BASE / 'app.py')).run(timeout=20)
        self.assertFalse(app.exception)
        return app

    def test_order_lookup_three_decisions(self):
        app = self.app()
        app.button(key='evaluate').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.warning[0].value, DECISIONS[1])
        app.selectbox(key='sales_order_id').set_value('ORD-002').run()
        app.button(key='evaluate').click().run()
        self.assertEqual(app.warning[0].value, DECISIONS[3])
        app.selectbox(key='sales_order_id').set_value('ORD-003').run()
        app.button(key='evaluate').click().run()
        self.assertEqual(app.error[0].value, DECISIONS[4])
        self.assertFalse(app.exception)

    def test_bad_order_stale_result(self):
        app = self.app()
        app.button(key='evaluate').click().run()
        app.number_input(key='affected').set_value(40).run()
        self.assertFalse(app.exception)
        self.assertFalse(app.success)
        self.assertFalse(app.warning)
        app.selectbox(key='sales_order_id').set_value('ORD-007').run()
        self.assertFalse(app.error)
        self.assertNotIn('Estimated order profit', [m.label for m in app.metric])
        self.assertFalse(app.exception)

    def test_production_save_autoloads_sales(self):
        app = self.app()
        app.radio(key='workspace').set_value('Production dashboard').run()
        self.assertFalse(app.exception)
        app.number_input(key='prodedit_capacity').set_value(5)
        next(b for b in app.button if b.label == 'Save Production data').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(get_order(self.path, 'ORD-001')[0]['assembly_capacity_per_day'], 5)
        app.radio(key='workspace').set_value('Sales simulator').run()
        app.button(key='evaluate').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.error[0].value, DECISIONS[4])
        self.assertEqual(app.session_state['sales_loaded_record'], ('ORD-001', 2))

    def test_partial_change_and_blocker(self):
        app = self.app()
        app.number_input(key='affected').set_value(10).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key='assembled_affected').max, 10)
        app.button(key='evaluate').click().run()
        self.assertFalse(app.exception)
        app.selectbox(key='sales_order_id').set_value('ORD-005').run()
        app.button(key='evaluate').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.error[0].value, DECISIONS[4])
        self.assertIn('shortage', '\n'.join(m.value for m in app.markdown).lower())

    def test_assumptions_view(self):
        app = self.app()
        app.radio(key='workspace').set_value('Model assumptions').run()
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
