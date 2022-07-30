from kilroy_ws_server_py_sdk import AppError

PARAMETER_GET_ERROR = AppError(1, "Unable to get parameter value.")
PARAMETER_SET_ERROR = AppError(2, "Unable to set parameter value.")
STATE_NOT_READY_ERROR = AppError(3, "State is not ready to be read.")
INVALID_CONFIG_ERROR = AppError(4, "Config is not valid.")
