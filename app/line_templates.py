def create_reminder_flex_message(project_name, date_str, reminders):
    """
    Constructs a LINE Flex Message bubble for project reminders.
    """
    
    # Construct Flex Message Bubble body
    bubble_body_contents = []
    
    # Date
    bubble_body_contents.append({
            "type": "text",
            "text": f"Date: {date_str}",
            "size": "xs",
            "color": "#aaaaaa",
            "wrap": True,
            "margin": "sm"
    })

    bubble_body_contents.append({
        "type": "separator",
        "margin": "md"
    })
    
    # List of tasks
    for reminder in reminders:
        bubble_body_contents.append({
            "type": "text",
            "text": f"• {reminder}",
            "size": "sm",
            "wrap": True,
            "margin": "md",
            "color": "#333333"
        })

    flex_message = {
        "type": "flex",
        "altText": f"TOR Reminders - {project_name}",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": bubble_body_contents
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "Enter Site",
                            "uri": "https://tor-notification.smg-service.app/"
                        },
                        "style": "primary",
                        "color": "#4F46E5",
                        "height": "sm"
                    }
                ],
                "spacing": "sm"
            }
        }
    }
    return flex_message
