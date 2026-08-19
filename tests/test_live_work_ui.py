import unittest
from thrilla.jobs import JobSnapshot, JobState
from thrilla.live_ui import ChatLine, ControlAction, LiveWorkRenderer, control_action_for
class LiveWorkUiTests(unittest.TestCase):
    def snap(self): return JobSnapshot(job_id='j',kind='research',goal='Research Thrilla',state=JobState.RUNNING,current_step='research.fetch',completed_steps=2,total_steps=5,progress=.4,last_action='Fetched source',next_action='Build evidence',evidence_count=2)
    def test_exact_controls(self):
        self.assertIs(control_action_for('1'),ControlAction.HOLD); self.assertIs(control_action_for('2'),ControlAction.COMMUNICATE); self.assertIs(control_action_for('3'),ControlAction.CONTINUE_FULL); self.assertIs(control_action_for('0'),ControlAction.BACK)
        self.assertIn('1.Hold  2.Communicate  3.Continue full  0.Back',LiveWorkRenderer().render([ChatLine('you','hello')],self.snap(),width=120))
    def test_wide_split(self):
        first=LiveWorkRenderer().render([ChatLine('you','conversation only')],self.snap(),width=120).splitlines()[0]
        self.assertIn('CONVERSATION',first); self.assertIn('ACTIVE WORK',first)
    def test_narrow_keeps_sections_separate(self):
        r=LiveWorkRenderer().render([ChatLine('thrilla','answer')],self.snap(),width=60)
        self.assertIn('CONVERSATION',r); self.assertIn('ACTIVE WORK',r); self.assertLess(r.index('CONVERSATION'),r.index('ACTIVE WORK'))
    def test_back_is_navigation_action(self): self.assertEqual(ControlAction.BACK.value,'back')
