import gradio as gr

def get_custom_theme():
    """
    Constructs a custom professional Gradio Theme matching the color requirements:
    Primary: #1E3A8A (Deep Navy Blue)
    Secondary: #2563EB (Royal Blue)
    Background: #F8FAFC (Light slate gray-blue)
    Text: #0F172A (Very dark blue-gray)
    """
    theme = gr.themes.Soft(
        primary_hue=gr.themes.colors.indigo,
        secondary_hue=gr.themes.colors.blue,
        neutral_hue=gr.themes.colors.slate,
    ).set(
        # Light mode colors
        body_background_fill="#F8FAFC",
        body_text_color="#0F172A",
        background_fill_primary="#FFFFFF",
        
        # Primary Action Buttons
        button_primary_background_fill="#1E3A8A",
        button_primary_background_fill_hover="#2563EB",
        button_primary_text_color="#FFFFFF",
        
        # Secondary Action Buttons
        button_secondary_background_fill="#E2E8F0",
        button_secondary_background_fill_hover="#CBD5E1",
        button_secondary_text_color="#0F172A",
        
        # Dark mode overrides (for a beautiful dual feel)
        body_background_fill_dark="#0F172A",
        body_text_color_dark="#F8FAFC",
        background_fill_primary_dark="#1E293B",
        button_primary_background_fill_dark="#2563EB",
        button_primary_background_fill_hover_dark="#3B82F6",
        button_primary_text_color_dark="#FFFFFF"
    )
    return theme
