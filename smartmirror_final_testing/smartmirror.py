# smartmirror.py
# requirements
# requests, feedparser, traceback, Pillow
from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from Tkinter import *
import locale
import threading
import time
import requests
import json
import traceback
import feedparser

from PIL import Image, ImageTk
from contextlib import contextmanager
import calendar


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

LOCALE_LOCK = threading.Lock()

ui_locale = '' # e.g. 'fr_FR' fro French, '' as default
time_format = 24 # 12 or 24
date_format = "%b %d, %Y" # check python doc for strftime() for options
news_country_code = 'us'
weather_api_token = '<TOKEN>' # create account at https://darksky.net/dev/
weather_lang = 'en' # see https://darksky.net/dev/docs/forecast for full list of language parameters values
weather_unit = 'us' # see https://darksky.net/dev/docs/forecast for full list of unit parameters values
latitude = 38.6518 # Set this if IP location lookup does not work for you (must be a string)
longitude = 104.07642 # Set this if IP location lookup does not work for you (must be a string)
xlarge_text_size = 60
large_text_size = 40
medium_text_size = 20
small_text_size = 12

@contextmanager
def setlocale(name): #thread proof function to work with locale
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)

# maps open weather icons to
# icon reading is not impacted by the 'lang' parameter
icon_lookup = {
    'Clear': "assets/Sun.png",  # clear sky day
    'wind': "assets/Wind.png",   #wind
    'Clouds': "assets/Cloud.png",  # cloudy day
    'PartialCoulds': "assets/PartlySunny.png",  # partly cloudy day
    'Rain': "assets/Rain.png",  # rain day
    'Snow': "assets/Snow.png",  # snow day
    'Snow': "assets/Snow.png",  # sleet day
    'Fog': "assets/Haze.png",  # fog day
    # 'Clear': "assets/Moon.png",  # clear sky night
    # 'Clouds': "assets/PartlyMoon.png",  # scattered clouds night
    # 'Thunderstorm': "assets/Storm.png",  # thunderstorm
    # 'Tornado': "assests/Tornado.png",    # tornado
    # 'hail': "assests/Hail.png"  # hail
}


class Clock(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        # initialize time label
        self.time1 = ''
        self.timeLbl = Label(self, font=('Helvetica', large_text_size), fg="white", bg="black")
        self.timeLbl.pack(side=TOP, anchor=E)
        # initialize day of week
        self.day_of_week1 = ''
        self.dayOWLbl = Label(self, text=self.day_of_week1, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.dayOWLbl.pack(side=TOP, anchor=E)
        # initialize date label
        self.date1 = ''
        self.dateLbl = Label(self, text=self.date1, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.dateLbl.pack(side=TOP, anchor=E)
        self.tick()

    def tick(self):
        with setlocale(ui_locale):
            if time_format == 12:
                time2 = time.strftime('%I:%M %p') #hour in 12h format
            else:
                time2 = time.strftime('%H:%M') #hour in 24h format

            day_of_week2 = time.strftime('%A')
            date2 = time.strftime(date_format)
            # if time string has changed, update it
            if time2 != self.time1:
                self.time1 = time2
                self.timeLbl.config(text=time2)
            if day_of_week2 != self.day_of_week1:
                self.day_of_week1 = day_of_week2
                self.dayOWLbl.config(text=day_of_week2)
            if date2 != self.date1:
                self.date1 = date2
                self.dateLbl.config(text=date2)
            # calls itself every 200 milliseconds
            # to update the time display as needed
            # could use >200 ms, but display gets jerky
            self.timeLbl.after(200, self.tick)


class Weather(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.temperature = ''
        self.forecast = ''
        self.location = ''
        self.humidity = ''
        self.currently = ''
        self.icon = ''
        self.degreeFrm = Frame(self, bg="black")
        self.degreeFrm.pack(side=TOP, anchor=W)
        self.temperatureLbl = Label(self.degreeFrm, font=('Helvetica', xlarge_text_size), fg="white", bg="black")
        self.temperatureLbl.pack(side=LEFT, anchor=N)

        self.humidityLbl = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.humidityLbl.pack(side=TOP, anchor=W)

        self.iconLbl = Label(self.degreeFrm, bg="black")
        self.iconLbl.pack(side=LEFT, anchor=N, padx=20)
        self.currentlyLbl = Label(self, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.currentlyLbl.pack(side=TOP, anchor=W)
        # self.forecastLbl = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black")
        # self.forecastLbl.pack(side=TOP, anchor=W)
        self.locationLbl = Label(self, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.locationLbl.pack(side=TOP, anchor=W)
        self.get_weather()

    def get_ip(self):
        try:
            ip_url = "http://jsonip.com/"
            req = requests.get(ip_url)
            ip_json = json.loads(req.text)
            return ip_json['ip']
        except Exception as e:
            traceback.print_exc()
            return "Error: %s. Cannot get ip." % e

    def get_weather(self):
        try:
            city= 'Suzhou'  # Change the city for your desired weather info
            location2 = city
            url="https://openweathermap.org/data/2.5/weather?q={}&appid=439d4b804bc8187953eb36d2a8c26a02".format(city)
            res=requests.get(url)
            weather_obj = res.json()

            weather_status=weather_obj['weather'][0]['description']
            temprature=weather_obj['main']['temp']
            humidity=weather_obj['main']['humidity']
            wind_speed=weather_obj['wind']['speed']
            cloudiness=weather_obj['clouds']['all']

            degree_sign= u'\N{DEGREE SIGN}'
            temperature2 = "%s%sC" % (str(temprature), degree_sign)
            currently2 = weather_status
            humidity2 = humidity

            wind_threshold = 5
            # forecast2 = weather_obj["hourly"]["summary"]
            # Determine the wind level
            if  int(wind_speed) > wind_threshold :
                icon_id = 'wind'
                icon2 = None
            else:
                icon_id = weather_obj['weather'][0]['main']
                icon2 = None

            if  icon_id == 'Clouds' :
                if cloudiness > 50:
                    icon_id = 'Clouds'
                else :
                    icon_id = 'PartialCoulds'
            else:
                icon_id = weather_obj['weather'][0]['main']
                icon2 = None

            if icon_id in icon_lookup:
                icon2 = icon_lookup[icon_id]

            if icon2 is not None:
                if self.icon != icon2:
                    self.icon = icon2
                    image = Image.open(icon2)
                    image = image.resize((100, 100), Image.ANTIALIAS)
                    image = image.convert('RGB')
                    photo = ImageTk.PhotoImage(image)

                    self.iconLbl.config(image=photo)
                    self.iconLbl.image = photo
            else:
                # remove image
                self.iconLbl.config(image='')

            if self.currently != currently2:
                self.currently = currently2
                self.currentlyLbl.config(text=currently2)
            # if self.forecast != forecast2:
            #     self.forecast = forecast2
            #     self.forecastLbl.config(text=forecast2)
            if self.temperature != temperature2:
                self.temperature = temperature2
                self.temperatureLbl.config(text=temperature2)
            if self.humidity != humidity2:
                self.humidity = humidity2
                self.humidityLbl.config(text='Humidity:'+str(humidity2))

            if self.location != location2:
                if location2 == ", ":
                    self.location = "Cannot Pinpoint Location"
                    self.locationLbl.config(text="Cannot Pinpoint Location")
                else:
                    self.location = location2
                    self.locationLbl.config(text=location2)
        except Exception as e:
            traceback.print_exc()
            print("Error: %s. Cannot get weather." % e)

        self.after(600000, self.get_weather)

    @staticmethod
    def convert_kelvin_to_fahrenheit(kelvin_temp):
        return 1.8 * (kelvin_temp - 273) + 32


class News(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.config(bg='black')
        self.title = 'News' # 'News' is more internationally generic
        self.newsLbl = Label(self, text=self.title, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.newsLbl.pack(side=TOP, anchor=W)
        self.headlinesContainer = Frame(self, bg="black")
        self.headlinesContainer.pack(side=TOP)
        self.get_headlines()

    def get_headlines(self):
        try:
            # remove all children
            for widget in self.headlinesContainer.winfo_children():
                widget.destroy()
            if news_country_code == None:
                headlines_url = "https://news.google.com/news?ned=us&output=rss"
            else:
                headlines_url = "https://news.google.com/news?ned=%s&output=rss" % news_country_code

            feed = feedparser.parse(headlines_url)

            for post in feed.entries[0:5]:
                headline = NewsHeadline(self.headlinesContainer, post.title)
                headline.pack(side=TOP, anchor=W)
        except Exception as e:
            traceback.print_exc()
            print("Error: %s. Cannot get news." % e)

        self.after(600000, self.get_headlines)


class NewsHeadline(Frame):
    def __init__(self, parent, event_name=""):
        Frame.__init__(self, parent, bg='black')

        image = Image.open("assets/Newspaper.png")
        image = image.resize((10, 10), Image.ANTIALIAS)
        image = image.convert('RGB')
        photo = ImageTk.PhotoImage(image)

        self.iconLbl = Label(self, bg='black', image=photo)
        self.iconLbl.image = photo
        self.iconLbl.pack(side=LEFT, anchor=N)

        self.eventName = event_name
        self.eventNameLbl = Label(self, text=self.eventName, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.eventNameLbl.pack(side=LEFT, anchor=N)


class Calendar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.title = 'Calendar Events (Deadlines)'
        self.calendarLbl = Label(self, text=self.title, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.calendarLbl.pack(side=TOP, anchor=W)
        self.calendarEventContainer = Frame(self, bg='black')
        self.calendarEventContainer.pack(side=TOP, anchor=W)
        self.get_events()

    def get_events(self):
        # reference from https://developers.google.com/google-apps/calendar/quickstart/python

        # remove all children
        for widget in self.calendarEventContainer.winfo_children():
            widget.destroy()

        calendar_event = CalendarEvent(self.calendarEventContainer)
        calendar_event.pack(side=TOP, anchor=W)
        pass
 

class CalendarEvent(Frame):
    def __init__(self, parent, event_name="Event 1"):
        #Prints the start and name of the next 10 events on the user's calendar using the Google Calendar API
        creds = None
        # File 'token.pickle' stores the user's access and refresh tokens
        # created automatically when the authorization flow completes for the first
        # time.

        # Get authorization from the user for the first time 
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('calendar', 'v3', credentials=creds)
        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        # print('Getting the upcoming 10 events')   # test the obatining process
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                            maxResults=20, singleEvents=True,
                                            orderBy='startTime').execute()
        events = events_result.get('items', [])

        Frame.__init__(self, parent, bg='black')
        if not events:
            self.eventName = 'No upcoming deadlines.'
            self.eventNameLbl = Label(self, text=self.eventName, font=('Helvetica', small_text_size), fg="white", bg="black")
            self.eventNameLbl.pack(side=TOP, anchor=W)
            # print('No upcoming events')   #test the printing format
        for event in events:
            start = event['start']['dateTime']  #obtain the info of start time & date
            date_time = start.encode('utf-8')   #encode to string
            date_time = date_time.replace(':00+08:00','').replace('T','\t') #modify the printed format
            # print(start)   #test the printing format
            self.eventName = date_time + event['summary']
            self.eventNameLbl = Label(self, text=self.eventName, font=('Helvetica', small_text_size), fg="white", bg="black")
            self.eventNameLbl.pack(side=TOP, anchor=W)

class LocalCalendar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        # initialize time label
#        self.time1 = ''
#        self.timeLbl = Label(self, font=('Helvetica', large_text_size), fg="white", bg="black")
#        self.timeLbl.pack(side=TOP, anchor=E)
        # initialize day of week
#        self.day_of_week1 = ''
#        self.dayOWLbl = Label(self, text=self.day_of_week1, font=('Helvetica', small_text_size), fg="white", bg="black")
#        self.dayOWLbl.pack(side=TOP, anchor=E)
        # initialize date label
        self.date1 = ''
        self.dateLbl = Label(self, text=self.date1, font=('Courier New', medium_text_size), fg="white", bg="black")
        # medium_text_size
        self.dateLbl.pack(side=TOP, anchor=E)
        self.tick()

    def tick(self):
        with setlocale(ui_locale):
            if time_format == 12:
                time2 = time.strftime('%I:%M %p') #hour in 12h format
            else:
                time2 = time.strftime('%H:%M') #hour in 24h format

#            day_of_week2 = time.strftime('%A')
#            date2 = time.strftime(date_format)
#       date2=calendar.calendar(2020,5)
        y = int(time.strftime('%Y',time.localtime(time.time())))
        m = int(time.strftime('%m',time.localtime(time.time())))
        date2=calendar.month(y, m, 2, 1)

        self.dateLbl.config(text=date2)
            # if time string has changed, update it
#            if time2 != self.time1:
#                self.time1 = time2
#                self.timeLbl.config(text=time2)
#            if day_of_week2 != self.day_of_week1:
#                self.day_of_week1 = day_of_week2
#                self.dayOWLbl.config(text=day_of_week2)
#            if date2 != self.date1:
#                self.date1 = calendar.calendar(2020,5)
#                self.dateLbl.config(text=date2)
            # calls itself every 200 milliseconds
            # to update the time display as needed
            # could use >200 ms, but display gets jerky
#            self.timeLbl.after(200, self.tick)
#            

class FullscreenWindow:

    def __init__(self):
        self.tk = Tk()
        self.tk.configure(background='black')
        self.topFrame = Frame(self.tk, background = 'black')
        self.bottomFrame = Frame(self.tk, background = 'black')
        self.topFrame.pack(side = TOP, fill=BOTH, expand = YES)
        self.bottomFrame.pack(side = BOTTOM, fill=BOTH, expand = YES)
        self.state = False
        self.tk.bind("<Return>", self.toggle_fullscreen)
        self.tk.bind("<Escape>", self.end_fullscreen)
        # clock     (Upper-right corner)
        self.clock = Clock(self.topFrame)
        self.clock.pack(side=RIGHT, anchor=N, padx=100, pady=60)

        # widget.config(height=3, width=20)
        # weather   (Upper-left corner)
        # @@@@@@@@@@@@@@@@@@@@@@@@@@
        self.weather = Weather(self.topFrame)
        self.weather.pack(side = LEFT, anchor=N, padx=100, pady=60)
        # news      (Lower-right corner)
        # self.news = News(self.bottomFrame)
        # self.news.pack(side=RIGHT, anchor=S, padx=100, pady=60)
        # calender  (Lower-left corner)
        # @@@@@@@@@@@@@@@@@@@@@@@@@@
        self.calender = Calendar(self.bottomFrame)
        self.calender.pack(side=LEFT, anchor=S, padx=100, pady=60)
        
        self.localcalender = LocalCalendar(self.bottomFrame)
        self.localcalender.pack(side=RIGHT, anchor=N, padx=100, pady=60)
        

    def toggle_fullscreen(self, event=None):
        self.state = not self.state  # Just toggling the boolean
        self.tk.attributes("-fullscreen", self.state)
        return "break"

    def end_fullscreen(self, event=None):
        self.state = False
        self.tk.attributes("-fullscreen", False)
        return "break"

if __name__ == '__main__':
    w = FullscreenWindow()
    w.tk.mainloop()
