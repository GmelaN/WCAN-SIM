class Time:
    @staticmethod
    def seconds(time):
        return time
    
    @staticmethod
    def milliseconds(time):
        return 0.0 if (time == 0) else (time / 1000.0) 

    @staticmethod
    def microseconds(time):
        return 0.0 if (time == 0) else (time / 1000000.0)
