"""
cBLUE (comprehensive Bathymetric Lidar Uncertainty Estimator)
Copyright (C) 2019
Oregon State University (OSU)
Center for Coastal and Ocean Mapping/Joint Hydrographic Center, University of New Hampshire (CCOM/JHC, UNH)
NOAA Remote Sensing Division (NOAA RSD)

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

Contact:
Christopher Parrish, PhD
School of Construction and Civil Engineering
101 Kearney Hall
Oregon State University
Corvallis, OR  97331
(541) 737-5688
christopher.parrish@oregonstate.edu

Last Edited:
Keana Kief (OSU)
January 16th, 2024
"""

import logging
import os
import json

logger = logging.getLogger(__name__)

class Sensor: 

    def __init__(self, sensor_name):
        #Initalizes the sensor object based on the sensor name selected in CBlueApp.py.

        #:param sensor_name: The name of the sensor model selected by the user in the GUI in CBlueApp.py

        #:return: None
        #:rtype: None
       
        #Assign the sensor name given to the sensor object
        self.name = sensor_name

        #JSON file containing lidar sensor configurations for cBLUE
        self.sensor_file = "lidar_sensors.json"

        #Check if the lidar sensor config file exists
        if os.path.isfile(self.sensor_file):
            with open(self.sensor_file) as sf:
                #If the file exists load the information into self.sensor_config
                self.sensor_config = json.load(sf)
        else:
            logger.sensor("Sensor file doesn't exist")

        #The type of sensor: "single", "single_leica", or "multi" beam
        self.type = self.sensor_config[self.name]["sensor_model"]["type"]

        #If this is a Leica Chiroptera or HawkEye sensor, get narrow and wide subaqueous lookup tables
        if self.type == "single_leica":
            #The vertical narrow look up table used for modeling
            self.vert_lut_narrow = self.sensor_config[self.name]["subaqueous_LUTs"]["vertical_narrow"]
            #The horizontal narrow look up table used for modeling
            self.horz_lut_narrow = self.sensor_config[self.name]["subaqueous_LUTs"]["horizontal_narrow"]
            #The vertical wide look up table used for modeling
            self.vert_lut_wide = self.sensor_config[self.name]["subaqueous_LUTs"]["vertical_wide"]
            #The horizontal wide look up table used for modeling
            self.horz_lut_wide = self.sensor_config[self.name]["subaqueous_LUTs"]["horizontal_wide"]
        #Otherwise if this is a non-Leica single beam sensor, or a multi beam sensor
        else:
            #The vertical look up table used for modeling
            self.vert_lut = self.sensor_config[self.name]["subaqueous_LUTs"]["vertical"]
            #The horizontal look up table used for modeling
            self.horz_lut = self.sensor_config[self.name]["subaqueous_LUTs"]["horizontal"]
        
        #Scan angle and range uncertainties
        self.a_std_dev = self.sensor_config[self.name]["sensor_model"]["a_std_dev"]
        self.b_std_dev = self.sensor_config[self.name]["sensor_model"]["b_std_dev"]
        self.std_rho = self.sensor_config[self.name]["sensor_model"]["std_rho"]