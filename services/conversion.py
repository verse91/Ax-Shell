from currency_converter import CurrencyConverter
class Conversion():
    def __init__(self):
        self.KILOGRAM_CHART: dict[str, float] = {
            "kilogram": 1,
            "tonne": 1000,
            "gram": pow(10, 3),
            "milligram": pow(10, 6),
            "metric-ton": pow(10, -3),
            "long-ton": 0.0009842073,
            "short-ton": 0.0011023122,
            "pound": 2.2046244202,
            "stone": 0.1574731728,
            "ounce": 35.273990723,
            "carrat": 5000,
            "atomic-mass-unit": 6.022136652e26,
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

        self.WEIGHT_TYPE_CHART: dict[str, float] = {
            "kilogram": 1,
            "tonne": 1000,
            "gram": pow(10, -3),
            "milligram": pow(10, -6),
            "metric-ton": pow(10, 3),
            "long-ton": 1016.04608,
            "short-ton": 907.184,
            "pound": 0.453592,
            "stone": 6.35029,
            "ounce": 0.0283495,
            "carrat": 0.0002,
            "atomic-mass-unit": 1.660540199e-27,
        }

        self.currency_converter = CurrencyConverter()


    def convert_weight(self, value, from_type, to_type):
        if to_type not in self.KILOGRAM_CHART or from_type not in self.WEIGHT_TYPE_CHART:
            msg = (
                f"Invalid 'from_type' or 'to_type' value: {from_type!r}, {to_type!r}\n"
                f"Supported values are: {', '.join(self.WEIGHT_TYPE_CHART)}"
            )
            raise ValueError(msg)
        return value * self.KILOGRAM_CHART[to_type] * self.WEIGHT_TYPE_CHART[from_type]
    
    def convert_currency(self, value, from_type, to_type):
        if from_type == to_type:
            return value
        return self.currency_converter.convert(value, from_type, to_type)
    
    def convert_temperature(self, value, from_type, to_type):
        if from_type == to_type:
            return value

        # Conversion to Kelvin (base scale)
        to_type_chart = {
            "celsius": lambda v: v + 273.15,
            "fahrenheit": lambda v: (v - 32) * 5/9 + 273.15,
            "kelvin": lambda v: v,
            "rankine": lambda v: v * 5/9,
            "reaumur": lambda v: v * 5/4 + 273.15,
        }

        # Conversion from Kelvin to target scale
        from_type_chart = {
            "celsius": lambda v: v - 273.15,
            "fahrenheit": lambda v: (v - 273.15) * 9/5 + 32,
            "kelvin": lambda v: v,
            "rankine": lambda v: v * 9/5,
            "reaumur": lambda v: (v - 273.15) * 4/5,
        }

        if from_type not in to_type_chart or to_type not in from_type_chart:
            raise ValueError(
                f"Invalid 'from_type' or 'to_type' value: {from_type!r}, {to_type!r}\n"
                f"Supported values are: {', '.join(to_type_chart.keys())}"
            )

        # Convert to Kelvin, then to the target scale
        temp_value = to_type_chart[from_type](value)
        return from_type_chart[to_type](temp_value)
    

    def convert_length(self, value, from_type, to_type):
        if from_type not in self.LENGTH_CHART or to_type not in self.LENGTH_CHART:
            msg = (
                f"Invalid 'from_type' or 'to_type' value: {from_type!r}, {to_type!r}\n"
                f"Supported values are: {', '.join(self.LENGTH_CHART)}"
            )
            raise ValueError(msg)
        
        # Convert to the target unit
        return value * (self.LENGTH_CHART[from_type] / self.LENGTH_CHART[to_type])
        
    def convert_time(self, value, from_type, to_type):
        # Conversion factors relative to seconds (base unit)
        TIME_CHART = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
            "month": 2628000,  # Approximation (30.44 days)
            "year": 31536000,  # Approximation (365 days)
        }

        if from_type not in TIME_CHART or to_type not in TIME_CHART:
            msg = (
                f"Invalid 'from_type' or 'to_type' value: {from_type!r}, {to_type!r}\n"
                f"Supported values are: {', '.join(TIME_CHART)}"
            )
            raise ValueError(msg)

        # Convert to the target unit
        return value * (TIME_CHART[from_type] / TIME_CHART[to_type])
    
    def convert_liquid_volume(self, value, from_type, to_type):
        
        LIQUID_VOLUME_CHART = {
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

        if from_type not in LIQUID_VOLUME_CHART or to_type not in LIQUID_VOLUME_CHART:
            msg = (
                f"Invalid 'from_type' or 'to_type' value: {from_type!r}, {to_type!r}\n"
                f"Supported values are: {', '.join(LIQUID_VOLUME_CHART)}"
            )
            raise ValueError(msg)

        # Convert to the target unit
        return value * (LIQUID_VOLUME_CHART[from_type] / LIQUID_VOLUME_CHART[to_type])
    
    def convert(self, value:float, from_type:str, to_type:str):
        # Determine the type of conversion based on the input types
        if from_type in self.WEIGHT_TYPE_CHART and to_type in self.WEIGHT_TYPE_CHART:
            return self.convert_weight(value, from_type.lower(), to_type.lower())
        elif from_type in self.LENGTH_CHART and to_type in self.LENGTH_CHART:
            return self.convert_length(value, from_type.lower(), to_type.lower())
        elif from_type in ["celsius", "fahrenheit", "kelvin", "rankine", "reaumur"] and to_type in ["celsius", "fahrenheit", "kelvin", "rankine", "reaumur"]:
            return self.convert_temperature(value, from_type.lower(), to_type.lower())
        elif from_type in ["second", "minute", "hour", "day", "week", "month", "year"] and to_type in ["second", "minute", "hour", "day", "week", "month", "year"]:
            return self.convert_time(value, from_type.lower(), to_type.lower())
        elif from_type in self.currency_converter.currencies and to_type in self.currency_converter.currencies:
            return self.convert_currency(value, from_type, to_type)
        else:
            raise ValueError(f"Unsupported conversion: {from_type} to {to_type}")
        
    def capitalize(self, text: str) -> str:
        if text.upper() not in self.currency_converter.currencies:
            return text.lower()
        else:
            return text.upper()
        
            

