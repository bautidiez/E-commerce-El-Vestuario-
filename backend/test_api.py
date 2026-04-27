
import requests
import time

def test_api():
    url = "http://127.0.0.1:5000/api/productos"
    try:
        start_time = time.time()
        response = requests.get(url)
        duration = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: OK")
            print(f"Response Time: {duration:.2f}ms")
            print(f"Products Count: {len(data.get('items', []))}")
        else:
            print(f"Status: FAILED ({response.status_code})")
            print(response.text)
    except Exception as e:
        print(f"Error connecting to server: {e}")

if __name__ == "__main__":
    test_api()
