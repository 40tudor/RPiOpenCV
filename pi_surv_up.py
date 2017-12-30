#!/usr/bin/env/python3

# import the necessary packages
import dropbox
import os
import sys

dropbox_key = "jycn2bee3hmeeoa"
dropbox_secret = "spaexmph5biaydc"
access_token = "Bpd1KPrWBgAAAAAAAAGJh5-do1kNYOJTT_8VowQ45vkpmKecNlLHiNDTI8TgOyBI"
dropbox_base_path = "/Motion"

filecount=0

print ("[CHECK] looking for .jpg files")
for filename in os.listdir("."):
	if filename.endswith(".jpg"):
		filecount=filecount+1

print ("[CHECK] found {} files".format(filecount))

if filecount > 0:
	try:
		client = dropbox.Dropbox(access_token)
		print ("[SUCCESS] dropbox account linked")
	except dropbox.exceptions.ApiError as msg:
		print ("[FAIL] {}".format(msg))
		sys.exit(2)
else:
	sys.exit()

#for entry in client.files_list_folder('').entries:
#    print(entry.name)

for filename in os.listdir("."):
	if filename.endswith(".jpg"):
	# upload the image to Dropbox and cleanup the tempory image
		print ("[UPLOADING] {} to {}".format(filename,dropbox_base_path))
		path = "{base_path}/{filename}".format(base_path=dropbox_base_path, filename=filename)

		try:
			with open(filename, 'rb') as f:
				response = client.files_upload(f, path, mode=dropbox.files.WriteMode.overwrite,mute=True)
			print("[UPLOADED]")
			os.remove(filename)
		except Exception as msg:
			print("[UPLOAD FAILED] {}".format(msg))
			break
