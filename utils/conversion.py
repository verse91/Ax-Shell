from currency_converter import CurrencyConverter

class Units():
    def __init__(self):
        self.WEIGHT_CHART: dict[str, tuple[float, float]] = {
            "kilogram": (1, 1),
            "kg": (1, 1),
            "tonne": (1000, 0.001),
            "ton": (1000, 0.001),
            "gram": (1e-3, 1e3),
            "g": (1e-3, 1e3),
            "milligram": (1e-6, 1e6),
            "mg": (1e-6, 1e6),
            "metric-ton": (1000, 0.001),
            "metric-tonne": (1000, 0.001),
            "long-ton": (1016.04608, 0.0009842073),
            "short-ton": (907.184, 0.0011023122),
            "pound": (0.453592, 2.2046244202),
            "lb": (0.453592, 2.2046244202),
            "stone": (6.35029, 0.1574731728),
            "st": (6.35029, 0.1574731728),
            "ounce": (0.0283495, 35.273990723),
            "oz": (0.0283495, 35.273990723),
            "carrat": (0.0002, 5000),
            "ct": (0.0002, 5000),
            "atomic-mass-unit": (1.660540199e-27, 6.022136652e26),
        }

        self.LENGTH_CHART: dict[str, float] = {
            # meter
            "m": 1,              
            "M": 1,              
            "meter": 1,          
            # kilometer
            "km": 1e3,           
            "KM": 1e3,           
            "kilometer": 1e3,    
            # centimeter
            "cm": 1e-2,          
            "CM": 1e-2,          
            "centimeter": 1e-2,  
            # millimeter
            "mm": 1e-3,          
            "MM": 1e-3,
            "millimeter": 1e-3,
            # micrometer
            "um": 1e-6,          
            "UM": 1e-6,
            "micrometer": 1e-6,
            # nanometer          
            "nm": 1e-9,          
            "NM": 1e-9,          
            "nanometer": 1e-9,
            # mile
            "mi": 1609.344,      
            "MI": 1609.344,      
            "mile": 1609.344,    
            # yard
            "yd": 0.9144,        
            "YD": 0.9144,        
            "yard": 0.9144,
            # foot
            "ft": 0.3048,        
            "FT": 0.3048,        
            "foot": 0.3048,      
            "feet": 0.3048,      
            # inch
            "in": 0.0254,
            "IN": 0.0254,
            "inch": 0.0254,
            "inches": 0.0254,
            # nautical mile
            "nmi": 1852,         
            "NMI": 1852,         
            "nautical-mile": 1852,
        }

        self.STORAGE_TYPE_CHART: dict[str, float] = {
            "bit": 1,
            "byte": 8,
            "B": 8,
            "kilobyte": 8192,
            "KB": 8192,
            "megabyte": 8388608,
            "MB": 8388608,
            "gigabyte": 8589934592,
            "GB": 8589934592,
            "terabyte": 8796093022208,
            "TB": 8796093022208,
            "petabyte": 9007199254740992,
            "PB": 9007199254740992,
            "exabyte": 9223372036854775808,
            "EB": 9223372036854775808,
        }

        self.currency_converter = CurrencyConverter()

        self.TEMPERATURE_CHART = {
            "celsius": (lambda v: v + 273.15, lambda v: v - 273.15),
            "c": (lambda v: v + 273.15, lambda v: v - 273.15),
            "fahrenheit": (lambda v: (v - 32) * 5/9 + 273.15, lambda v: (v - 273.15) * 9/5 + 32),
            "f": (lambda v: (v - 32) * 5/9 + 273.15, lambda v: (v - 273.15) * 9/5 + 32),
            "kelvin": (lambda v: v, lambda v: v),
            "k": (lambda v: v, lambda v: v),
            "rankine": (lambda v: v * 5/9, lambda v: v * 9/5),
            "reaumur": (lambda v: v * 5/4 + 273.15, lambda v: (v - 273.15) * 4/5),
        }

        self.TIME_CHART: dict[str, float] = {
            "second": 1,
            "s": 1,
            "minute": 60,
            "min": 60,
            "hour": 3600,
            "h": 3600,
            "day": 86400,
            "d": 86400,
            "week": 604800,
            "w": 604800,
            "fortnight": 1209600,
            "month": 2628000,  # Approximation (30.44 days)
            "m": 2628000,  # Approximation (30.44 days)
            "year": 31536000,  # Approximation (365 days)
            "yr": 31536000,  # Approximation (365 days)
            "decade": 315360000,  # Approximation (10 years)
            "dec": 315360000,  # Approximation (10 years)
        }

        self.LIQUID_VOLUME_CHART = {
            "liter": 1,
            "l": 1,
            "milliliter": 1e-3,
            "ml": 1e-3,
            "gallon": 3.78541,
            "quart": 0.946353,
            "pint": 0.473176,
            "fluid-ounce": 0.0295735,
            "fl-oz": 0.0295735,
            "oz": 0.0295735,
            "ounce": 0.0295735,
            "cup": 0.236588,
            "tablespoon": 0.0147868,
            "tbsp": 0.0147868,
            "teaspoon": 0.00492892,
            "tsp": 0.00492892,
        }

class Conversion():
    def __init__(self):
        self.units = Units()

    def convert_weight(self, value, from_type, to_type):
        if from_type == to_type:
            return value

        if to_type not in self.units.WEIGHT_CHART or from_type not in self.units.WEIGHT_CHART:
            msg = (
                f"Invalid 'from_type' or 'to_type' value: {from_type!r}, {to_type!r}\n"
                f"Supported values are: {', '.join(self.units.WEIGHT_CHART.keys())}"
            )
            raise ValueError(msg)
        return value * self.units.WEIGHT_CHART[to_type][0] * self.units.WEIGHT_CHART[from_type][1]
    
    def convert_currency(self, value, from_type, to_type):
        if from_type == to_type:
            return value
        return self.units.currency_converter.convert(value, from_type, to_type)
    
    
    def convert_temperature(self, value, from_type, to_type):
        if from_type == to_type:
            return value

        if from_type not in self.units.TEMPERATURE_CHART or to_type not in self.units.TEMPERATURE_CHART:
            raise ValueError(
                f"Invalid 'from_type' or 'to_type' value: {from_type!r}, {to_type!r}\n"
                f"Supported values are: {', '.join(self.units.TEMPERATURE_CHART.keys())}"
            )

        # Convert to Kelvin, then to the target scale
        to_kelvin = self.units.TEMPERATURE_CHART[from_type][0]
        from_kelvin = self.units.TEMPERATURE_CHART[to_type][1]
        return from_kelvin(to_kelvin(value))
    

    def convert_length(self, value, from_type, to_type):
        if from_type == to_type:
            return value
        
        if from_type not in self.units.LENGTH_CHART or to_type not in self.units.LENGTH_CHART:
            msg = (
                f"Invalid 'from_type' or 'to_type' value: {from_type!r}, {to_type!r}\n"
                f"Supported values are: {', '.join(self.units.LENGTH_CHART)}"
            )
            raise ValueError(msg)
        
        # Convert to the target unit
        return value * (self.units.LENGTH_CHART[from_type] / self.units.LENGTH_CHART[to_type])
        
    def convert_time(self, value, from_type, to_type):
        if from_type == to_type:
            return value
        
        # Conversion factors relative to seconds (base unit)
        if from_type not in self.units.TIME_CHART or to_type not in self.units.TIME_CHART:
            msg = (
                f"Invalid 'from_type' or 'to_type' value: {from_type!r}, {to_type!r}\n"
                f"Supported values are: {', '.join(self.units.TIME_CHART)}"
            )
            raise ValueError(msg)

        # Convert to the target unit
        return value * (self.units.TIME_CHART[from_type] / self.units.TIME_CHART[to_type])
    
    def convert_liquid_volume(self, value, from_type, to_type):
        if from_type == to_type:
            return value
        
        if from_type not in self.units.LIQUID_VOLUME_CHART or to_type not in self.units.LIQUID_VOLUME_CHART:
            msg = (
                f"Invalid 'from_type' or 'to_type' value: {from_type!r}, {to_type!r}\n"
                f"Supported values are: {', '.join(self.units.LIQUID_VOLUME_CHART)}"
            )
            raise ValueError(msg)

        # Convert to the target unit
        return value * (self.units.LIQUID_VOLUME_CHART[from_type] / self.units.LIQUID_VOLUME_CHART[to_type])
    
    def convert_storage_type(self, value, from_type, to_type):
        if from_type == to_type:
            return value
        
        if from_type not in self.units.STORAGE_TYPE_CHART or to_type not in self.units.STORAGE_TYPE_CHART:
            msg = (
                f"Invalid 'from_type' or 'to_type' value: {from_type!r}, {to_type!r}\n"
                f"Supported values are: {', '.join(self.units.STORAGE_TYPE_CHART)}"
            )
            raise ValueError(msg)

        # Convert to the target unit
        return value * (self.units.STORAGE_TYPE_CHART[from_type] / self.units.STORAGE_TYPE_CHART[to_type])
    
    def convert(self, value:float, from_type:str, to_type:str):
        # Determine the type of conversion based on the input types
        if from_type in self.units.WEIGHT_CHART and to_type in self.units.WEIGHT_CHART:
            return self.convert_weight(value, from_type.lower(), to_type.lower())
        elif from_type in self.units.LENGTH_CHART and to_type in self.units.LENGTH_CHART:
            return self.convert_length(value, from_type.lower(), to_type.lower())
        elif from_type in self.units.TEMPERATURE_CHART and to_type in self.units.TEMPERATURE_CHART:
            return self.convert_temperature(value, from_type.lower(), to_type.lower())
        elif from_type in self.units.TIME_CHART and to_type in self.units.TIME_CHART:
            return self.convert_time(value, from_type.lower(), to_type.lower())
        elif from_type in self.units.LIQUID_VOLUME_CHART and to_type in self.units.LIQUID_VOLUME_CHART:
            return self.convert_liquid_volume(value, from_type.lower(), to_type.lower())
        elif from_type in self.units.STORAGE_TYPE_CHART and to_type in self.units.STORAGE_TYPE_CHART:
            return self.convert_storage_type(value, from_type, to_type)
        elif from_type in self.units.currency_converter.currencies and to_type in self.units.currency_converter.currencies:
            return self.convert_currency(value, from_type, to_type)
        else:
            raise ValueError(f"Unsupported conversion: {from_type} to {to_type}")
        
    def clean_type(self, type:str):
        """
        Strips the 's' from the end of the type if it exists.
        """
        if type in self.units.currency_converter.currencies:
            return type.upper()
        if type.endswith("s") and type is not "celsius":
            if type[:-1] in self.units.STORAGE_TYPE_CHART:
                return type[:-1]
            return type[:-1].lower()
        return type