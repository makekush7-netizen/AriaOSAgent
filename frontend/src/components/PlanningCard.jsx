import React from 'react'
import { useAriaStore } from '../store/ariaStore'

export default function PlanningCard({ onApprovePlan }) {
  const { activePlan, transitionTo } = useAriaStore()

  if (!activePlan) return null

  const handleCancel = () => {
    onApprovePlan(activePlan.id, true)
    transitionTo('home')
  }

  const handleApprove = () => {
    onApprovePlan(activePlan.id, false)
    // transition will occur automatically when agent_spawn message is received, but let's set it to execution as well
    transitionTo('execution')
  }

  return (
    <div className="planning-card">
      <div className="plan-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
        <span>🎯 {activePlan.summary || 'Task Execution Plan'}</span>
      </div>

      <div className="plan-understanding">
        ARIA will automate this task by coordinating sub-agents. Please review the plan, permissions, and info gaps before executing.
      </div>

      <div className="plan-columns">
        <div className="plan-steps">
          <div className="plan-col-title">Execution Plan</div>
          {activePlan.steps?.map((step) => (
            <div key={step.id} className="plan-step">
              <div className={`step-circle ${step.status}`}></div>
              <span style={{ textDecoration: step.status === 'complete' ? 'line-through' : 'none', opacity: step.status === 'complete' ? 0.5 : 1 }}>
                {step.label}
              </span>
            </div>
          ))}
        </div>

        <div className="plan-perms">
          <div className="plan-col-title">Required Permissions</div>
          {activePlan.permissions?.map((perm, idx) => {
            const isWarning = perm.toLowerCase().includes('write') || perm.toLowerCase().includes('execute') || perm.toLowerCase().includes('submit');
            return (
              <div key={idx} className="perm-row">
                <span style={{ color: isWarning ? 'var(--accent-coral)' : 'var(--accent-green)' }}>
                  {isWarning ? '⚠' : '✅'}
                </span>
                <span>{perm}</span>
              </div>
            )
          })}
        </div>
      </div>

      {activePlan.info_gaps && activePlan.info_gaps.length > 0 && (
        <div className="plan-info-gap">
          <span style={{ color: 'var(--accent-coral)', marginRight: '6px' }}>⚠ Info Gaps Detected:</span>
          <span>We are missing {activePlan.info_gaps.join(', ')}. ARIA will ask for these via Human-in-the-Loop prompts during execution.</span>
        </div>
      )}

      <div className="plan-actions">
        <button className="btn-cancel" onClick={handleCancel}>Cancel</button>
        <button className="btn-approve" onClick={handleApprove}>✓ Approve & Run</button>
      </div>
    </div>
  )
}
