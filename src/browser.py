import asyncio
import websockets
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

# WebSocket server settings
WEBSOCKET_SERVER_URI = (
    "ws://karaoke.myltsev.ru:8080/ws"  # Replace with your WebSocket server URI
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
async def websocket_client(driver, uri):
    async with websockets.connect(uri) as websocket:
        print(f"Connected to WebSocket server at {uri}")
        try:
            async for message in websocket:
                print(f"Received URL: {message}")
                # Navigate to the received URL
                driver.get(message)

                # Wait for the video player to load
                time.sleep(3)

                play_button = driver.find_element(
                    By.CSS_SELECTOR, "button.ytp-fullscreen-button"
                )
                play_button.click()

        except websockets.ConnectionClosed:
            print("WebSocket connection closed.")


# Main function to start the WebSocket client and WebDriver
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default=WEBSOCKET_SERVER_URI)
    args = parser.parse_args()

    driver = setup_driver()
    try:
        while True:
            asyncio.run(websocket_client(driver, args.uri))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
