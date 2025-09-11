from enum import Enum
import requests

class SonoffSwitch:

    class SwitchState(Enum):
        ON = 1
        OFF = 2
        OFFLINE = 3
        ERROR = 4

    channel = "POWER3" # POWER2
    switchDNS = "192.168.178.25"



    def __init__(self):
        pass

    def getSwitchState(self):
        try:
            response = requests.get("http://" + self.switchDNS + "/cm?cmnd=" + self.channel, timeout = 1)
        except requests.exceptions.RequestException:
            return SonoffSwitch.SwitchState.OFFLINE
        except:
            return SonoffSwitch.SwitchState.ERROR

        if 200 != response.status_code:
            return SonoffSwitch.SwitchState.ERROR
        if "OFF" ==  response.json()[self.channel]:
            return SonoffSwitch.SwitchState.OFF
        elif "ON" == response.json()[self.channel]:
            return SonoffSwitch.SwitchState.ON
        else:
            return SonoffSwitch.SwitchState.ERROR

    def switch(self, state : SwitchState):
        response = None
        try:
            if SonoffSwitch.SwitchState.ON == state:
                response = requests.get("http://" + self.switchDNS + "/cm?cmnd=" + self.channel + "%20ON", timeout = 1)
            elif SonoffSwitch.SwitchState.OFF == state:
                response = requests.get("http://" + self.switchDNS + "/cm?cmnd=" + self.channel + "%20OFF", timeout = 1)
        except requests.exceptions.RequestException:
            return SonoffSwitch.SwitchState.OFFLINE
        except:
            return SonoffSwitch.SwitchState.ERROR

        if 200 != response.status_code:
            return SonoffSwitch.SwitchState.ERROR
        self.switchState = response.json()[self.channel]
