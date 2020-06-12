from flatland.agents.sensors.sensor import *

class GeometricSensor(Sensor):

    def __init__(self, anchor, sensor_param):


        self.name = sensor_param.get('name', None)
        self.sensor_type = sensor_param.get('type', None)
        self.sensor_params = sensor_param
        self.sensor_value = None

        self.sensor_modality = SensorModality.GEOMETRIC

        self.anchor = anchor


    @abstractmethod
    def update_sensor(self, current_agent, entities, agents):
        pass



    @abstractmethod
    def get_shape_observation(self):
        pass
