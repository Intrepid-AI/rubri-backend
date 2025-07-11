import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import os

from app.celery_app import celery_app
from app.db_ops.db_config import load_app_config
from app.logger import get_logger

logger = get_logger(__name__)

def get_email_config():
    """Get email configuration from app config and environment"""
    app_config = load_app_config()
    email_config = app_config.get('email', {})
    
    return {
        'smtp_server': os.getenv('SMTP_SERVER', email_config.get('smtp_server', 'smtp.gmail.com')),
        'smtp_port': int(os.getenv('SMTP_PORT', email_config.get('smtp_port', 587))),
        'smtp_username': os.getenv('SMTP_USERNAME', email_config.get('smtp_username', '')),
        'smtp_password': os.getenv('SMTP_PASSWORD', email_config.get('smtp_password', '')),
        'from_email': os.getenv('FROM_EMAIL', email_config.get('from_email', 'noreply@rubri.ai')),
        'from_name': os.getenv('FROM_NAME', email_config.get('from_name', 'Rubri Interview Assistant'))
    }

def create_completion_email_html(
    position_title: str,
    task_id: str,
    rubric_id: Optional[str],
    result_summary: Dict[str, Any]
) -> str:
    """Create HTML email template for completion notification"""
    
    questions_count = result_summary.get('questions_generated', 0)
    duration = result_summary.get('interview_duration_minutes', 0)
    skills_count = result_summary.get('skills_identified', 0)
    
    # You'll need to update this with your actual frontend URL
    app_config = load_app_config()
    frontend_url = os.getenv('FRONTEND_URL', app_config.get('frontend_url', 'http://localhost:3000'))
    
    results_link = f"{frontend_url}/results/{rubric_id}" if rubric_id else f"{frontend_url}/tasks/{task_id}"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Interview Questions Ready - {position_title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #2563eb; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 8px 8px; }}
            .stats {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .stat-item {{ display: inline-block; margin-right: 30px; text-align: center; }}
            .stat-number {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
            .stat-label {{ font-size: 14px; color: #64748b; }}
            .button {{ 
                display: inline-block; 
                background: #2563eb; 
                color: white; 
                padding: 12px 24px; 
                text-decoration: none; 
                border-radius: 6px; 
                font-weight: bold;
                margin: 20px 0;
            }}
            .footer {{ text-align: center; margin-top: 30px; color: #64748b; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Your Interview Questions Are Ready!</h1>
                <p>Position: <strong>{position_title}</strong></p>
            </div>
            
            <div class="content">
                <p>Great news! Your comprehensive interview evaluation has been generated and is ready for review.</p>
                
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-number">{questions_count}</div>
                        <div class="stat-label">Questions Generated</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{skills_count}</div>
                        <div class="stat-label">Skills Identified</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">{duration}</div>
                        <div class="stat-label">Estimated Duration (min)</div>
                    </div>
                </div>
                
                <p>Your interview evaluation includes:</p>
                <ul>
                    <li>📋 Comprehensive technical questions tailored to the role</li>
                    <li>📝 Expected responses and evaluation criteria</li>
                    <li>🎯 Skill-based assessment framework</li>
                    <li>📊 Interviewer guidance and scoring rubrics</li>
                </ul>
                
                <a href="{results_link}" class="button">View Your Interview Evaluation</a>
                
                <p style="margin-top: 30px;">
                    <strong>Task ID:</strong> {task_id}<br>
                    <strong>Generated:</strong> Just now
                </p>
            </div>
            
            <div class="footer">
                <p>This email was sent automatically by Rubri Interview Assistant.</p>
                <p>If you have any questions, please contact our support team.</p>
            </div>
        </div>
    </body>
    </html>
    """

def create_completion_email_text(
    position_title: str,
    task_id: str,
    rubric_id: Optional[str],
    result_summary: Dict[str, Any]
) -> str:
    """Create plain text email template for completion notification"""
    
    questions_count = result_summary.get('questions_generated', 0)
    duration = result_summary.get('interview_duration_minutes', 0)
    skills_count = result_summary.get('skills_identified', 0)
    
    app_config = load_app_config()
    frontend_url = os.getenv('FRONTEND_URL', app_config.get('frontend_url', 'http://localhost:3000'))
    results_link = f"{frontend_url}/results/{rubric_id}" if rubric_id else f"{frontend_url}/tasks/{task_id}"
    
    return f"""
Your Interview Questions Are Ready!

Position: {position_title}

Great news! Your comprehensive interview evaluation has been generated and is ready for review.

Results Summary:
- Questions Generated: {questions_count}
- Skills Identified: {skills_count}
- Estimated Duration: {duration} minutes

Your interview evaluation includes:
- Comprehensive technical questions tailored to the role
- Expected responses and evaluation criteria
- Skill-based assessment framework
- Interviewer guidance and scoring rubrics

View your results: {results_link}

Task ID: {task_id}
Generated: Just now

---
This email was sent automatically by Rubri Interview Assistant.
If you have any questions, please contact our support team.
"""

@celery_app.task(name="email_tasks.send_completion_email")
def send_completion_email(
    user_email: str,
    task_id: str,
    position_title: str,
    rubric_id: Optional[str] = None,
    result_summary: Optional[Dict[str, Any]] = None
):
    """
    Send completion notification email to user
    """
    if not result_summary:
        result_summary = {}
    
    logger.info(f"Sending completion email for task {task_id} to {user_email}")
    
    try:
        email_config = get_email_config()
        
        # Validate email configuration
        if not email_config['smtp_username'] or not email_config['smtp_password']:
            logger.warning(f"Email configuration incomplete, skipping email for task {task_id}")
            return False
        
        # Create email content
        html_body = create_completion_email_html(position_title, task_id, rubric_id, result_summary)
        text_body = create_completion_email_text(position_title, task_id, rubric_id, result_summary)
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Interview Questions Ready - {position_title}"
        msg['From'] = f"{email_config['from_name']} <{email_config['from_email']}>"
        msg['To'] = user_email
        
        # Attach both text and HTML versions
        text_part = MIMEText(text_body, 'plain')
        html_part = MIMEText(html_body, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.starttls()
            server.login(email_config['smtp_username'], email_config['smtp_password'])
            
            text = msg.as_string()
            server.sendmail(email_config['from_email'], user_email, text)
        
        logger.info(f"Completion email sent successfully for task {task_id} to {user_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send completion email for task {task_id}: {str(e)}")
        return False

@celery_app.task(name="email_tasks.send_error_email")
def send_error_email(
    user_email: str,
    task_id: str,
    position_title: str,
    error_message: str
):
    """
    Send error notification email to user
    """
    logger.info(f"Sending error email for task {task_id} to {user_email}")
    
    try:
        email_config = get_email_config()
        
        if not email_config['smtp_username'] or not email_config['smtp_password']:
            logger.warning(f"Email configuration incomplete, skipping error email for task {task_id}")
            return False
        
        subject = f"Interview Generation Failed - {position_title}"
        
        text_body = f"""
Interview Generation Failed

Position: {position_title}
Task ID: {task_id}

We encountered an error while generating your interview questions:
{error_message}

Please try again or contact our support team if the issue persists.

---
This email was sent automatically by Rubri Interview Assistant.
"""
        
        # Create message
        msg = MIMEText(text_body)
        msg['Subject'] = subject
        msg['From'] = f"{email_config['from_name']} <{email_config['from_email']}>"
        msg['To'] = user_email
        
        # Send email
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.starttls()
            server.login(email_config['smtp_username'], email_config['smtp_password'])
            
            text = msg.as_string()
            server.sendmail(email_config['from_email'], user_email, text)
        
        logger.info(f"Error email sent successfully for task {task_id} to {user_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send error email for task {task_id}: {str(e)}")
        return False