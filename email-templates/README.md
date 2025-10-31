# Email Templates

This directory contains custom Jinja2 email templates for GCP FinOps Sentinel notifications.

## Template Files

### Budget Alert Template
- **budget_alert.html** - HTML template for budget alert emails
- **budget_alert_subject.txt** - Subject line template for budget alerts

### Policy Action Template
- **policy_action.html** - HTML template for policy action event emails
- **policy_action_subject.txt** - Subject line template for policy actions

## Template Variables

### Budget Alert Template Variables

Available in `budget_alert.html`:

```jinja2
{{ cost_amount }}           # Current cost (float)
{{ budget_amount }}         # Budget amount (float)
{{ threshold_percent }}     # Threshold percentage (float)
{{ billing_account_id }}    # Billing account ID (string)
{{ billing_account_name }}  # Billing account display name (string)
{{ budget_id }}             # Budget ID (string)
{{ budget_name }}           # Budget display name (string)
{{ organization_id }}       # Organization ID (string)
{{ custom_message }}        # Optional custom message (string or None)
{{ actions }}               # List of automated actions taken
```

Actions list structure:
```python
[
    {
        "type": "restrict_services",
        "resource_id": "my-project",
        "resource_type": "project",
        "display_name": "My Production Project",
        "details": "Restricted services on My Production Project (my-project): compute.googleapis.com"
    }
]
```

**Display Names**: Templates automatically show human-readable names alongside IDs for better readability. Display names are fetched from GCP APIs for billing accounts, budgets, and projects discovered via labels.

### Policy Action Template Variables

Available in `policy_action.html`:

```jinja2
{{ timestamp }}             # Action timestamp (string)
{{ action_type }}           # Action type (string)
{{ resource_type }}         # Resource type (project/folder/organization)
{{ resource_id }}           # Resource ID (string)
{{ organization_id }}       # Organization ID (string)
{{ success }}               # Boolean indicating success/failure
{{ details }}               # Dictionary with additional details
```

Details dictionary may contain:
- `constraint` - Constraint name applied
- `services` - List of services affected
- `enforce` - Boolean constraint enforcement
- `values` - List of constraint values
- `display_name` - Human-readable name for the resource
- `error` - Error message (if failed)

## Using Custom Templates

### With Docker Compose

Templates are automatically mounted into the container at `/email-templates` when using Docker Compose:

```bash
docker compose up
```

The `TEMPLATE_DIR` environment variable is set to `/email-templates` in the compose file.

### Standalone Deployment

1. Deploy templates to a persistent volume or Cloud Storage
2. Set the `TEMPLATE_DIR` environment variable to the template directory path
3. Restart the Cloud Function

### Local Testing

For local development:

```bash
export TEMPLATE_DIR=/path/to/email-templates
export SMTP_HOST=mailhog
export SMTP_PORT=1025
export SMTP_USE_TLS=false
export SMTP_FROM_EMAIL=test@example.com

# Run function locally
cd src
functions-framework --target=budget_response_handler --debug
```

## Template Development

### Testing Templates Locally

Use the provided test script to send sample emails to MailHog:

```bash
python scripts/test-email-templates.py
```

Then open http://localhost:8025 to view the emails.

### Template Syntax

Templates use Jinja2 syntax:

**Conditionals:**
```jinja2
{% if threshold_percent >= 100 %}
    <div class="critical">Critical Alert!</div>
{% elif threshold_percent >= 90 %}
    <div class="warning">Warning!</div>
{% else %}
    <div class="info">Info</div>
{% endif %}
```

**Loops:**
```jinja2
{% for action in actions %}
    <div>{{ action.type }}: {{ action.details }}</div>
{% endfor %}
```

**Filters:**
```jinja2
{{ "%.2f"|format(cost_amount) }}  # Format as 2 decimal float
{{ threshold_percent|round(1) }}  # Round to 1 decimal
{{ services|join(', ') }}         # Join list with commas
```

## Customization Examples

### Adding Company Branding

Modify the header gradient colors in the `<style>` section:

```css
.header {
    background: linear-gradient(135deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 100%);
}
```

### Adding a Logo

Add an image in the header section:

```html
<div class="header">
    <img src="https://your-cdn.com/logo.png" alt="Company Logo" style="max-width: 200px; margin-bottom: 20px;">
    <h1>GCP Budget Alert</h1>
</div>
```

### Custom Threshold Colors

Modify the color logic in the alert banner:

```jinja2
background: {% if threshold_percent >= 100 %}#dc2626{% elif threshold_percent >= 80 %}#f97316{% else %}#3b82f6{% endif %};
```

### Additional Sections

Add custom sections to the content area:

```html
<div class="section">
    <h3 class="section-title">Recommended Actions</h3>
    <ul>
        <li>Review high-cost resources in Cloud Console</li>
        <li>Enable committed use discounts</li>
        <li>Contact FinOps team for optimization guidance</li>
    </ul>
</div>
```

## Best Practices

1. **Mobile Responsive**: Templates use responsive CSS Grid - test on mobile devices
2. **Inline CSS**: Keep styles inline for better email client compatibility
3. **Safe Variables**: Always check for None values before rendering
4. **Testing**: Test all templates with MailHog before production deployment
5. **Accessibility**: Use semantic HTML and sufficient color contrast
6. **File Size**: Keep HTML under 100KB for email client compatibility

## Troubleshooting

### Templates Not Loading

1. Check `TEMPLATE_DIR` environment variable is set correctly
2. Verify template files exist in the directory
3. Check file permissions (templates must be readable)
4. Review function logs for Jinja2 errors

### Template Rendering Errors

1. Validate Jinja2 syntax using online validators
2. Check variable names match exactly (case-sensitive)
3. Test with sample data locally before deploying
4. Review error logs for specific syntax issues

### Email Not Displaying Correctly

1. Test in MailHog first (http://localhost:8025)
2. Validate HTML using W3C validator
3. Check CSS compatibility with email clients
4. Use inline styles instead of `<style>` tags for better compatibility
