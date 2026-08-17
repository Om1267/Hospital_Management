import urllib.request
import urllib.parse
import re
import sys
import datetime

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
        'room_id': '2'    # Semi-Private (Room 102)
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

    # 4. Discharge the patient (Attempt 1: Should block and redirect to pending bill details)
    print(f"\nDischarging patient #{patient_id} (Attempt 1: Unpaid bill)...")
    discharge_data = {
        'csrf_token': csrf_token or ''
    }
    data = urllib.parse.urlencode(discharge_data).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/patients/{patient_id}/discharge', data=data, method='POST')
    try:
        resp = urllib.request.urlopen(req)
        redirect_url = resp.geturl()
        print(f"Discharge redirect URL: {redirect_url}")
        
        # Verify it redirected to bill payment page
        bill_match = re.search(r'bills/(\d+)', redirect_url)
        if not bill_match:
            print("FAILED: Discharge did not redirect to pay outstanding bill.")
            return False
        
        bill_id = bill_match.group(1)
        print(f"Outstanding Bill ID generated: {bill_id}")
        
        # Check summary page to verify patient status is STILL Admitted
        summary_resp = urllib.request.urlopen(f'{BASE_URL}/patients/{patient_id}/summary')
        summary_html = summary_resp.read().decode('utf-8')
        if 'status-admitted' in summary_html.lower() or 'admitted' in summary_html.lower():
            print("SUCCESS: Patient remains Admitted because bill is unpaid.")
        else:
            print("FAILED: Patient was discharged despite outstanding bill.")
            return False
            
    except Exception as e:
        print(f"Error during discharge Attempt 1: {e}")
        return False

    # 5. Pay the outstanding bill
    print(f"\nPaying outstanding Bill #{bill_id}...")
    pay_data = {
        'csrf_token': csrf_token or ''
    }
    data = urllib.parse.urlencode(pay_data).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}/bills/{bill_id}/pay', data=data, method='POST')
    try:
        resp = urllib.request.urlopen(req)
        # Should redirect back to patient summary page
        print(f"Bill paid redirect URL: {resp.geturl()}")
        if 'summary' in resp.geturl():
            print("SUCCESS: Redirected back to summary page after payment!")
        else:
            print("FAILED: Did not redirect to summary page after paying bill.")
            return False
    except Exception as e:
        print(f"Error paying bill: {e}")
        return False

    # 6. Discharge the patient (Attempt 2: Should succeed since bill is paid)
    print(f"\nDischarging patient #{patient_id} (Attempt 2: Paid bill)...")
    req = urllib.request.Request(f'{BASE_URL}/patients/{patient_id}/discharge', data=data, method='POST')
    try:
        resp = urllib.request.urlopen(req)
        summary_html_discharge = resp.read().decode('utf-8')
        if 'discharged' in summary_html_discharge.lower():
            print("SUCCESS: Patient status is now Discharged!")
        else:
            print("FAILED: Patient status did not change to Discharged after paying bill.")
            return False
    except Exception as e:
        print(f"Error during discharge Attempt 2: {e}")
        return False

    # 7. Verify PDF download for bills
    print(f"\nDownloading bill PDF for Bill #{bill_id}...")
    try:
        pdf_resp = urllib.request.urlopen(f'{BASE_URL}/bills/{bill_id}/pdf')
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


def test_new_6_features():
    print("\n--- Testing the 6 New Hospital Modules ---")
    
    # Get initial CSRF token by hitting patient summary
    try:
        resp = urllib.request.urlopen(f'{BASE_URL}/patients/1/summary')
        html = resp.read().decode('utf-8')
        csrf_token = get_csrf_token(html)
    except Exception as e:
        print(f"Error fetching patient summary CSRF: {e}")
        return False

    # 1. Lab Tests
    print("\nTesting Lab Tests Module...")
    try:
        # Request a new test
        data = urllib.parse.urlencode({
            'csrf_token': csrf_token or '',
            'patient_id': '1',
            'test_name': 'Blood sugar test',
            'category': 'Blood Test',
            'cost': '200.0'
        }).encode('utf-8')
        req = urllib.request.Request(f'{BASE_URL}/lab_tests/add', data=data, method='POST')
        resp = urllib.request.urlopen(req)
        
        # Verify it shows up in lab tests list
        list_resp = urllib.request.urlopen(f'{BASE_URL}/lab_tests')
        list_html = list_resp.read().decode('utf-8')
        if 'Blood sugar test' in list_html:
            print("  SUCCESS: Lab test requested and listed.")
        else:
            print("  FAILED: Lab test request not found in list.")
            return False

        # Update test result
        data = urllib.parse.urlencode({
            'csrf_token': csrf_token or '',
            'result': 'Normal (95 mg/dL)'
        }).encode('utf-8')
        # Seed lab tests: CBC is 1, MRI is 2. The new one should be ID 3.
        req = urllib.request.Request(f'{BASE_URL}/lab_tests/3/update', data=data, method='POST')
        resp = urllib.request.urlopen(req)
        
        list_resp_after = urllib.request.urlopen(f'{BASE_URL}/lab_tests')
        list_html_after = list_resp_after.read().decode('utf-8')
        if 'Normal (95 mg/dL)' in list_html_after:
            print("  SUCCESS: Lab test result updated and completed.")
        else:
            print("  FAILED: Lab test result update not shown.")
            return False
    except Exception as e:
        print(f"  EXCEPTION in Lab Tests test: {e}")
        return False

    # 2. Ambulances
    print("\nTesting Ambulances Module...")
    try:
        # Add new ambulance
        data = urllib.parse.urlencode({
            'csrf_token': csrf_token or '',
            'vehicle_number': 'DL-4CD-3456',
            'driver_name': 'Harish Kumar',
            'driver_contact': '9876543213',
            'status': 'Available'
        }).encode('utf-8')
        req = urllib.request.Request(f'{BASE_URL}/ambulances/add', data=data, method='POST')
        resp = urllib.request.urlopen(req)

        # Verify added
        list_resp = urllib.request.urlopen(f'{BASE_URL}/ambulances')
        list_html = list_resp.read().decode('utf-8')
        if 'DL-4CD-3456' in list_html:
            print("  SUCCESS: New ambulance registered.")
        else:
            print("  FAILED: Registered ambulance not listed.")
            return False

        # Book ambulance
        data = urllib.parse.urlencode({
            'csrf_token': csrf_token or '',
            'ambulance_id': '1', # Rajesh Kumar is available
            'patient_name': 'Rahul Gupta',
            'destination': 'Noida Sector-62',
            'charges': '800.0'
        }).encode('utf-8')
        req = urllib.request.Request(f'{BASE_URL}/ambulances/book', data=data, method='POST')
        resp = urllib.request.urlopen(req)

        # Check booking exists (seed booking was ID 1, so this new one is ID 2)
        list_resp_after = urllib.request.urlopen(f'{BASE_URL}/ambulances')
        list_html_after = list_resp_after.read().decode('utf-8')
        if 'Noida Sector-62' in list_html_after:
            print("  SUCCESS: Ambulance dispatch booking created.")
        else:
            print("  FAILED: Ambulance booking not found in log.")
            return False

        # Complete booking
        data = urllib.parse.urlencode({'csrf_token': csrf_token or ''}).encode('utf-8')
        req = urllib.request.Request(f'{BASE_URL}/ambulances/booking/2/complete?action=Completed', data=data, method='POST')
        resp = urllib.request.urlopen(req)
        print("  SUCCESS: Ambulance booking completed.")
    except Exception as e:
        print(f"  EXCEPTION in Ambulances test: {e}")
        return False

    # 3. Duty Roster
    print("\nTesting Duty Roster Module...")
    try:
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        # Schedule shift
        data = urllib.parse.urlencode({
            'csrf_token': csrf_token or '',
            'shift_date': today_str,
            'staff_type': 'doctor',
            'doctor_id': '1',
            'shift_type': 'Night',
            'ward_id': ''
        }).encode('utf-8')
        req = urllib.request.Request(f'{BASE_URL}/roster/add', data=data, method='POST')
        resp = urllib.request.urlopen(req)

        # Check in list
        list_resp = urllib.request.urlopen(f'{BASE_URL}/roster?date={today_str}')
        list_html = list_resp.read().decode('utf-8')
        if 'Night' in list_html:
            print("  SUCCESS: Shift scheduled in roster.")
        else:
            print("  FAILED: Scheduled shift not found in roster list.")
            return False

        # Update roster entry (seeds were 1 and 2, so this new roster entry is ID 3)
        data = urllib.parse.urlencode({'csrf_token': csrf_token or ''}).encode('utf-8')
        req = urllib.request.Request(f'{BASE_URL}/roster/3/update?status=Completed', data=data, method='POST')
        resp = urllib.request.urlopen(req)
        print("  SUCCESS: Shift status updated to Completed.")
    except Exception as e:
        print(f"  EXCEPTION in Duty Roster test: {e}")
        return False

    # 4. Visitor Logs
    print("\nTesting Visitor Logs Module...")
    try:
        # Check in visitor
        data = urllib.parse.urlencode({
            'csrf_token': csrf_token or '',
            'patient_id': '1',
            'visitor_name': 'Aman Gupta',
            'contact': '9876543214',
            'relationship': 'Sibling'
        }).encode('utf-8')
        req = urllib.request.Request(f'{BASE_URL}/visitors/checkin', data=data, method='POST')
        resp = urllib.request.urlopen(req)

        # Verify listed
        list_resp = urllib.request.urlopen(f'{BASE_URL}/visitors')
        list_html = list_resp.read().decode('utf-8')
        if 'Aman Gupta' in list_html:
            print("  SUCCESS: Visitor pass checked-in.")
        else:
            print("  FAILED: Checked-in visitor not listed.")
            return False

        # Check out visitor (seed visitor was 1, so this is ID 2)
        data = urllib.parse.urlencode({'csrf_token': csrf_token or ''}).encode('utf-8')
        req = urllib.request.Request(f'{BASE_URL}/visitors/2/checkout', data=data, method='POST')
        resp = urllib.request.urlopen(req)
        print("  SUCCESS: Visitor checked-out.")
    except Exception as e:
        print(f"  EXCEPTION in Visitor Logs test: {e}")
        return False

    # 5. Insurance Claims
    print("\nTesting Insurance Claims Module...")
    try:
        # File claim
        data = urllib.parse.urlencode({
            'csrf_token': csrf_token or '',
            'patient_id': '1',
            'insurance_provider': 'LIC Insurance',
            'policy_number': 'POL-112233',
            'claim_amount': '15000.0'
        }).encode('utf-8')
        req = urllib.request.Request(f'{BASE_URL}/claims/add', data=data, method='POST')
        resp = urllib.request.urlopen(req)

        # Verify listed
        list_resp = urllib.request.urlopen(f'{BASE_URL}/claims')
        list_html = list_resp.read().decode('utf-8')
        if 'LIC Insurance' in list_html:
            print("  SUCCESS: Insurance claim filed.")
        else:
            print("  FAILED: Filed insurance claim not listed.")
            return False

        # Approve claim (seed claim was 1, so this is ID 2)
        data = urllib.parse.urlencode({
            'csrf_token': csrf_token or '',
            'status': 'Approved',
            'approved_amount': '10000.0'
        }).encode('utf-8')
        req = urllib.request.Request(f'{BASE_URL}/claims/2/update', data=data, method='POST')
        resp = urllib.request.urlopen(req)
        print("  SUCCESS: Insurance claim approved.")
    except Exception as e:
        print(f"  EXCEPTION in Insurance Claims test: {e}")
        return False

    # 6. Patient Feedback
    print("\nTesting Feedback Module...")
    try:
        # Submit feedback
        data = urllib.parse.urlencode({
            'csrf_token': csrf_token or '',
            'patient_name': 'Tester Customer',
            'email': 'tester@example.com',
            'rating': '5',
            'category': 'Overall',
            'comments': 'Great overall service!'
        }).encode('utf-8')
        req = urllib.request.Request(f'{BASE_URL}/feedback/submit', data=data, method='POST')
        resp = urllib.request.urlopen(req)

        # Verify listed
        list_resp = urllib.request.urlopen(f'{BASE_URL}/feedback')
        list_html = list_resp.read().decode('utf-8')
        if 'Tester Customer' in list_html and 'Great overall service!' in list_html:
            print("  SUCCESS: Feedback submitted and listed successfully.")
        else:
            print("  FAILED: Submitted feedback not found in reviews list.")
            return False
    except Exception as e:
        print(f"  EXCEPTION in Feedback test: {e}")
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
        '/register',
        '/lab_tests',
        '/ambulances',
        '/roster',
        '/visitors',
        '/claims',
        '/feedback'
    ]
    
    print("\nStarting basic route testing...")
    all_ok = True
    for route in routes:
        if not test_url(route):
            all_ok = False
            
    if not test_new_features():
        all_ok = False
        
    if not test_new_6_features():
        all_ok = False
        
    if all_ok:
        print("\nAll tests completed and working perfectly!")
        sys.exit(0)
    else:
        print("\nSome tests failed.")
        sys.exit(1)

if __name__ == '__main__':
    main()
