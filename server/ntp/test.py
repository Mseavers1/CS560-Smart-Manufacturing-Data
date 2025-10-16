from ntp_facade_smr import TimeBrokerFacade
from time import ctime

LOCALHOST = "localhost"

try:
    tbroker = TimeBrokerFacade(ntp_server_ip = LOCALHOST)
    
    synced_time = tbroker.get_synchronized_time()

    print(f"Success")
    print(f"Server Time: {ctime(synced_time)}")

except(ValueError, IOError) as e:
    print("error")
    print (e)