import abc

class tion:
  @abc.abstractmethod
  def _send_request(self, request: bytearray) -> bytearray:
    """ Send request to device

    Args:
      request : array of bytes to send to device
    Returns:
      array of bytes with device response
    """
    pass

  @abc.abstractmethod
  def _decode_response(self, response: bytearray) -> dict:
    """ Decode response from device

    Args:
      response: array of bytes with data from device, taken from _send_request
    Returns:
      dictionary with device response
    """
    pass
  
  @abc.abstractmethod
  def _encode_request(self, request: dict) -> bytearray:
    """ Encode dictionary of request to byte array
    
    Args:
      request: dictionry with request
    Returns:
      Byte array for sending to device
    """
    pass

  @abc.abstractmethod
  def get() -> dict:
    """ Get device information
    Returns:
      dictionay with device paramters
    """
    pass
