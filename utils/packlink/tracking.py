import requests
from utils.packlink.base import PacklinkBase

class PacklinkTracking(PacklinkBase):
    def __init__(self, user, password):
        self.user         = user
        self.password     = password
        self.token        = None
        self.shipping_res = None
        self.tracking_res = None

    def get_shipment(self, reference):
        shipping = requests.get(f"https://api.packlink.com/pro/shipments/{reference}",
                            headers={
                                "Authorization": self.token,
                                "Content-Type": "application/json"
                             })
        self.shipping_res = shipping
        return self.shipping_res
    
    def get_tracking(self, reference):
        tracking = requests.get(f"https://api.packlink.com/pro/shipments/{reference}/track",
                            headers={
                                "Authorization": self.token,
                                "Content-Type": "application/json"
                             })
        self.tracking_res = tracking
        return self.tracking_res