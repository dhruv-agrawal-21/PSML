# Requirement Approval System - AI Agent Instructions

## Project Overview

This is a **Django 4.2 multi-tier approval workflow system** for managing material/service requirements with role-based access control, email notifications, PDF generation, and audit logging. Requirements flow through a 4-level approval chain: Department Head → Admin → CFO → CEO.

**Key Tech Stack:** Django 4.2, MySQL 8.0+, ReportLab (PDF), Celery+Redis (async tasks), Pillow (image handling)

---

## Architecture & Critical Data Flows

### 1. **Requirement Creation → Multi-Tier Approval Chain**
- **Flow:** Department User creates Requirement → auto-assigned to their Dept Head (level 1) → on approval, auto-chain to Admin (level 2) → CFO (level 3) → CEO (level 4)
- **Key Files:** [apps/requirements/models.py](apps/requirements/models.py), [apps/requirements/views.py](apps/requirements/views.py#L15-L70), [apps/approvals/views.py](apps/approvals/views.py#L38-L100)
- **Key Model Fields:**
  - `Requirement.status` (pending/approved/rejected) - tracks overall requirement state
  - `Requirement.next_approver` - cached pointer to current approver (optimization for querying)
  - `Approval.approval_level` (1-4 enum) - tracks position in approval chain
  - `Approval.status` (pending/approved/rejected) - per-approver decision

### 2. **Email Notification Service with PDF Attachments**
- **Trigger Points:** Requirement created, approved, rejected, escalated
- **Key Service:** [apps/notifications/email_service.py](apps/notifications/email_service.py) - centralized service with methods for each workflow state
- **PDF Generation:** [apps/requirements/pdf_utils.py](apps/requirements/pdf_utils.py) - ReportLab-based PDF with requirement details + approver chain
- **Email Config:** `.env` variables (EMAIL_BACKEND, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL) - defaults to console backend for testing

### 3. **Role-Based Access Control**
- **Custom User Model:** [apps/users/models.py](apps/users/models.py) extends AbstractUser with role + department fields
- **Roles:** user (dept user), head (dept head), admin, cfo, ceo - each sees different requirement subsets
- **Role Checks in Views:** Use `user.is_department_user()`, `user.is_department_head()`, `user.is_admin_user()`, etc. helper methods
- **Permission Logic:** Department users see only own requirements; heads see dept requirements; admins/cfo/ceo see all

### 4. **Audit Trail & Compliance**
- **Model:** [apps/audit/models.py](apps/audit/models.py) - logs every action (created, approved, rejected, modified)
- **Key Pattern:** Every view that changes state creates AuditLog entry with user, action, timestamp, details
- **Example:** [apps/requirements/views.py#L44-L47](apps/requirements/views.py#L44-L47), [apps/approvals/views.py#L76-L81](apps/approvals/views.py#L76-L81)

---

## Project-Specific Conventions & Patterns

### 1. **Form Handling & Validation**
- Forms in [apps/*/forms.py](apps/requirements/forms.py) handle both validation and business logic
- Use `form.save(commit=False)` pattern to inject user/department before persisting
- Always redirect on success, re-render with form on validation error

### 2. **Email Service Integration**
- **Never** call `EmailMessage` directly in views - use `EmailNotificationService.send_*()` static methods
- All methods return boolean (success/failure) - check return value and message user appropriately
- PDF attachment is auto-generated; callers don't need to handle PDF generation separately
- Example: [apps/requirements/views.py#L63-L67](apps/requirements/views.py#L63-L67)

### 3. **PDF Generation**
- Always use `generate_requirement_pdf(requirement)` from [apps/requirements/pdf_utils.py](apps/requirements/pdf_utils.py)
- Returns PDF bytes; used by email service and download endpoints
- Includes all approvals chain, signatures, timestamps - full audit trail in PDF

### 4. **Approval Chain Routing**
- When approver approves, **automatically** create next Approval record with level+1 and find approver by role
- Role-to-level mapping: 1=head, 2=admin, 3=cfo, 4=ceo (hardcoded in [apps/approvals/views.py](apps/approvals/views.py))
- On rejection, **mark entire requirement as rejected**, do NOT create further approval records
- Always notify next approver via email with PDF attached

### 5. **Requirement Status vs Approval Status**
- **Requirement.status** (pending/approved/rejected) = final requirement state (only set when ALL approvals complete)
- **Approval.status** (pending/approved/rejected) = individual approver's decision
- Until all 4 approvals are approved, requirement.status stays pending
- On any rejection, requirement.status → rejected, further approvals blocked

### 6. **Document Upload Workflow**
- Department Head (level 1) receives PDF, doesn't need to upload signed version
- Levels 2-4 (Admin, CFO, CEO) **must** upload signed document before approving
- Check: `Document.objects.filter(approval=approval, is_signed=True).first()` before saving approval
- Model: [apps/documents/models.py](apps/documents/models.py)

---

## Developer Workflows

### Initial Setup
```bash
# 1. Configure MySQL credentials in .env (see SETUP_GUIDE.md)
# 2. Create database
mysql -u root -p -e "CREATE DATABASE requirement_approval CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 3. Run migrations (idempotent - safe to run multiple times)
python manage.py makemigrations
python manage.py migrate

# 4. Create demo users (or use Django admin)
python manage.py create_demo_users

# 5. Start server
python manage.py runserver
```

### Running Tests
- Tests in [apps/*/tests.py](apps/requirements/tests.py) - follow Django test patterns
- Run: `python manage.py test` (discovers all tests automatically)

### Debugging Email Issues
- Run [check_env.py](check_env.py) to validate EMAIL_* environment variables
- Console backend (default) prints emails to stdout; check Django debug output
- For Gmail SMTP, use app-specific passwords (not account password)

### Celery Tasks (Async Email)
- Configured in settings.py but **not yet implemented** - tasks currently synchronous
- Redis broker configured at `localhost:6379`
- Future: migrate email sends to `@shared_task` decorated functions

---

## Key Files Quick Reference

| Purpose | File | Notes |
|---------|------|-------|
| Models - Requirement lifecycle | [apps/requirements/models.py](apps/requirements/models.py) | Status choices, type choices, next_approver pointer |
| Models - Approval chain | [apps/approvals/models.py](apps/approvals/models.py) | Level 1-4, per-approver decisions |
| Views - Requirement flow | [apps/requirements/views.py](apps/requirements/views.py) | Creation, listing, role-based filtering |
| Views - Approval logic | [apps/approvals/views.py](apps/approvals/views.py) | Pending approvals, approve/reject, chain routing |
| Email service | [apps/notifications/email_service.py](apps/notifications/email_service.py) | Centralized notification hub |
| PDF generation | [apps/requirements/pdf_utils.py](apps/requirements/pdf_utils.py) | ReportLab-based PDF rendering |
| URL routing | [config/urls.py](config/urls.py) | App includes, media/static file serving |
| Settings | [config/settings.py](config/settings.py) | CustomUser auth, MySQL, email config, Celery |
| Demo data | [apps/users/management/commands/create_demo_users.py](apps/users/management/commands/create_demo_users.py) | Creates test users for each role/dept |

---

## Common Tasks & Code Patterns

### Adding a new approval notification
```python
# In apps/notifications/email_service.py, add method following pattern:
@staticmethod
def send_approval_status_notification(approval, is_approved):
    recipient_email = approval.requirement.requested_by.email
    context = {'approval': approval, 'is_approved': is_approved}
    subject = f"REQ-{approval.requirement.id}: {'Approved' if is_approved else 'Rejected'}"
    html_message = render_to_string('notifications/emails/approval_status.html', context)
    email = EmailMessage(subject=subject, body=html_message, 
                        from_email=settings.DEFAULT_FROM_EMAIL, to=[recipient_email])
    # Generate and attach PDF
    pdf_content = generate_requirement_pdf(approval.requirement)
    email.attach(f'REQ-{approval.requirement.id}.pdf', pdf_content, 'application/pdf')
    return email.send() > 0
```

### Filtering requirements by user role
```python
# In views, use pattern from apps/requirements/views.py#L85-L100:
if user.is_department_user():
    requirements = Requirement.objects.filter(requested_by=user)
elif user.is_department_head():
    requirements = Requirement.objects.filter(department=user.department)
else:  # admin, cfo, ceo
    requirements = Requirement.objects.all()
```

### Creating audit log on state change
```python
AuditLog.objects.create(
    requirement=requirement,
    user=request.user,
    action='approved',  # or 'rejected', 'created', etc.
    details=f'{request.user.get_full_name()} approved with comments: {comments}'
)
```

---

## Gotchas & Important Details

1. **MySQL Connection Issues:** Requires `mysqlclient` Python package, NOT `mysql-connector-python`. If migrations fail, verify MySQL server running and credentials correct.

2. **PDF Font Issues:** WeasyPrint + ReportLab may fail if system fonts missing. Ensure Arial/default fonts available on deployment OS.

3. **Email Testing:** Console backend useful for dev; Gmail requires app-specific password (not regular account password). Never commit real credentials to `.env`.

4. **Requirement.next_approver Stale Pointer:** This field is cached for performance but must be updated whenever approval chain advances. Always set when creating next Approval record.

5. **Approval Level Hardcoding:** Role-to-level mapping is hardcoded in [apps/approvals/views.py](apps/approvals/views.py) - if adding new approval levels, update the dictionary there.

6. **Media Files:** Document uploads (signed PDFs) go to `/media/documents/` - ensure writable on deployment and included in `.gitignore`.
