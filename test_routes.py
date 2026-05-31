import urllib.request
import urllib.parse
import re
import sys

# Setup opener with cookie jar
cookie_processor = urllib.request.HTTPCookieProcessor()
opener = urllib.request.build_opener(cookie_processor)
urllib.request.install_opener(opener)

BASE_URL = 'http://127.0.0.1:5000'

def get_csrf_token(html):
    # Match tag with name="csrf_token" and get the value attribute
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', html)
    if match:
        return match.group(1)
    return None

def login(username, password):
    print("Fetching login page to get CSRF token...")
    try:
        resp = urllib.request.urlopen(f'{BASE_URL}/login')
        html = resp.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching login page: {e}")
        return False
    
    csrf_token = get_csrf_token(html)
    if not csrf_token:
        print("Could not find CSRF token on login page.")
        return False
    print(f"Found CSRF token: {csrf_token}")
    
    # Send login POST request
    data = urllib.parse.urlencode({
        'csrf_token': csrf_token,
        'username': username,
        'password': password,
        'submit': 'Login'
    }).encode('utf-8')
    
    req = urllib.request.Request(f'{BASE_URL}/login', data=data, method='POST')
    try:
        resp = urllib.request.urlopen(req)
        final_url = resp.geturl()
        print(f"Login response URL: {final_url}")
        if 'dashboard' in final_url or resp.getcode() == 200:
            print("Login looks successful!")
            return True
    except Exception as e:
        print(f"Error during login POST: {e}")
    return False

def test_url(url_path):
    url = f'{BASE_URL}{url_path}'
    try:
        resp = urllib.request.urlopen(url)
        code = resp.getcode()
        print(f"  {url_path}: SUCCESS (Status {code})")
        return True
    except urllib.error.HTTPError as e:
        print(f"  {url_path}: FAILED (Status {e.code})")
        try:
            err_html = e.read().decode('utf-8', errors='ignore')
            if e.code == 500:
                print("--- Error Page Output ---")
                lines = err_html.split('\n')
                for line in lines[:30]:
                    if 'Traceback' in line or 'Exception' in line or 'Error' in line or 'p' in line:
                        print("  ", line.strip()[:120])
                print("-------------------------")
        except:
            pass
        return False
    except Exception as e:
        print(f"  {url_path}: EXCEPTION ({e})")
        return False

def test_add_patient():
    print("\nTesting Patient Admission...")
    # First get patients list or add page to verify it loads
    try:
        resp = urllib.request.urlopen(f'{BASE_URL}/patients/add')
        html = resp.read().decode('utf-8')
        csrf_token = get_csrf_token(html)
        print(f"Found CSRF token on Patient Add: {csrf_token}")
    except Exception as e:
        print(f"Error loading Patient Add page: {e}")
        return False

    patient_data = {
        'csrf_token': csrf_token or '',
        'name': 'Test Patient Python',
        'age': '35',
        'gender': 'Male',
        'blood_group': 'O+',
        'mobile': '9876543210',
        'email': 'testpatient@example.com',
        'emergency_contact': '9876543211',
        'address': '123 Test Lane, Python City',
        'disease': 'Fever',
        'doctor_id': '',  # None
        'ward_id': '',    # None
        'room_id': ''     # None
    }
    
    data = urllib.parse.urlencode(patient_data).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/patients/add', data=data, method='POST')
    try:
        resp = urllib.request.urlopen(req)
        print(f"Patient Add response URL: {resp.geturl()} Status: {resp.getcode()}")
        if resp.getcode() == 200 and 'patients' in resp.geturl():
            # Check if name is in the list
            list_html = resp.read().decode('utf-8')
            if 'Test Patient Python' in list_html:
                print("Patient successfully created and shown in list!")
                return True
            else:
                print("Patient not found in patients list HTML.")
        else:
            print("Failed redirect/status on Patient Add.")
    except Exception as e:
        print(f"Error during Patient Add POST: {e}")
    return False

def main():
    if not login('admin', 'admin123'):
        print("Login failed, aborting tests.")
        sys.exit(1)
        
    routes = [
        '/dashboard',
        '/patients',
        '/doctors',
        '/nurses',
        '/wards',
        '/rooms',
        '/appointments',
        '/medicines',
        '/bills',
        '/reports',
        '/profile',
        '/register'
    ]
    
    print("\nStarting route testing...")
    all_ok = True
    for route in routes:
        if not test_url(route):
            all_ok = False
            
    if not test_add_patient():
        all_ok = False
        
    if all_ok:
        print("\nAll tests completed and working perfectly!")
        sys.exit(0)
    else:
        print("\nSome tests failed.")
        sys.exit(1)

if __name__ == '__main__':
    main()
