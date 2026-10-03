#!/usr/bin/env python3
from __future__ import annotations
from common import agent_main, base_result
AGENT = "content"
PURPOSE = "fishing/social content hooks and calendar drafts (draft only, never posts)"
def build_result(task: str, payload: dict) -> dict:
    result=base_result(AGENT, PURPOSE, task, payload)
    topic=str(payload.get('topic') or task)
    outline={'topic':topic,'hook':f'DRAFT hook for: {topic}','beats':['Local conditions or seasonal angle','One practical tip a customer can use today','Shop tie-in (bait, tackle, or guide trip)'],'call_to_action':'DRAFT CTA - operator review required before posting','channels':['facebook','in-store board']}
    result['actions'].append('Drafted a content outline locally; nothing was posted or published.')
    result['findings'].append(f'Outline prepared for topic: {topic}')
    result['next_steps'].append('Review the draft, then hand approved copy to the operator for posting.')
    result['data']['draft_outline']=outline
    return result
if __name__ == '__main__': raise SystemExit(agent_main(AGENT, PURPOSE, build_result))
