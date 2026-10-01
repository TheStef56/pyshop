import requests
from utils.packlink.base import PacklinkBase

class PacklinkShipping(PacklinkBase):
    def __init__(self, user: str, password: str):
        self.user      = user
        self.password  = password
        self.token     = None
        self.reference = None
        self.payload  = {
            "carrier"                : "",
            "service"                : "",
            "service_id"             : 0,
            "collection_date"        : "",
            "collection_time"        : "",
            "adult_signature"        : False,
            "additional_handling"    : False,
            "insurance"              : {"amount":0, "insurance_selected": False},
            "print_in_store_selected": False,
            "proof_of_delivery"      : False,
            "priority"               : False,
            "additional_data": {
                "postal_zone_id_from": "",
                "postal_zone_id_to": "",
                "postal_zone_name_from": "",
                "postal_zone_name_to": "",
                "zip_code_id_to": "",
                "zip_code_id_from": ""
            },
            "content"                : "",
            "content_second_hand"    : False,
            "contentvalue"           : 0,
            "currency"               : "",
            "from"                   : {},
            "packages"               : [],
            "to"                     : {},
            "has_customs"            : False
        }

    def set_shipping_details(
                    self,
                    city    : str,
                    country : str, # IT
                    state   : str, # Italia
                    zip_code: str,
                    email   : str,
                    name    : str,
                    phone   : str,
                    street1 : str,
                    surname : str,
                    from_to : str = "from"
                   ): 
        self.payload[from_to] = {
                "city"    : city,
                "country" : country,
                "state"   : state,
                "zip_code": zip_code,
                "email"   : email,
                "name"    : name,
                "phone"   : phone,
                "street1" : street1,
                "surname" : surname
            }

    def append_package(self,
                       height: int,
                       length: int,
                       width : int,
                       weight: float,
                       name  : str = "custom-name",
                       id    : str = "custom-parcel-id"
                       ):
        self.payload["packages"].append(
            {
                "height": height,
                "id"    : id,
                "length": length,
                "name"  : name,
                "weight": weight,
                "width" : width
            }
        )
        
    def carrier_details(self,
                        carrier        : str, # Poste Italiane
                        service        : str, # Crono Standard
                        service_id     : int,
                        collection_date: str, # 2025/08/04
                        collection_time: str, # 09:00-18:30
                        content_value  : int,
                        content        : str = "Abbigliamento",
                        currency       : str = "EUR",
                        ):
        self.payload.update({
            "carrier"        : carrier,
            "service"        : service,
            "service_id"     : service_id,
            "collection_date": collection_date,
            "collection_time": collection_time,
            "contentvalue"   : content_value,
            "content"        : content,
            "currency"       : currency
        })
    
    def additional_data(self,
                               from_region : str, # Puglia 
                               to_region   : str  # Sicilia
                               ):
        locations_url = "https://api.packlink.com/v1/locations/postalzones/destinations?language=en_GB"
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        possible_zones = []
        from_chosen_zone = None
        to_chosen_zone = None

        locations = requests.get(locations_url, headers=headers).json()

        # find all possible shipping zones {FROM}

        for zone in locations:
            if self.payload["from"]["state"] in zone["name"]:
                possible_zones.append(zone)
        
        # try to find the right one {FROM}

        if len(possible_zones) == 0:
            from_chosen_zone = None
        elif len(possible_zones) == 1:
            from_chosen_zone = possible_zones[0]
        elif len(possible_zones) > 1:
            for zone in possible_zones:
                if from_region in zone["name"] or self.payload["from"]["city"] in zone["name"]:
                    from_chosen_zone = zone
        if from_chosen_zone == None and len(possible_zones) > 1:
            for zone in possible_zones:
                if self.payload["from"]["state"] == zone["name"]:
                    from_chosen_zone = zone

        # RESET POSSIBLE ZONES

        possible_zones = []

        # find all possible shipping zones {TO}

        for zone in locations:
            if self.payload["to"]["state"] in zone["name"]:
                possible_zones.append(zone)
        
        # try to find the right one {TO}


        if len(possible_zones) == 0:
            to_chosen_zone = None
        elif len(possible_zones) == 1:
            to_chosen_zone = possible_zones[0]
        elif len(possible_zones) > 1:
            for zone in possible_zones:
                if to_region in zone["name"] or self.payload["to"]["city"] in zone["name"]:
                    to_chosen_zone = zone
        if to_chosen_zone == None and len(possible_zones) > 1:
            for zone in possible_zones:
                if self.payload["to"]["state"] == zone["name"]:
                    to_chosen_zone = zone
        
        # FROM additional information
        
        from_id = from_chosen_zone["id"]
        from_postal_code = self.payload["from"]["zip_code"]
        postal_zones_url = f"https://api.packlink.com/v1/locations/postalcodes?language=en_GB&postalzone={from_id}&q={from_postal_code}&platform=PRO&platform_country=IT"
        from_res = requests.get(postal_zones_url, headers=headers).json()

        if len(from_res) > 0:
            self.payload["additional_data"]["postal_zone_id_from"]   = from_res[0]["postal_zone_id"]
            self.payload["additional_data"]["zip_code_id_from"]      = from_res[0]["id"]
            self.payload["additional_data"]["postal_zone_name_from"] = self.payload["from"]["state"]

        # TO additional information

        to_id = to_chosen_zone["id"]
        to_postal_code = self.payload["to"]["zip_code"]
        postal_zones_url = f"https://api.packlink.com/v1/locations/postalcodes?language=en_GB&postalzone={to_id}&q={to_postal_code}&platform=PRO&platform_country=IT"
        to_res = requests.get(postal_zones_url, headers=headers).json()
        if len(to_res) > 0:
            self.payload["additional_data"]["postal_zone_id_to"]   = to_res[0]["postal_zone_id"]
            self.payload["additional_data"]["zip_code_id_to"]      = to_res[0]["id"]
            self.payload["additional_data"]["postal_zone_name_to"] = self.payload["to"]["state"]

        
    def commit_shipment(self):
        url = "https://api.packlink.com/v1/shipments"
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json=self.payload)
        if response.status_code == 201:
            self.reference = response.json()["reference"]
            return True
        return False
    
# usage
# s = PacklinkShipping("user", "password")
# s.login()
# s.set_shipping_details(...)
# s.set_shipping_details(...)
# s.carrier_details(...)
# s.append_package(...)
# s.additional_data(...)
# s.commit_shipment()
# s.logout()