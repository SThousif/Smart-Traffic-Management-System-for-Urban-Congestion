import urllib.request

def fetch(path):
    url = 'http://127.0.0.1:3000' + path
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            data = r.read(2000)
            print(f'URL: {url} STATUS: {r.getcode()}')
            print(data.decode('utf-8', errors='ignore')[:800])
    except Exception as e:
        print(f'URL: {url} ERROR: {e}')

if __name__ == '__main__':
    for p in ['/view_parking', '/reserveslot/A1', '/reserveslot/123', '/debug_session']:
        fetch(p)
