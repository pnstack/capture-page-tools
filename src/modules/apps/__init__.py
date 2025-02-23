import gradio as gr
import tempfile
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
print("Gradio app loaded.")

def capture_page(url: str, output_file: str = "screenshot.png"):
    """
    Captures a screenshot of the given webpage.
    
    :param url: The URL of the webpage to capture.
    :param output_file: The filename to save the screenshot.
    """
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--window-size=1920,1080")  # Set window size
    
    # Initialize Chrome service
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(url)
        driver.save_screenshot(output_file)
        print(f"Screenshot saved: {output_file}")
    finally:
        driver.quit()

def capture_and_show(url: str):
    """Capture webpage and return the image"""
    try:
        # Get the temporary directory path (defaulting to /tmp if TMPDIR is not set)
        temp_dir = os.getenv('TMPDIR', '/tmp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create temporary file in the specified directory
        temp_path = os.path.join(temp_dir, f"screenshot_{os.urandom(8).hex()}.png")
        
        # Capture the webpage
        capture_page(url, temp_path)
        
        # Return the image path
        return temp_path
    except Exception as e:
        return f"Error capturing page: {str(e)}"
    
def create_gradio_app():
    """Create the main Gradio application with all components"""
    with gr.Blocks() as app:
        gr.Markdown("# Webpage Screenshot Capture")
        
        with gr.Row():
            url_input = gr.Textbox(
                label="Website URL",
                placeholder="Enter website URL (e.g., https://www.example.com)",
                scale=4
            )
            capture_btn = gr.Button("Capture", scale=1)
            
        with gr.Row():
            output_image = gr.Image(
                label="Captured Screenshot",
                type="filepath"
            )
            
        # Connect the components
        capture_btn.click(
            fn=capture_and_show,
            inputs=[url_input],
            outputs=[output_image]
        )
        
    return app

app = create_gradio_app()

# Configure server settings for Docker deployment
server_port = 7860  # Standard Gradio port
server_name = "0.0.0.0"  # Allow external connections

def main():
    """Launch the Gradio application"""
    print("Starting Gradio server...")
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=False,  # Disable sharing as we're running in Docker
        auth=None,    # Can be configured if authentication is needed
        ssl_verify=False,  # Disable SSL verification for internal Docker network
        show_error=True,
        favicon_path=None
    )

main()