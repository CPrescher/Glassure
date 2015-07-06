# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'



class Observable(object):
    def __init__(self):
        self.observer = []
        self.notification = True

    def subscribe(self, function):
        self.observer.append(function)

    def unsubscribe(self, function):
        try:
            self.observer.remove(function)
        except ValueError:
            pass

    def notify(self):
        if self.notification:
            for observer in self.observer:
                observer()

    def turn_off_notification(self):
        self.notification = False

    def turn_on_notification(self):
        self.notification = True