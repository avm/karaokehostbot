import asyncio
import websockets
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# WebSocket server settings
WEBSOCKET_SERVER_URI = (
    "ws://localhost:8080/ws"  # Replace with your WebSocket server URI
)


# Initialize Selenium WebDriver
def setup_driver():
    options = Options()
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")
    service = Service(
        "/usr/local/bin/chromedriver"
    )  # Replace with the path to your WebDriver
    driver = webdriver.Chrome(service=service, options=options)
    return driver


# WebSocket client to receive URLs
async def websocket_client(driver):
    async with websockets.connect(WEBSOCKET_SERVER_URI) as websocket:
        print(f"Connected to WebSocket server at {WEBSOCKET_SERVER_URI}")
        try:
            async for message in websocket:
                print(f"Received URL: {message}")
                # Navigate to the received URL
                driver.get(message)
        except websockets.ConnectionClosed:
            print("WebSocket connection closed.")
        finally:
            driver.quit()


# Main function to start the WebSocket client and WebDriver
def main():
    driver = setup_driver()
    try:
        asyncio.run(websocket_client(driver))
    except KeyboardInterrupt:
        print("Program interrupted. Exiting...")
        driver.quit()


if __name__ == "__main__":
    main()
