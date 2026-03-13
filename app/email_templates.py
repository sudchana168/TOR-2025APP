def get_enter_site_button_html():
    """
    Returns the HTML string for the premium 'Enter Site' button.
    """
    return """
    <div style="margin-top: 35px; text-align: left;">
        <a href="https://tor-notification.smg-service.app:8443/" 
           style="background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); 
                  color: white; 
                  padding: 12px 32px; 
                  text-decoration: none; 
                  border-radius: 9999px; 
                  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
                  font-weight: 600; 
                  font-size: 15px; 
                  letter-spacing: 0.5px; 
                  box-shadow: 0 4px 14px 0 rgba(79, 70, 229, 0.4); 
                  display: inline-block;
                  transition: transform 0.2s;">
            Enter Site
        </a>
    </div>
    """
