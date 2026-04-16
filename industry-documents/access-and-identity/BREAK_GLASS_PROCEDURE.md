# Break-Glass Procedure

| Field | Value |
|---|---|
| Owner | TechNova Identity and Access |
| Classification | INTERNAL |
| Last Reviewed | 2026-04-16 |
| Next Review | 2026-10-16 |
| Version | 1.0 |

---

## 1. Purpose and Scope

Break-glass is the controlled override of normal authentication and role-based access for exceptional circumstances. It exists so that TechNova RAG remains recoverable and investigable when the regular identity path is unavailable or insufficient, without creating a permanent backdoor.

This document defines when break-glass may be invoked, who may invoke it, how the session is monitored and terminated, and what happens after. The procedure is binding: deviating from it without an incident declaration is itself a reportable security event.

Break-glass grants admin-clearance access to the TechNova RAG corpus only. It does not grant access to other TechNova systems, payment infrastructure, customer data outside RAG, or source control. Those systems have their own break-glass procedures governed by their respective owners.

---

## 2. Triggers

Break-glass may only be invoked for one of the four triggers below. Any other reason is a denial by default.

| Trigger | Definition | Typical invoker |
|---|---|---|
| **SSO outage** | The tenant's IdP (Okta, Entra ID, Google Workspace) is unreachable or returning auth failures broadly, and RAG admin access is required to operate the platform (for example, triggering a forced re-ingest, rotating a key, or reading an incident runbook from the RESTRICTED set). | Head of Engineering |
| **Active security incident** | A declared P1 security incident (severity 1 in the incident matrix) where RAG content is believed to be relevant and the investigating team requires admin-level visibility regardless of their standing role. | Security Officer |
| **Legal hold** | A formal legal hold or preservation order requires retrieval of content from the RAG corpus for discovery, and the retrieval must be performed by a named custodian outside the normal admin pool. | General Counsel |
| **Forensic investigation** | An internal investigation (fraud, insider threat, policy violation) requires admin-level RAG access for a named investigator who does not hold admin role in normal operation. | Security Officer + General Counsel (joint) |

Outages of Qdrant, Postgres, or the FastAPI backend are not break-glass triggers; those are standard on-call responses using the runbook in `OnCall_Runbook.pdf`. Break-glass is specifically for the identity and access layer.

---

## 3. Pre-authorized Break-Glass Accounts

Three break-glass accounts exist. They are permanent, unique, and never used for anything other than break-glass activation.

| Account | Holder role | Escrow |
|---|---|---|
| `bg-sec-01@technova.internal` | Security Officer | Sealed envelope in the Security Officer's office safe; digital copy in 1Password vault under `Break-Glass / bg-sec-01`, dual-custody unlock. |
| `bg-eng-01@technova.internal` | Head of Engineering | Sealed envelope in the Engineering Head's office safe; digital copy in 1Password vault under `Break-Glass / bg-eng-01`, dual-custody unlock. |
| `bg-legal-01@technova.internal` | General Counsel | Sealed envelope in the General Counsel's office safe; digital copy in 1Password vault under `Break-Glass / bg-legal-01`, dual-custody unlock. |

Each account has:

- A dedicated hardware security key (YubiKey 5 series) issued exclusively to the holder. The key is registered as the sole MFA factor; TOTP and SMS are disabled.
- A strong randomly generated password (minimum 24 characters, cryptographic random) stored only in the sealed envelope and the 1Password vault entry.
- An explicitly assigned `admin` role in the RBAC config with the break-glass flag `is_break_glass=true` set at user-record level.
- A disabled state by default (`active=false` in SCIM). Activation flips `active=true` and records the event.

Accounts are not shared between individuals. A departing holder triggers immediate rotation: new password, new hardware key, new envelope, prior credentials revoked within four hours.

---

## 4. Activation Protocol

Activation requires a two-of-three approval. The three approvers are the three account holders (Security Officer, Head of Engineering, General Counsel). An approver cannot approve their own activation request - the invoker is always separate from at least one of the two approvals.

### 4.1 Step-by-step

1. **Declare**. The invoker opens a ticket in the incident tracker with summary `Break-glass activation request`, prefix `INC-` for security and operational triggers, `LEG-` for legal. The ticket must include: trigger (one of section 2), specific RAG resource needed (document domain or query topic), expected duration, and any existing parent incident.
2. **Request approvals**. The invoker pages the other two account holders via PagerDuty escalation `break-glass-approvers`. Approvals are recorded as ticket comments with the approver's authenticated SSO identity; pager acknowledgements alone are not approvals.
3. **Two approvals received**. The ticket transitions to state `Break-glass approved`. Time-to-approve SLO is fifteen minutes from declaration to approval during business hours, thirty minutes out of hours.
4. **Credential retrieval**. The invoker opens the 1Password vault entry. Dual-custody unlock requires a second holder to approve the vault access in 1Password. (This is the operational backstop: even if the two-of-three approval is spoofed in the ticket, the vault unlock adds independent identity verification.)
5. **Login**. Invoker authenticates to `https://rag.technova.com` with the break-glass account credentials plus the hardware key. Session is minted with `is_break_glass=true`.
6. **Time-boxing**. The default activation window is four hours. At three hours and thirty minutes, a Slack alert prompts the invoker to either complete or request a renewal. Renewals require a fresh two-of-three approval and extend the window by four hours. Maximum total window is twenty-four hours; beyond that, the incident must escalate to the board-notified protocol.
7. **Scope discipline**. The invoker operates only within the scope declared in the ticket. Queries outside the declared scope are flagged at post-incident review as a procedural violation.

### 4.2 Privileged operations during activation

- **Full corpus read**. The break-glass admin role has the standard `admin` clearance - it can query all eleven documents, including RESTRICTED.
- **Cannot modify classifications**. `DOCUMENT_METADATA` changes require a separate approval chain (section 8 of `ROLE_CLEARANCE_MATRIX.md`) and are not included in break-glass scope.
- **Cannot create or delete users**. Role grants and SCIM mutations remain in the normal IAM path; break-glass is read-only at the identity layer.
- **Cannot disable audit logging**. Any attempt to suppress audit events via admin API returns 403 even for break-glass sessions.

---

## 5. Monitoring

Break-glass sessions are visible in real time across multiple channels.

- **Audit log flag**. Every audit event emitted during the session carries `actor_is_break_glass=true`. The flag is immutable and is part of the hash chain (`AUDIT_LOG_SCHEMA.md` section 3).
- **Slack alert on activation**. Channel `#security` receives an alert within thirty seconds of the `AUTH_LOGIN` event, tagging `@security-leadership` and including the ticket link.
- **Slack periodic reminder**. Every thirty minutes while the session is active, a reminder posts to `#security` with the time remaining and the activation ticket.
- **SIEM rule**. A dedicated SIEM rule watches for break-glass sessions lasting longer than four hours; this is a high-severity alert even if renewal has been approved, because extended duration is itself a signal of a larger incident.
- **Auto-expiry**. At the end of the activation window, the backend invalidates the session JWT and flips `active=false` on the SCIM record. Any further API call from the session returns 401.

No private mode exists. The invoker cannot suppress, throttle, or delay any of the above.

---

## 6. Deactivation

Deactivation is automatic at window expiry, but three explicit deactivation paths exist.

1. **Voluntary close**. The invoker completes the task and clicks Logout. The session is terminated, SCIM `active=false` is set, and the audit event `AUTH_LOGOUT` is written with `outcome=success, closed_by=invoker`.
2. **Approver revocation**. Either of the two approvers may close the session early by posting a `revoke` command in the activation ticket. The IAM service polls the ticket every thirty seconds and terminates on `revoke`.
3. **Auto-expiry**. At the end of the time-boxed window, the session terminates even if the invoker has not logged out. A grace period of sixty seconds allows in-flight requests to complete.

In all three cases:

- Session cookies are invalidated.
- Refresh token family is revoked.
- Credential rotation is scheduled for T+1 hour: the password is changed by the IAM bot, the 1Password entry is updated, and the sealed envelope is replaced at the next in-person opportunity (within five business days). Hardware keys are not rotated on every activation; they rotate annually or on compromise suspicion.
- An audit export of the session's events is prepared within four hours and attached to the activation ticket.

---

## 7. Post-Incident Review

A post-incident review is mandatory within forty-eight hours of every break-glass deactivation. This is true even for routine SSO outages that resolved without issue.

### 7.1 Participants

- The invoker.
- The two approvers.
- Security Officer (chair if not the invoker; otherwise the Head of Engineering chairs).
- Compliance Officer.
- Minute-taker from the Security team (non-participant).

### 7.2 Agenda

1. Timeline reconstruction from the audit export.
2. Scope discipline check: did the invoker stay within the declared scope?
3. Did any session activity look anomalous in retrospect?
4. Were there procedural deviations? Were approvals properly recorded?
5. Lessons learned: should any trigger definition, SLO, or control be adjusted?
6. Sign-offs: Security Officer and Compliance Officer both sign the report.

### 7.3 Archive

The review report is retained in the incident archive for seven years. A redacted version (no customer data, no RESTRICTED content, but full procedural detail) is shared with the board at the next quarterly security update.

If any procedural deviation is found, a follow-up remediation ticket is opened with a target close date of thirty days. Repeated deviations by the same invoker escalate to executive review.

---

## 8. Annual Drill

The break-glass procedure is drilled annually in Q4. The drill has two parts.

### 8.1 Tabletop

A ninety-minute scenario-based exercise with the three account holders, the Security Officer, the Compliance Officer, and a rotating set of observers. Scenarios are drawn from a library that includes SSO provider total outage, insider-threat investigation requiring admin access, court-ordered preservation, and ransomware incident with IdP compromise.

### 8.2 Live

A live activation of one break-glass account under controlled conditions. The success criteria are:

- Time from declaration to activation: under fifteen minutes.
- All three monitoring channels (audit flag, Slack activation alert, SIEM rule) fire as expected.
- Thirty-minute Slack reminders fire correctly.
- Auto-expiry at the end of the drill window succeeds without manual intervention.
- Audit trail is complete and verifiable against the hash chain.
- Post-incident review completes within forty-eight hours.

Failure of any criterion results in a remediation plan before the next release cycle.

---

## 9. Legal Considerations

Break-glass does not override legal constraints on the underlying data.

- **GDPR**. Break-glass activation does not unlock rights-of-access restrictions for data subjects. A data subject's erasure request that was processed before break-glass remains effective during break-glass; the procedure is about restoring TechNova's operational access, not about revisiting data-subject rights.
- **Cross-border access**. If the break-glass activation involves a custodian accessing data from a different jurisdiction than where the data is stored, General Counsel must be consulted and the cross-border access is documented in the activation ticket. This is most relevant for `Board_Minutes_Q4.pdf` and `Vendor_Contracts.pdf` which may contain third-country personal data.
- **Regulatory hold**. If a regulator has issued a preservation order, the invoker must acknowledge the order in the activation ticket. Content retrieved under break-glass during a preservation window is itself subject to the preservation.
- **Labour law**. In jurisdictions with strong works-council rights (Germany, France), break-glass activations that access personnel compensation (`Salary_Structure.pdf`) or security incident reports involving named employees may require works-council notification. The General Counsel maintains the jurisdiction matrix; the break-glass ticket template prompts for jurisdictional review.

Break-glass never suspends these obligations; it accelerates operational access within them.

---

## 10. Appendix A - Activation Checklist (printable)

A single-page checklist is posted in the Security Officer's office, the Engineering Head's office, and the General Counsel's office. The text below is the authoritative content.

```
[ ] Confirm trigger matches one of: SSO outage / active security incident /
    legal hold / forensic investigation.
[ ] Open activation ticket (INC-* or LEG-*) with required fields.
[ ] Page the other two account holders via PagerDuty "break-glass-approvers".
[ ] Receive two approvals as ticket comments with SSO-authenticated identity.
[ ] Unlock vault entry (dual-custody required).
[ ] Login with account credentials + hardware key.
[ ] Verify Slack #security activation alert fired.
[ ] Record start time; default window 4h; renewal requires fresh approval.
[ ] Operate only within declared scope.
[ ] At 3h30m: decide complete or renew.
[ ] On completion: Logout, confirm session end, confirm credential rotation scheduled.
[ ] Attach audit export to ticket within 4 hours.
[ ] Schedule post-incident review within 48 hours.
```

## 11. Appendix B - Vault Entry Format

1Password entries for break-glass accounts follow a fixed schema. Deviations trigger a weekly audit report.

```
Title:            Break-Glass / bg-{sec|eng|legal}-01
URL:              https://rag.technova.com/login
Username:         bg-{sec|eng|legal}-01@technova.internal
Password:         {24-char cryptographic random}
MFA:              Hardware key (YubiKey serial: {serial})
Notes:            Activation requires 2-of-3 approval.
                  See BREAK_GLASS_PROCEDURE.md section 4.
                  Rotation: password at every activation;
                  hardware key annually or on compromise.
Vault:            Break-Glass (shared: Security Officer, Head of Engineering,
                  General Counsel; dual-custody unlock required)
Tags:             break-glass, admin, rag
Custom Fields:
  Account Holder: {name}
  Envelope Location: {safe location}
  Last Rotated:    {YYYY-MM-DD}
  Last Activation: {YYYY-MM-DD or "never"}
```

## 12. Appendix C - Slack Alert Template

The Slack activation alert uses the template below. Template text is version-controlled in the `security-bot` repository.

```
:rotating_light: *BREAK-GLASS ACTIVATED*  :rotating_light:

Account:       {account_username}
Invoker:       {invoker_name} ({invoker_sub})
Trigger:       {trigger_category}
Ticket:        {ticket_url}
Approvers:     {approver_1_name}, {approver_2_name}
Activated at:  {iso_timestamp}
Expires at:    {iso_timestamp}  (4h default, max 24h with renewal)
Audit tag:     actor_is_break_glass=true

Per policy:
- Operate only within the declared scope in the ticket.
- Reminders will post every 30 min while this session is active.
- Post-incident review required within 48h of deactivation.
- Any approver may revoke by commenting `revoke` on the ticket.

cc @security-leadership @compliance-oncall
```

---

## 13. Revision History

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-04-16 | TechNova Identity & Access | Initial release |
