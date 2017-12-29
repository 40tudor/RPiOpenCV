from picamera.array import PiRGBArray
from picamera import PiCamera
import db_upload as dbox
import time
import math
import datetime
import cv2

# Define internal functions

# place a prompt on the displayed image
def prompt_on_image(txt):
    global image
    cv2.putText(image, txt, (10, 35),
    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
     
# calculate speed from pixels and time
def get_speed(pixels, ftperpixel, secs):
    if secs > 0.0:
        return ((pixels * ftperpixel)/ secs) * 0.681818  
    else:
        return 0.0
 
# calculate elapsed seconds
def secs_diff(endTime, begTime):
    diff = (endTime - begTime).total_seconds()
    return diff    

# Define Constants

DISTANCE = 80
THRESHOLD = 15
MIN_AREA = 175
BLURSIZE = (15,15)
IMAGEWIDTH = 800
IMAGEHEIGHT = 600
RESOLUTION = [IMAGEWIDTH,IMAGEHEIGHT]
FOV = 53.5
FPS = 30
WAITING = 0
TRACKING = 1
SAVING = 2
UNKNOWN = 0
LEFT_TO_RIGHT = 1
RIGHT_TO_LEFT = 2
state = WAITING
direction = UNKNOWN

# Define Variables

initial_x = 0
last_x = 0
base_image = None
abs_chg = 0
mph = 0
secs = 0.0
show_bounds = True
showImage = False
ix,iy = -1,-1
fx,fy = -1,-1
drawing = False
setup_complete = False
tracking = False
text_on_image = 'No cars'
loop_count = 0
prompt = ''

# Calculate the the width of the image at the distance specified

frame_width_ft = 2*(math.tan(math.radians(FOV*0.5))*DISTANCE)
ftperpixel = frame_width_ft / float(IMAGEWIDTH)
print("Image width in feet {} at {} from camera".format("%.0f" % frame_width_ft,"%.0f" % DISTANCE))

#    Connect to Dropbox

dbox.connect_dropbox()

#    Initialize the camera

camera = PiCamera()
camera.resolution = RESOLUTION
camera.framerate = FPS
camera.vflip = False
camera.hflip = False

rawCapture = PiRGBArray(camera, size=camera.resolution)
time.sleep(0.9)

#    Set up capture area

upper_left_x = 4
upper_left_y = 243
lower_right_x = 785
lower_right_y = 354

monitored_width = lower_right_x - upper_left_x
monitored_height = lower_right_y - upper_left_y

#    Capture frames

for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    #initialize the timestamp
    timestamp = datetime.datetime.now()
 
    # grab the raw NumPy array representing the image 
    frame = f.array
     
    # crop area defined by [y1:y2,x1:x2]
    crop = frame[upper_left_y:lower_right_y,upper_left_x:lower_right_x]
 
    # convert it to grayscale, and blur it
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, BLURSIZE, 0)
 
    # if the base image has not been defined, initialize it
    if base_image is None:
        base_image = gray.copy().astype("float")
        lastTime = timestamp
        rawCapture.truncate(0)
        print ("Initialized...Looking for Motion")
        cv2.imshow("Speed Camera", frame)
        continue

    # accumulate the weighted average between the current frame and
    # previous frames, then compute the difference between the current
    # frame and running average
    cv2.accumulateWeighted(gray, base_image, 0.5)

    # Calculate delta and threshold
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(base_image))
    thresh = cv2.threshold(frameDelta, THRESHOLD, 255, cv2.THRESH_BINARY)[1]
  
    # dilate the thresholded image to fill in any holes, then find contours
    # on thresholded image
    thresh = cv2.dilate(thresh, None, iterations=2)
    (_, cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

#    Look for motion
    for c in cnts:
        (x, y, w, h) = cv2.boundingRect(c)
        # get an approximate area of the contour
        found_area = w*h 
        # find the largest bounding rectangle
        if (found_area > MIN_AREA) and (found_area > biggest_area):  
            biggest_area = found_area
            motion_found = True
        else:
            motion_found = False
            
#       If motion found and not already tracking, start tracking, else continue tracking

    if motion_found:
        if state == WAITING:
            # intialize tracking
            state = TRACKING
            print ('state = TRACKING')
            initial_x = x
            last_x = x
            initial_time = timestamp
            last_mph = 0
            text_on_image = 'Tracking'
            print(text_on_image)
        else:
            if state == TRACKING:       
                if x >= last_x:
                    direction = LEFT_TO_RIGHT
                    abs_chg = x + w - initial_x
                else:
                    direction = RIGHT_TO_LEFT
                    abs_chg = initial_x - x
                secs = secs_diff(timestamp,initial_time)
                mph = get_speed(abs_chg,ftperpixel,secs)
                print("--> count={} chg={}  secs={}  mph={} this_x={} w={} ".format(loop_count,abs_chg,secs,"%.0f" % mph,x,w))
                real_y = upper_left_y + y
                real_x = upper_left_x + x
                # is front of object outside the monitored boundary? Then write date, time and speed on image
                # and save it 
                if mph > 10 and (((x <= 2) and (direction == RIGHT_TO_LEFT)) \
                        or ((x+w >= monitored_width - 2) \
                        and (direction == LEFT_TO_RIGHT))):
                    # timestamp the image
                    cv2.putText(image, datetime.datetime.now().strftime("%A %d %B %Y %I:%M:%S%p"),
                        (10, image.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 1)
                    # write the speed: first get the size of the text
                    size, base = cv2.getTextSize( "%.0f mph" % last_mph, cv2.FONT_HERSHEY_SIMPLEX, 2, 3)
                    # then center it horizontally on the image
                    cntr_x = int((IMAGEWIDTH - size[0]) / 2) 
                    cv2.putText(image, "%.0f mph" % mph,
                        (cntr_x , int(IMAGEHEIGHT * 0.2)), cv2.FONT_HERSHEY_SIMPLEX, 2.00, (0, 255, 0), 3)
                    # and save the image to disk
                    cv2.imwrite("car_at_"+datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+".jpg",
                        image)
                    dbox.upload_dropbox("~/Motion",TempImage)
#           Write mph and timestamp to logfile
                    state = SAVING
                    print ('state = SAVING')
                    print ('Saved image at {}mph'.format("%.0f" % mph))
                # if the object hasn't reached the end of the monitored area, just remember the speed 
                # and its last position
                last_mph = mph
                last_x = x
    else:
        if state != WAITING:
            state = WAITING
            print ("state = WAITING")
            direction = UNKNOWN
            text_on_image = 'No Car Detected'
            print(text_on_image)
            loop_count = 0
            print ("reset loop_count")

    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)
    loop_count = loop_count + 1
  
# cleanup the camera and close any open windows
print("Quitting")
cv2.destroyAllWindows()
