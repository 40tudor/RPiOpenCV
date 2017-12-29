# Module to connect to dropbox account and upload a file

from dropbox.client import DropboxClient


def connect_dropbox():
        # connect to dropbox with access token
        client = DropboxClient("Bpd1KPrWBgAAAAAAAAAAft9Wxbo-NUL2DOu7Slf0uZiyWugUdHQAP0VkPV4aVBhH")
        print ("[SUCCESS] dropbox account linked")

def upload_dropbox(f_path,filename):
        print ("path=", f_path, filename)
        db_path = "/Motion"
        print ("[UPLOAD] {}".format(filename))
        fileID = f_path + filename
        response = client.put_file(db_path, open(fileID, "rb"))
        print("[UPLOADED] {}".format(response))


