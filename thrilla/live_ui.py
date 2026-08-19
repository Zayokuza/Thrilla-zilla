"""Pure foreground renderer for Stage-5 live work."""
from dataclasses import dataclass
from enum import Enum
class ControlAction(str,Enum): HOLD='hold'; COMMUNICATE='communicate'; CONTINUE_FULL='continue_full'; BACK='back'
_MAP={'1':ControlAction.HOLD,'2':ControlAction.COMMUNICATE,'3':ControlAction.CONTINUE_FULL,'0':ControlAction.BACK}
CONTROL_FOOTER='1.Hold  2.Communicate  3.Continue full  0.Back'
def control_action_for(value):
    try: return _MAP[str(value).strip()]
    except KeyError as e: raise ValueError('unknown live-work control') from e
@dataclass(frozen=True)
class ChatLine: role:str; text:str
def _clip(value,width):
    x=' '.join(str(value).split())
    if len(x)<=width: return x
    return x[:max(0,width-1)]+'…'
class LiveWorkRenderer:
    def _work(self,s):
        if s is None: return ['No active job']
        out=[f"State: {getattr(s.state,'value',s.state)}",f'Goal: {s.goal}',f'Step: {s.current_step or "-"}']
        if s.total_steps: out.append(f'Progress: {s.completed_steps}/{s.total_steps}')
        elif s.progress: out.append(f'Progress: {s.progress*100:.0f}%')
        if s.evidence_count: out.append(f'Evidence: {s.evidence_count}')
        if s.last_action: out.append(f'Last: {s.last_action}')
        if s.next_action: out.append(f'Next: {s.next_action}')
        if s.error: out.append(f'Error: {s.error}')
        return out
    def render(self,conversation,snapshot=None,width=120):
        width=max(40,int(width)); chat=[f'{x.role}: {_clip(x.text,max(10,width-12))}' for x in conversation] or ['(no conversation yet)']; work=self._work(snapshot)
        if width<88:
            return '\n'.join(['CONVERSATION','─'*min(width,60),*chat,'','ACTIVE WORK','─'*min(width,60),*work,'',CONTROL_FOOTER])
        gap=' │ '; left=max(30,int(width*.56)); right=width-left-len(gap); rows=max(len(chat),len(work)); out=['CONVERSATION'.ljust(left)+gap+'ACTIVE WORK'.ljust(right),'─'*left+'─┼─'+'─'*right]
        for i in range(rows):
            a=_clip(chat[i],left) if i<len(chat) else ''; b=_clip(work[i],right) if i<len(work) else ''; out.append(a.ljust(left)+gap+b)
        out += ['',CONTROL_FOOTER]; return '\n'.join(out)
