import gradio as gr
import tempfile
import os
import time
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from subprocess import PIPE, STDOUT
import psutil

print("Gradio app loaded.")

def capture_page(url: str, output_file: str = "screenshot.png"):
    """
    Captures a screenshot of the given webpage.
    
    :param url: The URL of the webpage to capture.
    :param output_file: The filename to save the screenshot.
    """
    options = Options()
    
    # Use new headless mode and basic options for Docker
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-features=NetworkService,NetworkServiceInProcess')
    options.add_argument('--disable-features=site-per-process')
    options.add_argument('--single-process')
    options.add_argument('--memory-pressure-off')
    options.add_argument('--disable-crash-reporter')
    options.add_argument('--disable-breakpad')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-web-security')
    options.add_argument('--shm-size=2g')
    
    # Set page load strategy to 'none' to avoid waiting indefinitely
    options.page_load_strategy = "none"
    
    # Set up Chrome service (ensure chromedriver is in your PATH)
    service = Service(
        log_output=PIPE,
        service_args=['--verbose']
    )
    
    driver = None
    try:
        print("Initializing Chrome...")
        driver = webdriver.Chrome(service=service, options=options)
        if not driver:
            raise Exception("Failed to initialize Chrome driver")
            
        print("Chrome initialized successfully")
        driver.implicitly_wait(5)
        
        try:
            # Set a 30-second timeout for page load
            driver.set_page_load_timeout(30)
            try:
                print(f"Navigating to URL: {url}")
                driver.get(url)
            except TimeoutException:
                print("Page load timed out. Proceeding with screenshot capture...")
            
            # Wait for the document ready state to be 'interactive' or 'complete'
            try:
                print("Waiting for document ready state...")
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script('return document.readyState') in ["interactive", "complete"]
                )
            except TimeoutException:
                print("Document did not reach ready state within timeout, proceeding anyway.")
            
            # Additional short delay to allow dynamic content to settle
            time.sleep(2)
            
            print("Taking screenshot...")
            driver.save_screenshot(output_file)
            print(f"Screenshot saved: {output_file}")
            return True
            
        except Exception as e:
            print(f"Error during page capture: {str(e)}")
            raise
        finally:
            print("Closing Chrome...")
            # Wrap cleanup in a try/except to prevent errors if the session is already closed
            if driver:
                try:
                    driver.quit()
                except Exception as cleanup_error:
                    print(f"Error during driver.quit(): {cleanup_error}")
                
                # Optionally clean up any lingering Chrome processes
                try:
                    current_pid = os.getpid()
                    current_process = psutil.Process(current_pid)
                    for child in current_process.children(recursive=True):
                        if 'chrome' in child.name().lower():
                            child.terminate()
                except Exception as psutil_error:
                    print(f"Error during process cleanup: {psutil_error}")
            
    except Exception as e:
        print(f"Error initializing Chrome: {str(e)}")
        raise Exception(f"Failed to initialize Chrome: {str(e)}")

def capture_and_show(url: str):
    """Capture webpage and return the image"""
    try:
        temp_dir = os.getenv('TMPDIR', '/tmp')
        try:
            os.makedirs(temp_dir, mode=0o777, exist_ok=True)
            print(f"Using temp directory: {temp_dir}")
            if not os.access(temp_dir, os.W_OK):
                print(f"Warning: Temp directory {temp_dir} is not writable")
                temp_dir = os.path.join('/tmp', f'chrome_screenshots_{os.getuid()}')
                os.makedirs(temp_dir, mode=0o777, exist_ok=True)
                print(f"Created user-specific temp directory: {temp_dir}")
                
            temp_path = os.path.join(temp_dir, f"screenshot_{os.urandom(8).hex()}.png")
            print(f"Temp file path: {temp_path}")
            
            success = capture_page(url, temp_path)
            if not success:
                print("Screenshot capture returned False")
                return None
                
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
            
        capture_btn.click(
            fn=capture_with_error,
            inputs=[url_input],
            outputs=[output_image, error_output]
        )
        
    return app

app = create_gradio_app()

server_port = 7860
server_name = "0.0.0.0"

def main():
    print("Starting Gradio server...")
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=False,
        auth=None,
        ssl_verify=False,
        show_error=True,
        favicon_path=None
    )

main()
