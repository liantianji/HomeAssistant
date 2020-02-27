#!/usr/bin/env python
# encoding: utf-8
import logging
import math 
import datetime
import time

"""
Support for AirCat air sensor.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.apparent_emperature/
"""

import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import config_validation as cv
from homeassistant.const import (CONF_NAME, TEMP_CELSIUS)

_LOGGER = logging.getLogger(__name__)
_INTERVAL = 60 #同步间隔多少秒

SCAN_INTERVAL = datetime.timedelta(seconds=_INTERVAL)

DEFAULT_NAME = 'apparent_temperature'

CONF_TS = "temperature_sensor"
CONF_HS = "humidity_sensor"
CONF_HUMIDITYOFFSETS="humidity_offsets"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_TS): cv.string,
    vol.Required(CONF_HS): cv.string,
    vol.Required(CONF_HUMIDITYOFFSETS): cv.string,
})

def calc_heat_index(T, RH):
    '''NOAA计算体感温度 参数为气温(摄氏度)和相对湿度(0~100或者0~1)''' 
    if RH < 1: 
        RH *= 100 
    T = 1.8 * T + 32 
    HI = 0.5 * (T + 61 + (T - 68) * 1.2 + RH * 0.094) 
    if HI >= 80:
        HI = -42.379 + 2.04901523 * T + 10.14333127 * RH - .22475541 * T * RH \
            - .00683783 * T * T - .05481717 * RH * RH + .00122874 * T * T * RH \
            + .00085282 * T * RH * RH - .00000199 * T * T * RH * RH 
        if RH < 13 and 80 < T < 112: 
            ADJUSTMENT = (13 - RH) / 4 * math.sqrt((17 - abs(T - 95)) / 17) 
            HI -= ADJUSTMENT 
        elif RH > 85 and 80 < T < 87: 
            ADJUSTMENT = (RH - 85) * (87 - T) / 50 
            HI += ADJUSTMENT 
    return round((HI - 32) / 1.8, 2)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the sensor."""
    name = config.get(CONF_NAME)
    temperatureSensor = config.get(CONF_TS)
    humiditySensor = config.get(CONF_HS)
    humidity_offsets= config.get(CONF_HUMIDITYOFFSETS)
    # mqtt = hass.components.mqtt
    # if mqtt:
    #     logging.info('获取到mqtt')
    devs = []

    devs.append(ApparentTSensor(
        hass, temperatureSensor, humiditySensor, name,humidity_offsets=humidity_offsets))

    add_devices(devs)
    logging.info('初始化体感温度组件成功')

class ApparentTSensor(Entity):
    """Implementation of a AirCat sensor."""

    def __init__(self, hass, temperatureSensor, humiditySensor, name,humidity_offsets=None):
        """Initialize the AirCat sensor."""
        self._hass = hass
        self._name = name
        self._temperatureSensor = temperatureSensor
        self._humiditySensor = humiditySensor
        self._apparent_temperature = 0
        self._updateTime=time.strftime("%Y-%m-%d %H:%M:%S") 
        self._humidit = 0
        self._temperature=0
        self._humidity_offsets=humidity_offsets


    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return TEMP_CELSIUS

    @property
    def available(self):
        """Return if the sensor data are available."""
        return self._apparent_temperature is not 0

    @property
    def state(self):
        """返回当前的状态."""
        return self._apparent_temperature

    @property
    def state_attributes(self):
        """Return the attributes of the entity."""
        return {
        'humidit': self._humidit,
        'temperature': self._temperature,
        'humidityOffsets': self._humidity_offsets,
        'lastUpdateTime': self._updateTime

        }
    def update(self):
        self._updateTime=time.strftime("%Y-%m-%d %H:%M:%S") 
        """Update state."""
        t = 0.0
        h = 0.0
        ttry = self._hass.states.get(self._temperatureSensor).state
        htry = self._hass.states.get(self._humiditySensor).state
        try:
            t = float(ttry)
            h = float(htry) #人为调整湿度值

            if self._humidity_offsets:
                h +=float(self._humidity_offsets)

            self._temperature=t
            self._humidit=h
        except ValueError:
            _LOGGER.debug('Can not calc apparent_temperature with %s,T: %s, %s,h:%s', self._temperatureSensor,ttry,self._humiditySensor,htry)
            return
        self._apparent_temperature = calc_heat_index(t,h)
        _LOGGER.debug('%s,T: %s, %s,h:%s AT:%s', self._temperatureSensor,t,self._humiditySensor,h, self._apparent_temperature)


