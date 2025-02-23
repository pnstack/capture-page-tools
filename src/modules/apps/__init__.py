import gradio as gr
import tempfile
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from subprocess import PIPE, STDOUT
import traceback

print("Gradio app loaded.")

def capture_page(url: str, output_file: str = "screenshot.png"):
    """
    Captures a screenshot of the given webpage.
    
    :param url: The URL of the webpage to capture.
    :param output_file: The filename to save the screenshot.
    """
    options = Options()
    
    # Basic options
    options.add_argument('--headless=new')  # New headless mode
    options.add_argument('--no-sandbox')  # Required in Docker
    options.add_argument('--disable-dev-shm-usage')  # Required in Docker
    
    # Performance and stability options
    options.add_argument('--disable-gpu')  # Required in Docker
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    
    # Resource configuration
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-features=NetworkService,NetworkServiceInProcess')
    options.add_argument('--disable-features=site-per-process')
    
    # Memory and process settings
    options.add_argument('--single-process')  # Run in single process mode
    options.add_argument('--memory-pressure-off')
    options.add_argument('--disable-crash-reporter')
    options.add_argument('--disable-breakpad')  # Disable crash reporting
    
    # Additional stability options
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-web-security')
    
    # Set specific shared memory /dev/shm size (if needed)
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--shm-size=2g')
    
    # Set up Chrome service with explicit path to chromedriver and logging
    service = Service(
        # executable_path='/usr/local/bin/chromedriver',
        log_output=PIPE,  # Redirect logs to pipe
        service_args=['--verbose']  # Enable verbose logging
    )
    
    try:
        print("Initializing Chrome...")
        driver = webdriver.Chrome(
            service=service,
            options=options
        )
        
        print("Chrome initialized successfully")
        
        try:
            print(f"Navigating to URL: {url}")
            driver.get(url)
            
            # Wait for page load
            print("Waiting for page to load...")
            driver.implicitly_wait(10)  # Increased wait time
            
            # Additional wait for dynamic content
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            # WebDriverWait(driver, 10).until(
            #     lambda d: d.execute_script('return document.readyState') == 'complete'
            # )
            
            print("Taking screenshot...")
            driver.save_screenshot(output_file)
            print(f"Screenshot saved: {output_file}")
            return True
            
        except Exception as e:
            print(f"Error during page capture: {str(e)}")
            raise
        finally:
            print("Closing Chrome...")
            try:
                driver.close()  # Close current window
                driver.quit()   # Quit browser completely
                import psutil   # For process cleanup
                current_pid = os.getpid()
                current_process = psutil.Process(current_pid)
                children = current_process.children(recursive=True)
                for child in children:
                    if 'chrome' in child.name().lower():
                        child.terminate()
            except Exception as cleanup_error:
                print(f"Error during cleanup: {cleanup_error}")
            
    except Exception as e:
        print(f"Error initializing Chrome: {str(e)}")
        raise Exception(f"Failed to initialize Chrome: {str(e)}")

def capture_and_show(url: str):
    """Capture webpage and return the image"""
    try:
        # Get the temporary directory path (defaulting to /tmp if TMPDIR is not set)
        temp_dir = os.getenv('TMPDIR', '/tmp')
        
        try:
            # Ensure temp directory exists and has correct permissions
            os.makedirs(temp_dir, mode=0o777, exist_ok=True)
            print(f"Using temp directory: {temp_dir}")
            
            # Verify directory is writable
            if not os.access(temp_dir, os.W_OK):
                print(f"Warning: Temp directory {temp_dir} is not writable")
                # Try to create a user-specific temp directory instead
                temp_dir = os.path.join('/tmp', f'chrome_screenshots_{os.getuid()}')
                os.makedirs(temp_dir, mode=0o777, exist_ok=True)
                print(f"Created user-specific temp directory: {temp_dir}")
                
            # Create temporary file in the specified directory
            temp_path = os.path.join(temp_dir, f"screenshot_{os.urandom(8).hex()}.png")
            print(f"Temp file path: {temp_path}")
            
            # Capture the webpage
            success = capture_page(url, temp_path)
            if not success:
                print("Screenshot capture returned False")
                return None
            
            # Verify file was created
            if not os.path.exists(temp_path):
                print("Screenshot file was not created")
                return None
                
            print("Screenshot captured successfully")
            return temp_path
            
        except OSError as e:
            print(f"OS Error: {str(e)}")
            print(f"Stack trace: {traceback.format_exc()}")
            return None
            
    except Exception as e:
        print(f"Error in capture_and_show: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        return None
    
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