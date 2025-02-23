import gradio as gr
import tempfile
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from subprocess import PIPE, STDOUT
print("Gradio app loaded.")

def capture_page(url: str, output_file: str = "screenshot.png"):
    """
    Captures a screenshot of the given webpage.
    
    :param url: The URL of the webpage to capture.
    :param output_file: The filename to save the screenshot.
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')  # Required in Docker
    options.add_argument('--disable-dev-shm-usage')  # Required in Docker
    options.add_argument('--disable-gpu')  # Required in Docker
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    
    # Set up Chrome service with explicit path to chromedriver and logging
    service = Service(
        executable_path='/usr/local/bin/chromedriver',
        log_output=PIPE  # Redirect logs to pipe
    )
    
    # Initialize Chrome with the service and options
    driver = webdriver.Chrome(
        service=service,
        options=options
    )
    
    try:
        driver.get(url)
        # Add a small delay to ensure page loads completely
        driver.implicitly_wait(5)
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
        print(f"Error in capture_and_show: {str(e)}")  # Add detailed logging
        return None  # Return None instead of error string to handle gracefully
    
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
            
        error_output = gr.Textbox(
            label="Error Message",
            visible=False,
            interactive=False
        )
            
        def capture_with_error(url):
            try:
                # Basic URL validation
                if not url:
                    return None, gr.update(visible=True, value="Please enter a URL")
                if not url.startswith(('http://', 'https://')):
                    return None, gr.update(visible=True, value="Please enter a valid URL starting with http:// or https://")
                    
                result = capture_and_show(url)
                if result is None:
                    return None, gr.update(visible=True, value="Failed to capture screenshot. Please check the URL and try again.")
                return result, gr.update(visible=False, value="")
            except Exception as e:
                return None, gr.update(visible=True, value=f"Error: {str(e)}")
            
        # Connect the components
        capture_btn.click(
            fn=capture_with_error,
            inputs=[url_input],
            outputs=[output_image, error_output]
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