#!/usr/bin/env python3
from __future__ import annotations
from common import agent_main, base_result
AGENT = "email"
PURPOSE = "email triage policy and drafts (draft only, never sends)"
def build_result(task: str, payload: dict) -> dict:
    result=base_result(AGENT, PURPOSE, task, payload)
    subject=str(payload.get('subject') or f'DRAFT: {task}')
    draft={'subject':subject,'body_outline':['Greeting','Status summary or answer','Requested action or reply-by date','Sign-off'],'recipient':'operator review required before addressing','send_policy':'NEVER auto-send; the operator sends manually'}
    result['actions'].append('Drafted email content locally; nothing was sent.')
    result['findings'].append('Email lane is draft/plan only by policy.')
    result['next_steps'].append('Operator reviews the draft, fills in specifics, and sends from their own mail client.')
    result['data']['email_draft']=draft
    return result
if __name__ == '__main__': raise SystemExit(agent_main(AGENT, PURPOSE, build_result))
