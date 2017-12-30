from dropbox.client import DropboxClient
from dropbox.session import DropboxSession
session = DropboxSession('sdxc6tsfnyu13r0', 'v1a4oz98ehcjt9t')
access_key, access_secret = 'sdxc6tsfnyu13r0', 'v1a4oz98ehcjt9t'  # Previously obtained OAuth 1 credentials
session.set_token(access_key, access_secret)
client = DropboxClient(session)
token = client.create_oauth2_access_token()
print (token)
