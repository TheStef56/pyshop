import requests
from base64 import b64encode

class PacklinkBase():
    def login(self):
        token = b64encode(f"{self.user}:{self.password}".encode("utf-8")).decode()
        url = "https://api.packlink.com/v1/login?platform=pro&platform_country=it"
        response = requests.get(url=url,
                                headers={
                                        "Authorization": f"Basic {token}"
                                    }
                                )
        if response.ok:
            data = response.json()
            self.token = data["token"]
            return True
        else:
            print("Login Error: ", response.status_code, response.text)
            return False

    def logout(self):
        url = "https://pro.packlink.it/auth-gateway/logout?return_url=https%3A%2F%2Fauth.packlink.com%2Fit-IT%2Fpro%2Flogout%3Ftenant_id%3DPACKLINKPROIT"
        response = requests.get(url=url,
                                headers={
                                    "Cookie": f"token={self.token}"
                                },
                            )
        return response