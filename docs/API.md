# API Reference

## Authentication
All API endpoints require an active session. Login via /login.

## Patient Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /patients | List all patients |
| POST | /patients/add | Register new patient |
| GET | /patients/<id> | Get patient details |
| POST | /patients/<id>/discharge | Discharge patient |

## Billing Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /billing/<patient_id> | View patient bill |
| POST | /billing/<patient_id>/add | Add billing item |
| GET | /billing/<patient_id>/pdf | Download bill as PDF |

## Ward/Bed Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /wards | List all wards |
| POST | /wards/add | Add new ward |
| GET | /beds | List all beds |

## Prescription Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /prescriptions/add | Add prescription |
| GET | /prescriptions/<patient_id> | Get patient prescriptions |
