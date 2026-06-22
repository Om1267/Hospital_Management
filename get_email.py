import json
import urllib.request
with urllib.request.urlopen('https://api.github.com/users/Om1267') as response:
    data = json.loads(response.read().decode())
    email = f"{data.get('id')}+{data.get('login')}@users.noreply.github.com"
    name = data.get('name') or data.get('login')
    print(email)
    print(name)
