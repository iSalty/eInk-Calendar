#TESTER PYTHON
from __future__ import print_function
import _datetime
import pickle
from pytz import timezone
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import math
import time
import logging
import numpy as np
from waveshare_epd import epd2in7
from PIL import Image,ImageDraw,ImageFont,ImageChops

SECTION_HEIGHT = 30 #pixels
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly'] # If modifying these scopes, delete the file token.pickle.

logging.basicConfig(level=logging.INFO) #print INFO - if you want more detail use DEBUG

def getTodaysEvents():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        print("Opening token.pickle")
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Need to refresh creds.")
            creds.refresh(Request())
        else:
            print("Enter credentials...")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    tz = timezone('EST')
    startTime = _datetime.datetime.today().isoformat() + 'Z' # 'Z' indicates UTC time
    startTime = startTime[0:11] + '08:00:00.000000' + 'Z' # always start at 8am
    events_result = service.events().list(calendarId='primary', timeMin=startTime, maxResults=10, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    todaysEvents = {8:'',9:'',10:'',11:'',12:'',13:'',14:'',15:''} # init dictionary 
    if not events:
        print('No upcoming events found.')
    
    prevStartHour = 0
    for event in events:
        #print(event)
        start = event['start'].get('dateTime', event['start'].get('date'))
        startHour = int(start[11:13])
        if startHour == prevStartHour:   # if you already got an event this hour: skip
            continue
        todaysEvents[startHour] = event['summary']

        prevStartHour = startHour
    
    return todaysEvents


try:
    ## GET CALENDAR LIST AND SEE IF IT HAS CHANGED ##

    
    ## LOAD FONTS ##
    logging.info(" Loading Fonts")
    fontDir = '/home/pi/Projects/eInk/fonts'
    font24 = ImageFont.truetype(os.path.join(fontDir, 'waveshare_default.ttc'), 24)
    font18 = ImageFont.truetype(os.path.join(fontDir, 'waveshare_default.ttc'), 18)
    fontBillion = ImageFont.truetype(os.path.join(fontDir, 'BillionDreams.ttf'), 24)    
    
    epd = epd2in7.EPD() #define EPD variable 2.7" dsiplay

    logging.info(" Init and clear display")
    epd.init()      #init the display
    epd.Clear(0xFF) #clears display of any previous image

    #print("Width:",epd.width,"\nHeight:",epd.height)

    logging.info(" Creating blank picture of right dimensions")
    image = Image.new('1', (epd.width, epd.height), 255)  #fully white binary image to start 
    draw = ImageDraw.Draw(image)


    ### ADD TITLE TO IMAGE ###
    logging.info(" Draw Title")
    draw.text((25,0), 'CALENDAR', font=fontBillion, fill=0 )  #add title to top of display


    ### DRAW LINES TO DIVIDE BY HOUR AND LABEL ###
    logging.info(" Draw lines to divide work hours")
    hour = hourTextW = hourTextH = textW = textH = startPixel = 0 #init vars
    task = '' #init var
    taskList = getTodaysEvents()
    elipsesW, elispsisH = draw.textsize('...', font=font18)
    for i in range(1,9):
        hour = 7+i
        if hour >= 13:
            hour = hour-12

        draw.text((2,i*SECTION_HEIGHT+5), str(hour), font=font18, fill=0)  #draw text (hour of day)
        draw.line((0,i*SECTION_HEIGHT,epd.width,i*SECTION_HEIGHT), width=2)
        
        ### PUT TASK SUMMARY IN HOUR SECTIONS ###
        task = taskList[7+i]
        if task != '':
            hourTextW, hourTextH = draw.textsize(str(hour), font=font18) 
            textW, textH = draw.textsize(task, font=font18) #gets length of string in pixels
            startPixel = math.ceil(((epd.width-hourTextW)/2+hourTextW)-(textW/2))
            if startPixel < 35: #limit startPixel to not overlap the hour number
                startPixel = 35

                if textW > (epd.width-35): #if summary is going off of screen place '...'
                    cutChar = len(task)-1
                    newTextW = textW
                    newTextH = textH
                    while newTextW > epd.width-35-elipsesW:
                        newTextW, newTextH = draw.textsize(task[0:cutChar], font=font18)
                        task = task[0:cutChar] + '...'
                        
                        cutChar = cutChar-1
                    
            #draw the text onto the image
            draw.text((startPixel,i*SECTION_HEIGHT+5), task, font=font18, fill=0)

    
    ### INVERT COLOR CURRENT TIME SECTION ###
    logging.info(" Invert color of current time section")
    timeNow = time.localtime() #get current time
    if timeNow.tm_hour >= 8 and timeNow.tm_hour <= 15:  #timeNow.tm_hour - use when not testing
        editSection = timeNow.tm_hour - 7

        logging.info(" Crop, invert color, and paste section")
        cropSection = image.crop((0,editSection*SECTION_HEIGHT+2,epd.width,(editSection+1)*SECTION_HEIGHT))
        invertedCrop = ImageChops.invert(cropSection)
        image.paste(invertedCrop, (0,editSection*SECTION_HEIGHT+2,epd.width,(editSection+1)*SECTION_HEIGHT))            
                

    ### SEND IMAGE TO DISPLAY ###
    logging.info(" Send image buffer to display")
    epd.display(epd.getbuffer(image)) #send image to display
    time.sleep(2)

    logging.info(" Putting display to sleep")
    epd.sleep() #put display to sleep (low power mode)

except IOError as e:
    print("Error occurred:",e)
    
except KeyboardInterrupt:    
    epd2in7.epdconfig.module_exit()
    exit()