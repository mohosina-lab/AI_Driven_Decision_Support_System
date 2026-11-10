from pathlib import Path
from dataclasses import replace
import unittest
from model import Scenario, Timing, evaluate, schedule
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'app.py')

class ModelTests(unittest.TestCase):
    def test_example_and_comparison(self):
        s = Scenario()
        self.assertEqual(evaluate(s)['rewiring_hours'], 30)
        self.assertEqual(evaluate(replace(s, stage='Design', wired=0))['rewiring_hours'], 0)

    def test_low_and_critical_factor(self):
        s = Scenario(stage='Design', wired=0)
        self.assertEqual(evaluate(s)['level'], 'LOW')
        self.assertEqual(evaluate(replace(s, availability='Unavailable'))['level'], 'HIGH')
        self.assertEqual(evaluate(replace(s, deadline='Fixed'))['level'], 'HIGH')

    def test_invalid_quantities(self):
        for s in [Scenario(affected=51), Scenario(wired=51), Scenario(stage='Design'), Scenario(hours=-1)]:
            with self.assertRaises(ValueError):
                evaluate(s)

    def test_fractional_and_zero_effort(self):
        self.assertEqual(evaluate(Scenario(wired=3, hours=0.25))['rewiring_hours'], 0.75)
        self.assertEqual(evaluate(Scenario(hours=0))['rewiring_hours'], 0)

class InterfaceTests(unittest.TestCase):
    def test_default_and_rerun(self):
        at = AppTest.from_file(APP).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[1].value, '30 person-hours')
        self.assertEqual(len(at.tabs), 6)
        at.selectbox(key='availability').set_value('Unavailable').run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[0].value, 'HIGH')
        at.number_input(key='wired').set_value(0)
        at.selectbox(key='stage').set_value('Design')
        at.selectbox(key='availability').set_value('Available').run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[0].value, 'LOW')
        self.assertEqual(at.metric[1].value, '0 person-hours')

    def test_invalid_input_and_recovery(self):
        at = AppTest.from_file(APP).run()
        at.number_input(key='affected').set_value(51).run()
        self.assertFalse(at.exception)
        self.assertTrue(at.error)
        self.assertEqual(len(at.metric), 0)
        at.number_input(key='affected').set_value(50).run()
        self.assertGreaterEqual(len(at.metric), 3)
        at.text_area(key='request').set_value(' ').run()
        self.assertTrue(at.error)
        self.assertEqual(len(at.metric), 0)


class ScheduleTests(unittest.TestCase):
    def test_default_chain_and_parts_propagation(self):
        s, t = Scenario(), Timing()
        base = schedule(s, t)
        later = schedule(s, replace(t, parts=5))
        self.assertEqual((base['total'], base['production'], base['margin']), (7, 3, 1))
        self.assertEqual((later['total'], later['overrun']), (10, 2))
        self.assertEqual(base['timeline'][2]['Start day'], 3)
        self.assertEqual(later['timeline'][2]['Start day'], 6)
        self.assertEqual(later['timeline'][3]['End day'], 10)

    def test_unknowns_and_zero_capacity(self):
        for t in [Timing(parts_known=False), Timing(capacity_known=False), Timing(testing_known=False), Timing(capacity=0)]:
            p = schedule(Scenario(), t)
            self.assertIsNone(p['total'])
            self.assertEqual(p['status'], 'UNDETERMINED')
            self.assertTrue(p['reasons'])
        self.assertEqual(schedule(Scenario(wired=0), Timing(capacity=0))['total'], 4)
        self.assertEqual(schedule(Scenario(wired=0), Timing(capacity_known=False))['total'], 4)

    def test_rounding_boundaries_and_stress(self):
        s = Scenario(wired=1, hours=0.25)
        self.assertEqual(schedule(s, Timing())['production'], 1)
        self.assertEqual(schedule(Scenario(), Timing(window=7))['margin'], 0)
        self.assertEqual(schedule(Scenario(), Timing(window=0))['overrun'], 7)
        self.assertEqual(schedule(Scenario(), Timing(engineering=2, testing=2))['total'], 9)
        self.assertEqual(schedule(Scenario(), Timing(capacity=5))['production'], 6)
        for t in [Timing(parts=-1), Timing(capacity=float('nan')), Timing(window=float('inf'))]:
            with self.assertRaises(ValueError):
                schedule(Scenario(), t)

class ScheduleInterfaceTests(unittest.TestCase):
    def test_timing_interactions_and_unknown_recovery(self):
        at = AppTest.from_file(APP).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[2].value, 'FITS WINDOW')
        self.assertEqual(at.metric[3].value, 'Day 7')
        at.number_input(key='parts_days').set_value(5).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[2].value, 'EXCEEDS WINDOW')
        self.assertEqual(at.metric[3].value, 'Day 10')
        at.checkbox(key='parts_known').uncheck().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[2].value, 'UNDETERMINED')
        self.assertEqual(len(at.metric), 3)
        at.checkbox(key='parts_known').check()
        at.number_input(key='capacity').set_value(0).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[2].value, 'UNDETERMINED')
        at.number_input(key='wired').set_value(0).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[3].value, 'Day 7')

if __name__ == '__main__':
    unittest.main()
