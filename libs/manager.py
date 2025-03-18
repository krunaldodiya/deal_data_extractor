import os
import MT5Manager


def get_mt5_manager() -> MT5Manager.ManagerAPI:
    client = MT5Manager.ManagerAPI()

    mt5_server = os.getenv("MT5_SERVER")
    mt5_login = int(os.getenv("MT5_LOGIN"))
    mt5_password = os.getenv("MT5_PASSWORD")

    try:
        assert isinstance(mt5_server, str), "mt5_server must be a string"
        assert isinstance(mt5_login, int), "mt5_server must be an integer"
        assert isinstance(mt5_password, str), "mt5_server must be a string"

        response = client.Connect(
            mt5_server,
            mt5_login,
            mt5_password,
            MT5Manager.ManagerAPI.EnPumpModes.PUMP_MODE_FULL,
            30000,
        )

        if not response:
            raise Exception(MT5Manager.LastError())

        return client
    except Exception as e:
        if client:
            client.Disconnect()
        raise e
