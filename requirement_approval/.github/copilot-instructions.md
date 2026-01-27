# Requirement Approval System - AI Agent Instructions

## Project Overview

This is a **Django 4.2 multi-tier approval workflow system** for material/service requirements with 4-level approval chain: Department Head (level 1) → Admin (level 2) → CFO (level 3) → CEO (level 4). Core features: role-based access control, email notifications with PDF attachments, automatic chain routing, modification requests, signed document uploads, and full audit logging.

**Key Tech Stack:** Django 4.2, MySQL 8.0+ (required, not SQLite), ReportLab + WeasyPrint (PDF), Celery+Redis (configured but async not yet implemented), Pillow (image handling)

**Database:** MySQL only. Custom `CustomUser` auth model with role/department fields. 6 apps: users, requirements, approvals, documents, notifications, audit.

---

## Architecture & Critical Data Flows

### 1. **Requirement Creation → Multi-Tier Approval Chain**
- **Linear Flow:** `pending` → Level 1 (Head) → Level 2 (Admin) → Level 3 (CFO) → Level 4 (CEO) → `approved` OR any rejection → `rejected`
- **Auto-routing:** When approver approves, next Approval record created with level+1; next approver looked up by role mapping
- **Rejection Blocks Chain:** If any level rejects, requirement.status → `rejected`, no further approvals created
- **Status Semantics:** `Requirement.status` = final state (only changed on full completion/rejection); `Approval.status` = individual approver decision
- **Requirement.next_approver:** Performance optimization - cached pointer to current pending approver; MUST update when routing to next level
- **Modification Flow:** Separate from main chain - approver can request modifications (creates `request_modification` Approval), requirement goes to `modification_requested`, requester resubmits, re-enters same approval level

### 2. **Email Notification Service with PDF Attachments**
- **Centralized Service:** [apps/notifications/email_service.py](apps/notifications/email_service.py) has static methods: `send_requirement_created_notification()`, `send_approval_notification()`, etc.
- **PDF Always Attached:** Every email includes ReportLab PDF with requirement details + full approval chain. Use `generate_requirement_pdf(requirement)` from [apps/requirements/pdf_utils.py](apps/requirements/pdf_utils.py)
- **Pattern:** Never call `EmailMessage` directly in views - always use `EmailNotificationService.send_*()` methods; they return boolean, check result before user message
- **Config:** `.env` has EMAIL_BACKEND (console default for dev), EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL. Run `check_env.py` to validate
- **Logging:** All sent/failed emails logged to `EmailLog` model for audit trail

### 3. **Role-Based Access Control**- CustomUser extends AbstractUser with `role` (user/head/admin/cfo/ceo) + `department` (finance/marketing/sales/technical/executive)
- **Role Helper Methods:** `is_department_user()`, `is_department_head()`, `is_admin_user()`, `is_cfo()`, `is_ceo()` on CustomUser instance
- **View Pattern:** Check role early; redirect if insufficient; then filter querysets:
  - **user:** can see only own requirements
  - **head:** can see department's requirements + approve at level 1
  - **admin/cfo/ceo:** can see all requirements + approve at their respective level
- **Approval Level ↔ Role Mapping:** Hardcoded in [apps/apprimmutable log entries: requirement, user, action (created/approved/rejected/modified/request_modification), details, timestamp
- **Pattern:** Every state-changing view must create AuditLog: `AuditLog.objects.create(requirement=req, user=request.user, action='action_name', details='...')`
- **Query Examples:** `AuditLog.objects.filter(requirement=req).order_by('timestamp')` for audit trail; logs all decisions + who made them + when
- **Requirement.was_modified Flag:** Set to True when requirement resubmitted after modification request; `last_modified_date` tracks submission timestamp
### 4. **Audit Trail & Compliance**
- **Model:** [apps/audit/models.py](apps/audit/models.py) - logs every action (created, approved, rejected, modified)
- **Key Pattern:** Every view that changes state creates AuditLog entry with user, action, timestamp, details
- **Example:** [apps/requirements/views.py#L44-L47](apps/requirements/views.py#L44-L47), [apps/approvals/views.py#L76-L81](apps/approvals/views.py#L76-L81)

---

## Project-Specific Conventions & Patterns

### 1. **Form Handling & Validation** 
- Forms in [apps/*/forms.py](apps/requirements/forms.py) include validation; use `form.save(commit=False)` to inject user/department context before persist
- Always post-redirect-get: success → `redirect()`, validation error → re-render with form errors shown

### 2. **View Permission Check Pattern**
```python
# START of every approval/modify view
@login_required(login_url='users:login')
def approve_view(request, approval_id):
    approval = get_object_or_404(Approval, id=approval_id)
    if approval.approver != request.user:
        messages.error(request, 'You cannot approve this.')
        return redirect('dashboard')
    # ... rest of logic
```

### 3. **Approval Chain Routing - Exact Pattern**
When approver approves:
```python
# 1. Save approval with status='approved'
approval.status = 'approved'
approval.approved_date = timezone.now()
approval.save()

# 2. Check if final approval (level 4)
if approval.approval_level == 4:
    approval.requirement.status = 'approved'
    approval.requirement.save()
    EmailNotificationService.send_approval_final_notification(approval.requirement)
else:
    # 3. Auto-create next approval
    next_level = approval.approval_level + 1
    level_to_role = {1: 'head', 2: 'admin', 3: 'cfo', 4: 'ceo'}
    next_approver = CustomUser.objects.get(role=level_to_role[next_level], ...)
    
    Approval.objects.create(
        requirement=approval.requirement,
        approver=next_approver,
        approval_level=next_level,
        status='pending'
    )
    
    approval.requirement.next_approver = next_approver
    approval.requirement.save()
    EmailNotificationService.send_requirement_created_notification(approval.requirement)

# 4. Create audit log
AuditLog.objects.create(requirement=approval.requirement, user=request.user, 
                       action='approved', details=f'Level {approval.approval_level} approved')
```

### 4. **Rejection Pattern - Blocks Entire Chain**
```python
approval.status = 'rejected'
approval.comments = request.POST.get('comments', '')
approval.save()

approval.requirement.status = 'rejected'
approval.requirement.save()

# Delete any pending approvals at higher levels
Approval.objects.filter(requirement=approval.requirement, 
                       status='pending', 
                       approval_level__gt=approval.approval_level).delete()

AuditLog.objects.create(requirement=approval.requirement, user=request.user,
                       action='rejected', details=f'Rejected at level {approval.approval_level}')
```

### 5. **Modification Request Pattern**
```python
# Approver requests modification instead of approving/rejecting
approval.status = 'request_modification'
approval.comments = request.POST.get('comments', '')
approval.save()

approval.requirement.status = 'modification_requested'
approval.requirement.save()

# Notify requester; they resubmit and requirement re-enters at SAME level
EmailNotificationService.send_modification_request_notification(approval)
```

### 6. **Requirement.next_approver Caching**
- Updated whenever approval chain advances or requirement resubmitted after modification
- Used for fast dashboard queries: `Requirement.objects.filter(next_approver=user)`
- **Must update when routing to next level** OR when modification resubmitted (reset to current approver)

### 7. **PDF Generation & Email Attachment**
- Always call: `pdf_bytes = generate_requirement_pdf(requirement)` - returns bytes
- Attach to email: `email.attach(f'REQ-{requirement.id}.pdf', pdf_bytes, 'application/pdf')`
- PDF includes all Approval records in chain, comments, signatures field (for manual sign)

### 8. **Document Upload (Signed PDFs)**
- Levels 2-4 (Admin, CFO, CEO) **must** upload signed document before status='approved'
- Check: `if not Document.objects.filter(approval=approval, is_signed=True).exists(): raise ValidationError`
- Level 1 (Head) does NOT need to upload; only receives PDF to review
- Model: [apps/documents/models.py](apps/documents/models.py) with `document_file`, `is_signed` fields

---

## Developer Workflows

### Initial Setup (First Time)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file in project root with MySQL credentials
# Copy template values from SETUP_GUIDE.md

# 3. Verify MySQL server running
mysql -u root -p -e "SHOW DATABASES;"

# 4. Create database
mysql -u root -p -e "CREATE DATABASE requirement_approval CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 5. Run all migrations (idempotent - safe to repeat)
python manage.py migrate

# 6. Create demo users (optional, for testing)
python manage.py create_demo_users

# 7. Start dev server
python manage.py runserver
```

### Verification Commands
```bash
# Validate email configuration
python check_env.py

# Run migrations and show SQL
python manage.py migrate --plan

# Create superuser for Django admin
python manage.py createsuperuser
```

### Testing
- Test files: [apps/*/tests.py](apps/requirements/tests.py)
- Run all: `python manage.py test`
- Run specific app: `python manage.py test apps.requirements`
- Tests auto-discover and use Django test database (not production MySQL)

### Debugging Email Issues
- Run [check_env.py](check_env.py) to validate EMAIL_* environment variables
- Console backend (default) prints emails to stdout; check Django debug output
- For Gmail SMTP, use app-specific passwords (not account password)

---

## Data Model Quick Reference

| Model | Key Fields | Purpose |
|-------|-----------|---------|
| `CustomUser` | role, department, is_active | Auth; role+dept determine approval routing |
| `Requirement` | requested_by, status, next_approver, was_modified | Tracks requirement lifecycle; status={pending/modification_requested/approved/rejected} |
| `Approval` | requirement, approver, approval_level, status, comments | Per-approver decision; level 1-4; status={pending/approved/rejected/request_modification} |
| `Document` | approval, document_file, is_signed | Signed PDFs uploaded by levels 2-4 |
| `AuditLog` | requirement, user, action, details, timestamp | Immutable audit trail |
| `EmailLog` | requirement, recipient, status, sent_at | Email delivery tracking |

---

## Common Implementation Patterns

### Pattern: List Requirements Filtered by Role
```python
from apps.requirements.models import Requirement

def get_requirements_for_user(user):
    if user.is_department_user():
        return Requirement.objects.filter(requested_by=user)
    elif user.is_department_head():
        return Requirement.objects.filter(department=user.department)
    else:  # admin, cfo, ceo - see all
        return Requirement.objects.all()
```

### Pattern: Get Pending Approvals for Dashboard
```python
pending = Approval.objects.filter(
    approver=request.user,
    status='pending'
).select_related('requirement', 'approver').order_by('-timestamp')

# For each pending approval, check if signed doc required
for approval in pending:
    needs_doc = approval.approval_level > 1
    has_doc = Document.objects.filter(approval=approval, is_signed=True).exists()
```

### Pattern: Send Email After Action
```python
# After approving/rejecting/creating
from apps.notifications.email_service import EmailNotificationService

success = EmailNotificationService.send_requirement_created_notification(requirement)
if success:
    messages.success(request, f'Requirement created and email sent to {requirement.next_approver.email}')
else:
    messages.warning(request, 'Requirement created but email failed. Check EMAIL_BACKEND config.')
```

---

## Gotchas & Common Issues

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| **Migration fails** | MySQL not running OR credentials wrong | Check SETUP_GUIDE.md; run `python check_env.py` |
| **PDF attachment missing in email** | `generate_requirement_pdf()` not called | Use EmailNotificationService methods; they auto-attach |
| **Approval chain stuck** | Requirement.next_approver not updated after approval | Always set after creating next Approval record |
| **Email to console (not sending)** | EMAIL_BACKEND='console.EmailBackend' in dev | Check settings.py; use console for dev, SMTP for prod |
| **Signed document upload fails** | Document.approval FK wrong OR is_signed not set | Pass `approval=approval` to Document.save(); set flag on form |
| **"You are not the approver" error** | Approval.approver != request.user | Check Approval lookup; ensure fetching correct approval record |
| **Modification request not showing** | Status='request_modification' but requirement not marked | Always set `requirement.status='modification_requested'` when creating request_modification Approval |
| **Permission denied in views** | No role check before filtering | Add role check BEFORE query: `if not user.can_approve(): return redirect()` |
