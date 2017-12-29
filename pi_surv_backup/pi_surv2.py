# import the necessary packages
from surv.TempImage import TempImage
import dropbox
#from dropbox.client import DropboxOAuth2FlowNoRedirect
#from dropbox.client import DropboxClient
from picamera.array import PiRGBArray
from picamera import PiCamera
import argparse
import warnings
import datetime
import json
import time
import cv2
import socket
import sys

# function to check internet connection
def check_internet(host="8.8.8.8", port=53, timeout=10):
	try:
		print("[CHECKING INTERNET]")
		socket.setdefaulttimeout(timeout)
		socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
		print("[INTERNET UP]")
		return True
	except socket.error as msg:
		print("[INTERNET DOWN] :: {}".format(msg))
		return False

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="path to the JSON configuration file")
args = vars(ap.parse_args())
# print(args["conf"])

# filter warnings, load the configuration and initialize the Dropbox
# client
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
client = None

# check to see if the Dropbox should be used

if conf["use_dropbox"]:
	if check_internet():
		try:
			client = dropbox.Dropbox(conf["access_token"])
			print ("[SUCCESS] dropbox account linked")
		except dropbox.exceptions.ApiError as msg:
			print ("[FAIL] {}".format(msg))
			sys.exit(2)

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

# allow the camera to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print ("[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

# capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
	# grab the raw NumPy array representing the image and initialize
	# the timestamp and occupied/unoccupied text
	frame = f.array
	timestamp = datetime.datetime.now()
	text = "Unoccupied"
	# resize the frame, convert it to grayscale, and blur it
	height, width = frame.shape[:2]
	scale = width/500
##	smallframe = cv2.resize(frame,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC)
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	gray = cv2.GaussianBlur(gray, (21, 21), 0)

	# if the average frame is None, initialize it
	if avg is None:
		print ("[INFO] starting background model...")
		avg = gray.copy().astype("float")
		rawCapture.truncate(0)
		continue

	# accumulate the weighted average between the current frame and
	# previous frames, then compute the difference between the current
	# frame and running average
	cv2.accumulateWeighted(gray, avg, conf["averaging"])
	frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

	# threshold the delta image, dilate the thresholded image to fill
	# in holes, then find contours on thresholded image
	thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
	thresh = cv2.dilate(thresh, None, iterations=2)
	cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]


	# loop over the contours
	for c in cnts:
		# if the contour is too small, ignore it
		if cv2.contourArea(c) < conf["min_area"]:
#			print ("Contour size: ",cv2.contourArea(c))
			continue

		# compute the bounding box for the contour, draw it on the frame,
		# and update the text
		print ("Contour Size: ",cv2.contourArea(c))
		print ("Motion Counter: ",motionCounter)
		(x, y, w, h) = cv2.boundingRect(c)
		cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
		text = "Occupied"
		# increment the motion counter
		motionCounter += 1

		# draw the text and timestamp on the frame
		ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
		cv2.putText(frame, "Room Status: {}".format(text), (10, 20),
			cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 255), 1)
		cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_PLAIN,
			2, (255, 255, 255), 1)

	# check to see if the room is occupied
	if text == "Occupied":
		# check to see if enough time has passed between uploads
		if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
			# check to see if the number of frames with consistent motion is
			# high enough
			if motionCounter >= conf["min_motion_frames"]:
				# check to see if dropbox should be used
				if conf["use_dropbox"]:
					# write the image to temporary file
					t = TempImage()
					# print(t.path)
					cv2.imwrite(t.path, frame)
					# look = input("look for file")

					# upload the image to Dropbox and cleanup the tempory image
					print ("[UPLOADING] {}".format(ts))
					path = "{base_path}/{timestamp}.jpg".format(
						base_path=conf["dropbox_base_path"], timestamp=ts)
					# print ("dbxpath = {}".format(path))
					if check_internet():
						try:
							response = client.files_upload(open(t.path,'rb'),path)
							print("[UPLOADED]")
						except dropbox.exceptions.ApiError as msg:
							print("[UPLOAD FAILED] {}".format(msg))
					else:
						print("[UPLOAD FAILED] Internet down")

				t.cleanup() 

				# update the last uploaded timestamp and reset the motion
				# counter
				lastUploaded = timestamp
				motionCounter = 0

	# otherwise, the room is not occupied
	else:
		motionCounter = 0
		#print("Motion Counter Reset")

	# check to see if the frames should be displayed to screen
	if conf["show_video"]:
		# display the security feed
		cv2.namedWindow("Security Feed", cv2.WINDOW_NORMAL)
		cv2.imshow("Security Feed", frame)
		key = cv2.waitKey(1) & 0xFF

		# if the `q` key is pressed, break from the loop
		if key == ord("q"):
			break

	# clear the stream in preparation for the next frame
	rawCapture.truncate(0)
