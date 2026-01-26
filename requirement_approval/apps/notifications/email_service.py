"""
Email notification service for Requirement Approval System.
Handles sending emails with PDF attachments at each approval stage.
"""
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from apps.notifications.models import EmailLog
from apps.requirements.pdf_utils import generate_requirement_pdf
import logging

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Centralized service for sending approval workflow emails"""
    
    @staticmethod
    def send_requirement_created_notification(requirement):
        """
        Send notification to department head when requirement is created.
        Attaches the generated requirement PDF.
        """
        try:
            # Get department head email
            recipient_email = requirement.next_approver.email
            recipient_name = requirement.next_approver.get_full_name()
            
            # Prepare context for email template
            context = {
                'requirement': requirement,
                'recipient_name': recipient_name,
                'requester_name': requirement.requested_by.get_full_name(),
                'department': requirement.get_department_display(),
                'priority': requirement.get_priority_display(),
            }
            
            # Render email content
            subject = f'New Requirement #{requirement.id} - Approval Required'
            html_message = render_to_string('notifications/emails/requirement_created.html', context)
            plain_message = strip_tags(html_message)
            
            # Create email
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            email.content_subtype = 'html'
            
            # Generate and attach PDF
            pdf_buffer = generate_requirement_pdf(requirement)
            email.attach(
                f'Requirement_{requirement.id}.pdf',
                pdf_buffer.getvalue(),
                'application/pdf'
            )
            
            # Send email
            email.send(fail_silently=False)
            
            # Log email
            EmailLog.objects.create(
                recipient=recipient_email,
                subject=subject,
                template_type='requirement_created',
                requirement=requirement,
                status='sent'
            )
            
            logger.info(f"✓ Email sent successfully to {recipient_email} for REQ-{requirement.id}")
            print(f"✓ EMAIL SENT: To {recipient_email}, Subject: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to send requirement created email: {str(e)}")
            print(f"✗ EMAIL FAILED: {str(e)}")
            # Log failed email
            EmailLog.objects.create(
                recipient=recipient_email if 'recipient_email' in locals() else 'unknown',
                subject=subject if 'subject' in locals() else 'Requirement Created',
                template_type='requirement_created',
                requirement=requirement,
                status='failed'
            )
            return False
    
    @staticmethod
    def send_approval_request_notification(requirement, approval, signed_document=None):
        """
        Send notification to next approver in the chain.
        Attaches the requirement PDF and any signed documents from previous approvers.
        """
        try:
            # Get next approver email
            recipient_email = requirement.next_approver.email
            recipient_name = requirement.next_approver.get_full_name()
            
            # Get previous approver info
            previous_approver = approval.approver.get_full_name()
            
            # Prepare context
            context = {
                'requirement': requirement,
                'recipient_name': recipient_name,
                'previous_approver': previous_approver,
                'approval_level': approval.get_approval_level_display(),
                'comments': approval.comments,
                'department': requirement.get_department_display(),
                'priority': requirement.get_priority_display(),
            }
            
            # Render email
            subject = f'Requirement #{requirement.id} - Approval Required (Level {approval.approval_level + 1})'
            html_message = render_to_string('notifications/emails/approval_request.html', context)
            
            # Create email
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            email.content_subtype = 'html'
            
            # Attach original requirement PDF
            pdf_buffer = generate_requirement_pdf(requirement)
            email.attach(
                f'Requirement_{requirement.id}.pdf',
                pdf_buffer.getvalue(),
                'application/pdf'
            )
            
            # Attach signed document if provided
            if signed_document:
                with signed_document.file.open('rb') as f:
                    email.attach(
                        signed_document.file_name,
                        f.read(),
                        'application/pdf'
                    )
            
            # Attach additional document from approval if provided
            if approval.additional_document:
                with approval.additional_document.open('rb') as f:
                    doc_name = f'Approval_Additional_Document_{approval.id}.pdf'
                    email.attach(doc_name, f.read(), 'application/pdf')
                    logger.info(f"✓ Additional document attached from approval {approval.id}")
            
            # Send email
            email.send(fail_silently=False)
            
            # Log email
            EmailLog.objects.create(
                recipient=recipient_email,
                subject=subject,
                template_type='approval_request',
                requirement=requirement,
                status='sent'
            )
            
            logger.info(f"Approval request email sent to {recipient_email} for REQ-{requirement.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send approval request email: {str(e)}")
            EmailLog.objects.create(
                recipient=recipient_email if 'recipient_email' in locals() else 'unknown',
                subject=subject if 'subject' in locals() else 'Approval Request',
                template_type='approval_request',
                requirement=requirement,
                status='failed'
            )
            return False
    
    @staticmethod
    def send_final_approval_notification(requirement):
        """
        Send notification to original requester when requirement is fully approved.
        """
        try:
            recipient_email = requirement.requested_by.email
            recipient_name = requirement.requested_by.get_full_name()
            
            context = {
                'requirement': requirement,
                'recipient_name': recipient_name,
                'department': requirement.get_department_display(),
            }
            
            subject = f'Requirement #{requirement.id} - APPROVED'
            html_message = render_to_string('notifications/emails/requirement_approved.html', context)
            
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            email.content_subtype = 'html'
            
            # Attach final PDF with all approvals
            pdf_buffer = generate_requirement_pdf(requirement)
            email.attach(
                f'Requirement_{requirement.id}_APPROVED.pdf',
                pdf_buffer.getvalue(),
                'application/pdf'
            )
            
            email.send(fail_silently=False)
            
            EmailLog.objects.create(
                recipient=recipient_email,
                subject=subject,
                template_type='requirement_approved',
                requirement=requirement,
                status='sent'
            )
            
            logger.info(f"Final approval email sent to {recipient_email} for REQ-{requirement.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send final approval email: {str(e)}")
            EmailLog.objects.create(
                recipient=recipient_email if 'recipient_email' in locals() else 'unknown',
                subject=subject if 'subject' in locals() else 'Requirement Approved',
                template_type='requirement_approved',
                requirement=requirement,
                status='failed'
            )
            return False
    
    @staticmethod
    def send_rejection_notification(requirement, approval):
        """
        Send notification to original requester when requirement is rejected.
        """
        try:
            recipient_email = requirement.requested_by.email
            recipient_name = requirement.requested_by.get_full_name()
            
            context = {
                'requirement': requirement,
                'recipient_name': recipient_name,
                'rejected_by': approval.approver.get_full_name(),
                'rejection_comments': approval.comments,
                'department': requirement.get_department_display(),
            }
            
            subject = f'Requirement #{requirement.id} - REJECTED'
            html_message = render_to_string('notifications/emails/requirement_rejected.html', context)
            
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            email.content_subtype = 'html'
            
            # Attach PDF
            pdf_buffer = generate_requirement_pdf(requirement)
            email.attach(
                f'Requirement_{requirement.id}_REJECTED.pdf',
                pdf_buffer.getvalue(),
                'application/pdf'
            )
            
            email.send(fail_silently=False)
            
            EmailLog.objects.create(
                recipient=recipient_email,
                subject=subject,
                template_type='requirement_rejected',
                requirement=requirement,
                status='sent'
            )
            
            logger.info(f"Rejection email sent to {recipient_email} for REQ-{requirement.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send rejection email: {str(e)}")
            EmailLog.objects.create(
                recipient=recipient_email if 'recipient_email' in locals() else 'unknown',
                subject=subject if 'subject' in locals() else 'Requirement Rejected',
                template_type='requirement_rejected',
                requirement=requirement,
                status='failed'
            )
            return False
    @staticmethod
    def send_modification_request_notification(requirement, approval):
        """
        Send notification to requirement creator when approver requests modifications.
        Includes approver comments and optional file.
        """
        try:
            recipient_email = requirement.requested_by.email
            recipient_name = requirement.requested_by.get_full_name()
            
            # Prepare context for email template
            context = {
                'requirement': requirement,
                'recipient_name': recipient_name,
                'approver_name': approval.approver.get_full_name(),
                'approver_level': approval.get_approval_level_display(),
                'comments': approval.comments,
                'has_file': bool(approval.additional_document),
            }
            
            # Render email content
            subject = f'Modification Requested for Requirement #{requirement.id}'
            html_message = render_to_string('notifications/emails/modification_request.html', context)
            plain_message = strip_tags(html_message)
            
            # Create email
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            
            # Attach additional document if present
            if approval.additional_document:
                try:
                    email.attach_file(approval.additional_document.path)
                except:
                    pass
            
            email.send()
            
            # Log email sent
            EmailLog.objects.create(
                recipient=recipient_email,
                subject=subject,
                template_type='modification_request',
                requirement=requirement,
                status='sent'
            )
            
            logger.info(f"Modification request email sent to {recipient_email} for REQ-{requirement.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send modification request email: {str(e)}")
            EmailLog.objects.create(
                recipient=recipient_email if 'recipient_email' in locals() else 'unknown',
                subject=subject if 'subject' in locals() else 'Modification Requested',
                template_type='modification_request',
                requirement=requirement,
                status='failed'
            )
            return False