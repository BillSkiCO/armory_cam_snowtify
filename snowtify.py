from threading import Thread, Event
import time
import math
import constant
import queue
import requests
import api

# Set shared queue for thread of size 1 to hold notification trigger
notif_q = queue.Queue(1)


#
# Producer Thread for notifications
#
class EventWindow(Thread):

    # Class Constants
    WAIT_TIME = 1.0  # Number of seconds to wait for next task

    # Class Variables
    _notify_window = constant.NOTIFY_EVENT_WINDOW_SECS
    _notify_threshold = constant.NOTIFY_EVENT_WINDOW_SECS * constant.NOTIFY_THRESHOLD
    _no_snow_threshold = constant.NOTIFY_EVENT_WINDOW_SECS * constant.NOT_SNOWING_THRESHOLD
    _snow_event_handler = False
    _snow_events = 0          # How many snow detections has there been
    _no_snow_events = 0       # How many no snow detections has there been
    _is_it_snowing = False    # Boolean for is it snowing or not
    _refractory_timer = 0     # How long has it been since it's stopped snowing, after notification

    def __init__(self, event):
        Thread.__init__(self)
        self.stopped = event

        # Set refractory period to max to allow for instant notification
        self._refractory_timer = constant.NOTIF_REFRACTORY_SECS

    def run(self):

        # Run task every second
        while not self.stopped.wait(self.WAIT_TIME):

            # Start pseudo circular buffer logic once we collect enough data points
            # keep snow events + no snow events at _notify_window's value
            # Since we are looping every second, we can assume snow & no snow
            # are updated every second. We want snow + no snow = _notify_window
            # for a filled "pseudo circular buffer"

            # If (Filled circular buffer [Good!])
            if self._snow_events + self._no_snow_events >= self._notify_window:

                print("buffer full!")

                # IF ( there is a snow event to log )
                if self._snow_event_handler:

                    print("incrementing snow event!")

                    # Reset event handler and increment snow event if we havent
                    # reached maximum
                    self._snow_event_handler = False
                    if self._snow_events >= self._notify_window:
                        self._snow_events = self._notify_window
                    else:
                        self._snow_events += 1

                    # Decrement no snow event, but make sure
                    # no snow events stays positive
                    if self._no_snow_events > 0:
                        self._no_snow_events -= 1

                # ELSE ( No snow event to log! )
                else:

                    # Increment no snow event only if below _notify_window value
                    if self._no_snow_events >= self._notify_window:
                        self._no_snow_events = self._notify_window
                    else:
                        self._no_snow_events += 1

                    # Decrement snow event, but make sure
                    # snow events stays positive
                    if self._snow_events > 0:
                        self._snow_events -= 1

                ################################################################
                #
                # All values now up to date for this second
                #
                ################################################################

                print("snow events: " + str(self._snow_events))
                print("no snow events: " + str(self._no_snow_events))

                # Determine if it is snowing
                if self._snow_events >= self._notify_threshold:

                    # Its snowing!
                    self._is_it_snowing = True

                    # IF an acceptable amount no snow time has passed
                    if self._refractory_timer >= constant.NOTIF_REFRACTORY_SECS:

                        # Send Notification
                        self.send_notification()

                    # Reset refractory timer to 0. It's snowing again!
                    self._refractory_timer = 0

                # Determine if it is not snowing for refractory timer
                elif self._no_snow_events >= self._no_snow_threshold:
                    self._is_it_snowing = False

                    # IF we haven't hit the threshold yet
                    if self._refractory_timer <= constant.NOTIF_REFRACTORY_SECS:
                        self._refractory_timer += 1

            # else (Circular buffer not filled [Sad!])
            else:

                if self._snow_event_handler:
                    # Reset event handler and increment snow event
                    self._snow_event_handler = False
                    self._snow_events += 1
                else:
                    self._no_snow_events += 1

    def increment_snow_event(self):
        self._snow_event_handler = True
        print("logged snow event!")

    @staticmethod
    def send_notification():

        print("SEND THE NOTIFICATION!")

        # Add notification to notification queue
        # Just passing value True at this time. Could pass object holding analytics
        notif_q.put(True)


#
# Notification Consumer Thread
#
class NotificationThread(Thread):

    def __init__(self, event):
        Thread.__init__(self)
        self.stopped = event

    def run(self):

        # Monitor for event
        while True:
            if not notif_q.empty():

                # Get the item from the queue (which clears queue)
                notif_event = notif_q.get()

                # Send notification
                self.send_notification(notif_event)
            time.sleep(1)

    @staticmethod
    def send_notification(notif_event):

        success = False

        while success is not True:

            # Send to yo!
            try:
                # requests.post("http://api.justyo.co/yo/", data={'api_token': api.YO_API, 'username': api.JOHN_UN,
                #                                                 'link': 'www.armorycam.com'})
                requests.post("http://api.justyo.co/yo/", data={'api_token': api.YO_API, 'username': api.BILL_UN,
                                                                'link': 'www.armorycam.com'})
                success = True

            except Exception:
                print("Could not send yo!")


class Snowtification():

    _event_window = None
    _snow_event = False
    _notification_threshold = math.floor(constant.NOTIFY_EVENT_WINDOW_SECS * constant.NOTIFY_THRESHOLD)
    _stop_flag = None
    _notif_thread = None
    _event_thread = None

    def __init__(self):

        self._snow_event = False
        self._stopFlag = Event()  # Initialize timer stop flag

        # Init Producer/Consumer Threads
        self._notif_thread = NotificationThread(self._stop_flag)
        self._event_thread = EventWindow(self._stopFlag)

        # Start Producer/Consumer Threads
        self._notif_thread.start()
        self._event_thread.start()

    def log_snow_event(self):
        self._event_thread.increment_snow_event()

    def stop_threads(self):
        self._stopFlag.set()

