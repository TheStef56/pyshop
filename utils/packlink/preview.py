import requests
from utils.packlink.base import PacklinkBase

class PacklinkPreview(PacklinkBase):
    def __init__(self,
                user    : str,
                password: str, 
                countryA: str,
                countryB: str,
                zipcodeA: int,
                zipcodeB: int,
                ):
        self.URL    = "https://api.packlink.com/pro/services"
        self.payload = {
            "platform"           : "PRO",
            "platform_country"   : countryA,
            "sort_by"            : "bestPrice",
            "from"               : {"country": countryA, "zip": str(zipcodeA)},
            "packages"           : [],
            "source"             : "PRO",
            "to"                 : {"country": countryB, "zip": str(zipcodeB)}
        }

        self.user            = user
        self.password        = password
        self.token           = None
        self.response        = None
        self.shipping_time   = None
        self.price           = None
        self.carrier         = None
        self.id              = None
        self.service         = None
        self.collection_date = None
        self.collection_time = None

    def add_package(self,
                    width : int,
                    length: int,
                    height: int,
                    weigth: float
                    ):
            self.payload["packages"].append(
                {
                    "height": str(height),
                    "length": str(length),
                    "weight": str(weigth),
                    "width" : str(width)
                }
            )

    def makereq(self): 
        req = requests.post(self.URL,
                            headers={
                                "Authorization": self.token,
                                "Content-Type" : "application/json"
                            },
                            json=self.payload)
        self.response = req.json()
        return req

    def select_best(self, dropoff=False, deliverytp=False):
        if self.response is None:
            return None
        for entry in self.response:
            if entry["dropoff"] == dropoff and entry["delivery_to_parcelshop"] == deliverytp:
                self.shipping_time   = entry["transit_time"]
                self.price           = entry["base_price"]
                self.carrier         = entry["carrier_name"]
                self.id              = entry["id"]
                self.service         = entry["name"]
                self.collection_date = list(entry["available_dates"].keys())[0]
                self.collection_time = list(entry["available_dates"].values())[0][1:-1].replace(" ", "").replace(",","-")
                return entry
        return None

# usage:
# p = PacklinkPreview("user", "password", "IT", "IT", 72026, 20019)
# p.login()
# p.add_package(10, 10, 2, 0.15)
# p.makereq()
# print(p.response)
# p.select_best()
# p.logout()

# print(p.carrier)
# print(p.price)
# print(p.shipping_time)
