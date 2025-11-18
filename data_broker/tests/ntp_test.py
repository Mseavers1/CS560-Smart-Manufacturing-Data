from ntp_facade_smr import TimeBrokerFacade
from time import ctime

LOCAL_NTP_SERVER = "192.168.1.76"
LOCAL_NTP_PORT = 123 # Our custom port for the local test server

def run_facade_test():
    """
    Tests the locally installed ntp_client_facade package
    against our temporary Python NTP server.
    """
    print("--- Starting Local Facade Test ---")
    
    try:
        # 1. Initialize the facade, passing both the IP and our custom test port.
        time_broker = TimeBrokerFacade(
            ntp_server_ip=LOCAL_NTP_SERVER,
            port=LOCAL_NTP_PORT
        )
        
        # 2. Call the facade's public method.
        synced_timestamp = time_broker.get_synchronized_time()
        
        print("\n--- Synchronization Test Passed ---")
        print(f"Server: {LOCAL_NTP_SERVER}:{LOCAL_NTP_PORT}")
        print(f"Synced Time (Human): {ctime(synced_timestamp)}")
        print("-----------------------------------")

    except (ValueError, IOError) as e:
        print(f"\n--- Test Failed ---")
        print(f"{e}")
        print("-----------------------")

if __name__ == "__main__":
    run_facade_test()