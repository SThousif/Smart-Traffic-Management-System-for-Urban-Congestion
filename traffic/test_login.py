import requests
url='http://127.0.0.1:3000/customer'
data={'customeremail':'testuser@example.com','customerpassword':'testpass'}
resp=requests.post(url,data=data,allow_redirects=False)
print('status',resp.status_code)
print('headers:',resp.headers)
print('cookies:',resp.cookies.get_dict())
print('text snippet:', resp.text[:400])
