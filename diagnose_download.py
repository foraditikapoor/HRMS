from app import app

with app.test_client() as client:
    response = client.get('/admin/attendance/download')
    print('status_code:', response.status_code)
    print('content_type:', response.headers.get('Content-Type'))
    print('content_disposition:', response.headers.get('Content-Disposition'))
    print('first_bytes:', response.data[:12])
