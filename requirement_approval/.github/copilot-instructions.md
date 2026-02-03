# Requirement Approval System - AI Agent Instructions

## Project Overview

**Django 4.2 multi-tier approval workflow** for material/service requirements with 4-level approval chain: Department Head (L1) → Admin (L2) → CFO (L3) → CEO (L4). 

**Key features:** Role-based access control (5 roles: user/head/admin/cfo/ceo across 5 departments), email notifications with PDF attachments, automatic chain routing, modification requests, signed document uploads, complete audit logging.

**Tech Stack:** Django 4.2, MySQL 8.0+ (required—no SQLite), ReportLab/WeasyPrint (PDF generation), Celery+Redis (configured but async tasks not yet implemented), Pillow (image handling).

**6 Apps:** `users` (auth), `requirements` (submission), `approvals` (chain logic), `documents` (signed PDFs), `notifications` (email service), `audit` (compliance logging).

---

## Critical Architecture: Requirement → Approval Chain

```
Flow: Requirement created (status='pending') 
  → Level 1 Approval created (approver = dept head)
  → On approval: Level 2 Approval auto-created, next_approver updated
  → Repeat L2→L3→L4
  → Final approval (L4): requirement.status='approved'
  
OR at any level:
  → rejection → requirement.status='rejected' + all pending approvals deleted
  → request_modification → requirement.status='modification_requested'
                          + requester resubmits → re-enters at SAME level
```

**Key Fields:**
- `Requirement.status`: Immutable "final state" (only changed end-of-chain or on rejection)
- `Requirement.next_approver`: Cached FK to current pending approver (updated with each routing)
- `Approval.status`: Individual decision (pending/approved/rejected/request_modification)
- `Approval.approval_level`: 1-4 hardcoded; auto-routing uses level+1

**Why this matters:** Queries like `Requirement.objects.filter(next_approver=user)` are fast; `next_approver` is THE optimization for dashboards. Always update it.

---

## Email & PDF Pattern (No Direct EmailMessage Calls)

**Service:** [apps/notifications/email_service.py](apps/notifications/email_service.py) — static methods only (`send_requirement_created_notification()`, `send_approval_notification()`, `send_modification_request_notification()`, `send_rejection_notification()`, `send_approval_final_notification()`).

**Pattern:**
```python
# NEVER call EmailMessage directly
# ALWAYS use EmailNotificationService
from apps.notifications.email_service import EmailNotificationService

EmailNotificationService.send_requirement_created_notification(requirement)
```

**PDF in Every Email:**
```python
from apps.requirements.pdf_utils import generate_requirement_pdf

pdf_buffer = generate_requirement_pdf(requirement)
email.attach(f'REQ-{requirement.id}.pdf', pdf_buffer.getvalue(), 'application/pdf')
```

PDF includes all Approval records, comments, empty signature fields for printing/scanning.

**Config:** `.env` keys: `EMAIL_BACKEND` (dev: console; prod: smtp), `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`. Run `python check_env.py` before deploying.

**Logging:** Every send attempt (success/fail) logged to EmailLog model.

---

## Role-Based Access Control (RBAC)

**Roles:** [CustomUser.ROLE_CHOICES](apps/users/models.py#L6) — user, head, admin, cfo, ceo.
**Departments:** finance, marketing, sales, technical, executive.

**Helper Methods on CustomUser:**
```python
user.is_department_user()    # role == 'user'
user.is_department_head()    # role == 'head'
user.is_admin_user()         # role == 'admin'
user.is_cfo_user()           # role == 'cfo'
user.is_ceo_user()           # role == 'ceo'
```

**View Access Pattern:**
```python
@login_required(login_url='users:login')
def approve_view(request, approval_id):
    approval = get_object_or_404(Approval, id=approval_id)
    # CRITICAL: Verify user is the assigned approver
    if approval.approver != request.user:
        messages.error(request, 'Not your approval.')
        return redirect('dashboard')
    # Then proceed with approval logic
```

**Approval Level ↔ Role Mapping:**
```python
level_to_role = {1: 'head', 2: 'admin', 3: 'cfo', 4: 'ceo'}
role_to_level = {'head': 1, 'admin': 2, 'cfo': 3, 'ceo': 4}
```

---

## Document Upload Constraint (Levels 2-4 Only)

Levels 2, 3, 4 (Admin, CFO, CEO) MUST upload signed document before approving.
Level 1 (Head) does NOT upload—only reviews.

**Check in approval view:**
```python
if approval.approval_level >= 2:
    if not Document.objects.filter(approval=approval, is_signed=True).exists():
        messages.error(request, 'Upload signed document first.')
        return redirect('document_upload', approval_id=approval.id)
```

[Document model](apps/documents/models.py): `document_file`, `is_signed` boolean, `uploaded_by`, `uploaded_date`.

---

## Approval Chain Auto-Routing (Exact Implementation)

When approver submits approval (code location: [apps/approvals/views.py](apps/approvals/views.py)):

```python
approval.status = 'approved'
approval.approved_date = timezone.now()
approval.save()

AuditLog.objects.create(requirement=approval.requirement, user=request.user, 
                       action='approved', details=f'Level {approval.approval_level} approved')

# CRITICAL: Check if final level
if approval.approval_level == 4:
    approval.requirement.status = 'approved'
    approval.requirement.save()
    EmailNotificationService.send_approval_final_notification(approval.requirement)
    return redirect('requirements:detail_requirement', pk=approval.requirement.id)

# Auto-create next approval
next_level = approval.approval_level + 1
level_to_role = {1: 'head', 2: 'admin', 3: 'cfo', 4: 'ceo'}
next_role = level_to_role[next_level]

# Lookup next approver by role (assumes one person per role across company)
next_approver = CustomUser.objects.get(role=next_role)

Approval.objects.create(
    requirement=approval.requirement,
    approver=next_approver,
    approval_level=next_level,
    status='pending'
)

# UPDATE CACHE
approval.requirement.next_approver = next_approver
approval.requirement.save()

# Notify next approver
EmailNotificationService.send_requirement_created_notification(approval.requirement)
```

---

## Rejection Pattern (Cascades Down)

```python
approval.status = 'rejected'
approval.comments = request.POST.get('comments', '')
approval.save()

approval.requirement.status = 'rejected'
approval.requirement.save()

# Delete all pending approvals at higher levels
Approval.objects.filter(requirement=approval.requirement, 
                       status='pending', 
                       approval_level__gt=approval.approval_level).delete()

AuditLog.objects.create(requirement=approval.requirement, user=request.user,
                       action='rejected', details=f'Rejected at level {approval.approval_level}: {approval.comments}')

EmailNotificationService.send_rejection_notification(approval)
```

---

## Modification Request Pattern

```python
approval.status = 'request_modification'
approval.comments = request.POST.get('modification_comments', '')
approval.save()

approval.requirement.status = 'modification_requested'
approval.requirement.modification_description = request.POST.get('modification_details', '')
approval.requirement.save()

AuditLog.objects.create(requirement=approval.requirement, user=request.user,
                       action='request_modification', details=f'{approval.comments}')

EmailNotificationService.send_modification_request_notification(approval)
```

When requester resubmits:
```python
requirement.status = 'pending'
requirement.was_modified = True
requirement.last_modified_date = timezone.now()
requirement.next_approver = Approval.objects.get(requirement=requirement, 
                                                 status='pending').approver  # Reset to same level
requirement.save()

AuditLog.objects.create(requirement=requirement, user=request.user, action='resubmitted_after_modification')
EmailNotificationService.send_requirement_created_notification(requirement)
```

---

## Form & View Pattern

**Forms:** [apps/*/forms.py](apps/requirements/forms.py) — use `form.save(commit=False)` to inject user/department before persist.

```python
def create_requirement(request):
    if request.method == 'POST':
        form = RequirementForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.requested_by = request.user
            req.department = request.user.department
            req.save()
            
            # Create L1 approval
            dept_head = CustomUser.objects.get(role='head', department=req.department)
            Approval.objects.create(requirement=req, approver=dept_head, approval_level=1, status='pending')
            req.next_approver = dept_head
            req.save()
            
            AuditLog.objects.create(requirement=req, user=request.user, action='created')
            EmailNotificationService.send_requirement_created_notification(req)
            
            messages.success(request, 'Requirement created.')
            return redirect('requirements:list_requirements')
    else:
        form = RequirementForm()
    return render(request, 'requirements/create_requirement.html', {'form': form})
```

**Always:** Post-redirect-get pattern. On error, re-render with form errors.

---

## Audit Logging (Every State Change)

[AuditLog model](apps/audit/models.py): `requirement`, `user`, `action` (created/approved/rejected/modified/request_modification/resubmitted_after_modification), `details`, `timestamp`.

**Pattern:** Every view that changes requirement/approval state MUST log:
```python
AuditLog.objects.create(
    requirement=requirement,
    user=request.user,
    action='action_name',
    details='Human-readable context'
)
```

Query entire audit trail: `AuditLog.objects.filter(requirement=req).order_by('timestamp')`.

---

## Developer Setup & Commands

**First time:**
```bash
pip install -r requirements.txt
# Create .env (see SETUP_GUIDE.md for template)
python manage.py migrate
python manage.py create_demo_users  # Optional test data
python manage.py runserver
```

**Verify setup:**
```bash
python check_env.py              # Email config validation
python manage.py test            # Run all tests (uses test DB, not MySQL)
python manage.py test apps.approvals  # Single app
```

**Debug email locally:**
- Default `.env` uses `EMAIL_BACKEND=console`; emails print to Django console
- Check stdout for `[Email]` lines
- For SMTP testing, update `.env` with Gmail credentials (app-specific password required)

**Create superuser:**
```bash
python manage.py createsuperuser  # Access /admin/
```

---

## File Structure Reference

| Path | Purpose |
|------|---------|
| [apps/users/models.py](apps/users/models.py) | CustomUser, roles/departments |
| [apps/requirements/models.py](apps/requirements/models.py) | Requirement + next_approver cache |
| [apps/approvals/models.py](apps/approvals/models.py) | Approval chain, levels 1-4 |
| [apps/documents/models.py](apps/documents/models.py) | Document uploads, is_signed flag |
| [apps/notifications/email_service.py](apps/notifications/email_service.py) | Central email service |
| [apps/requirements/pdf_utils.py](apps/requirements/pdf_utils.py) | PDF generation |
| [apps/audit/models.py](apps/audit/models.py) | AuditLog compliance |
| [config/settings.py](config/settings.py) | Django settings, 6 apps, email config from .env |
