from Settings import App
from datetime import datetime
from MyLogging import Logging
import requests

class TimeSwitch():
    times : list

    def __init__(self, times : list ):
        self.times = times

    def isOn(self, now : datetime.time):
        for time in self.times:
            onTime = time.on.hour * 60 + time.on.minute
            offTime =  time.off.hour * 60 + time.off.minute
            if 0 == offTime:
                offTime = 24 * 60
            timestamp = now.hour * 60 + now.minute

            if timestamp > onTime and timestamp < offTime:
                return True, time.soc
        return False, 0

class Consumer():
    prio : int
    mode : str # Settings.E_MODE
    soc : int
    name : str
    __dns : str
    timeswitch : TimeSwitch
    logger : Logging
    timestampOn : int
    prohibitCounter: int
    maxSoftProhibits = 5

    def __init__(self, settings : App, logger : Logging):
        self.name = settings.name
        self.__dns = settings.dns
        self.mode = settings.mode
        self.prio = settings.prio
        self.logger = logger
        self.timestampOn = 0
        self.minTime = 0
        self.prohibitCounter = 0
        self.soc = settings.soc

        if settings.minTimeRunningMinutes:
            self.minTime = int(settings.minTimeRunningMinutes)
        if  0 < len(settings.timers):
            self.timeswitch = TimeSwitch(settings.timers)
        else:
            self.timeswitch = None

        self.isOn = False
        if 'On' == self.mode:
            self.isOn = True


    def approve(self, soc : int):
        oldState = self.isOn
        oldSoc = self.soc

        self.prohibitCounter = 0
        if not 'Auto' == self.mode:
            return (self.isOn != oldState)
        if self.timeswitch:
            self.isOn, self.soc = self.timeswitch.isOn(datetime.now().time())
        else:
            self.isOn = True

        if oldSoc != self.soc:
            self.logger.Debug("Change SOC of " + self.name + " by timeswitch from " + str(oldSoc) + "% to " + str(self.soc) + "%")

        #ausschalten wenn min soc unterschritten
        if self.soc > soc:
            self.isOn = False

        if self.isOn and (oldState != self.isOn):
            self.logger.Debug("Switch on " + self.name)

        if not self.isOn and (oldState != self.isOn):
            self.logger.Debug("Switch off " + self.name)

        return (self.isOn != oldState)

    def prohibit(self, force : bool):
        self.prohibitCounter +=1
        ret = False
        if force or (self.maxSoftProhibits < self.prohibitCounter):
            if 'Auto' == self.mode:
                ret = self.isOn
                self.isOn = False
        return ret

    def push(self):
        response = None
        if self.isOn:
            cmd = "on"
        else:
            cmd = "off"
        try:
            self.logger.Debug("send command to " + self.__dns + ": " + cmd)
            self.logger.Debug(self.__dns + "/cm?cmnd=Power%20" + cmd)
            response = requests.get("http://" + self.__dns + "/cm?cmnd=Power%20" + cmd)
            if 200 != response.status_code:
                raise Exception
        except Exception:
            self.logger.Error("No connection to " + self.name + "(DNS: " + self.__dns + ")")
            if response:
                self.logger.Error("Response: " + str(response))



    def onTime(self):
        return datetime.now().timestamp() - self.timestampOn
