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
        return False
    except Exception as e:
        print(f"  {url_path}: EXCEPTION ({e})")
        return False

def test_new_features():
    print("\n--- Testing New Features (Discharge, Prescription, PDFs) ---")
    
    # 1. Admit a new test patient first
    print("\nAdmitting patient for new features testing...")
    try:
        resp = urllib.request.urlopen(f'{BASE_URL}/patients/add')
        html = resp.read().decode('utf-8')
        csrf_token = get_csrf_token(html)
    except Exception as e:
        print(f"Error fetching Patient Add: {e}")
        return False

    patient_data = {
        'csrf_token': csrf_token or '',
        'name': 'Feature Test Patient',
        'age': '42',
        'gender': 'Female',
        'blood_group': 'AB+',
        'mobile': '9000000000',
        'email': 'featuretest@example.com',
        'emergency_contact': '9000000001',
        'address': 'Feature Lane',
        'disease': 'Diagnosed for Test',
        'doctor_id': '1', # Arjun Sharma
        'ward_id': '1',   # General Ward
        'room_id': '102'  # Semi-Private
    }
    
    data = urllib.parse.urlencode(patient_data).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/patients/add', data=data, method='POST')
    try:
        resp = urllib.request.urlopen(req)
        # Parse the page to get the ID of the newly admitted patient
        list_html = resp.read().decode('utf-8')
        print(f"Patient admitted successfully. List page URL: {resp.geturl()}")
        
        # Let's search for the patient ID in the HTML
        match = re.search(r'patients/(\d+)/summary', list_html)
        if not match:
            print("Could not locate newly created patient ID on list page.")
            return False
        
        patient_id = match.group(1)
        print(f"Newly created patient ID: {patient_id}")
    except Exception as e:
        print(f"Error creating patient for feature tests: {e}")
        return False

    # 2. Prescribe a medicine
    print(f"\nPrescribing medicine to patient #{patient_id}...")
    try:
        summary_resp = urllib.request.urlopen(f'{BASE_URL}/patients/{patient_id}/summary')
        summary_html = summary_resp.read().decode('utf-8')
        csrf_token = get_csrf_token(summary_html)
    except Exception as e:
        print(f"Error loading summary page to get CSRF: {e}")
        return False

    presc_data = {
        'csrf_token': csrf_token or '',
        'medicine_id': '1', # Paracetamol
        'quantity': '3',
        'instructions': 'Take 3 times daily after meals'
    }
    data = urllib.parse.urlencode(presc_data).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/patients/{patient_id}/prescribe', data=data, method='POST')
    try:
        resp = urllib.request.urlopen(req)
        summary_html_after = resp.read().decode('utf-8')
        if 'Take 3 times daily after meals' in summary_html_after:
            print("SUCCESS: Prescription added and shown on summary page!")
        else:
            print("FAILED: Prescription not found on summary page after POST.")
            return False
    except Exception as e:
        print(f"Error prescribing medicine: {e}")
        return False

    # 3. Download Patient Summary PDF
    print(f"\nDownloading patient summary PDF for #{patient_id}...")
    try:
        pdf_resp = urllib.request.urlopen(f'{BASE_URL}/patients/{patient_id}/pdf')
        content_type = pdf_resp.headers.get('Content-Type')
        print(f"PDF response Status: {pdf_resp.getcode()}, Content-Type: {content_type}")
        if pdf_resp.getcode() == 200 and 'application/pdf' in content_type:
            print("SUCCESS: Patient summary PDF downloaded successfully!")
        else:
            print(f"FAILED: PDF download failed with Content-Type: {content_type}")
            return False
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        return False

    # 4. Discharge the patient
    print(f"\nDischarging patient #{patient_id}...")
    discharge_data = {
        'csrf_token': csrf_token or ''
    }
    data = urllib.parse.urlencode(discharge_data).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/patients/{patient_id}/discharge', data=data, method='POST')
    try:
        resp = urllib.request.urlopen(req)
        summary_html_discharge = resp.read().decode('utf-8')
        if 'Discharged' in summary_html_discharge:
            print("SUCCESS: Patient status is now Discharged!")
        else:
            print("FAILED: Patient status did not change to Discharged.")
            return False
    except Exception as e:
        print(f"Error discharging patient: {e}")
        return False

    # 5. Verify PDF download for bills
    print(f"\nDownloading bill PDF for Bill #1...")
    try:
        pdf_resp = urllib.request.urlopen(f'{BASE_URL}/bills/1/pdf')
        content_type = pdf_resp.headers.get('Content-Type')
        print(f"Bill PDF response Status: {pdf_resp.getcode()}, Content-Type: {content_type}")
        if pdf_resp.getcode() == 200 and 'application/pdf' in content_type:
            print("SUCCESS: Bill PDF downloaded successfully!")
        else:
            print(f"FAILED: Bill PDF download failed with Content-Type: {content_type}")
            return False
    except Exception as e:
        print(f"Error downloading Bill PDF: {e}")
        return False

    return True

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
    
    print("\nStarting basic route testing...")
    all_ok = True
    for route in routes:
        if not test_url(route):
            all_ok = False
            
    if not test_new_features():
        all_ok = False
        
    if all_ok:
        print("\nAll tests completed and working perfectly!")
        sys.exit(0)
    else:
        print("\nSome tests failed.")
        sys.exit(1)

if __name__ == '__main__':
    main()
