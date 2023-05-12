from .pcan import send_message, read_message, Message, error_handler, PCAN_BASIC, CHANNEL, CHANNEL_PARAMETERS
from .hexfiles import decode_hex_file

from time import sleep, time
from enum import Enum
from math import log2
from typing import List

VERBOSE = False
TIMEOUT_MS = 20000
UPDATE_PERIOD_S = 0.001

class Commands(Enum):

    ACK                 = 0X79
    NACK                = 0x1f
    GET_VERSION         = 0X50
    ERASE_MEMORY        = 0x20
    READ_MEMORY         = 0x40
    WRITE_MEMORY        = 0x30
    GO                  = 0x10 #Does nothing, it just returns NACK. Reserved for future use.

class BootloaderException(Exception):
    pass

class ResponseStatus(Enum):
    OK=0
    ERROR=1
    BAD_PARAMETERS=2
    

def upload_code(file) :
    print(f"- 👨‍💻 Upload code from file: {file}")
    print(f"|    Bootloader version : {get_version()}")
    print("|    Erasing memory")
    erase_memory()
    sleep(0.01)
    print("|    Uploading code...")
    decode_hex_file(file, write_memory)
    print("|    Starting code ->")
    exit_bootmode(0x8000000)
    print("- Done 🥳")
    
#Done
def get_version() -> int : 
    __initialize_can()
    send_message(Message(int(Commands.GET_VERSION.value), []))

    msg = __wait_for_bootloader_command_response()
    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)
    
    __unitialize_can()
    return msg[0]

#Done
def read_memory(sector: int) -> List[int]:
    if((sector < 0) or (sector > 7)):
        raise BootloaderException("Sector must be between 0 and 7")

    __initialize_can()
    send_message(Message(int(Commands.READ_MEMORY.value), []))

    result = []
    
    __wait_for_bootloader_command_response()
    send_message(Message(int(Commands.ACK.value), []))

    packets_left = 2048
    counter = 0
    while packets_left > 0:
        msg = __wait_for_bootloader_message()
        result += msg.data

        if counter >= 8:
            __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)
            send_message(Message(int(Commands.ACK.value), []))
            counter = 0

        counter += 1
        packets_left -= 1

    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)

    __unitialize_can()
    return result

def write_memory(sector : int, data : List[int]) :
    __initialize_can()

    send_message(Message(int(Commands.WRITE_MEMORY.value), []))

    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)
    send_message(Message(int(Commands.ACK.value), []))

    packets_left = 2048
    counter = 1
    index = 0
    while packets_left > 0:
        send_message(Message(int(Commands.ACK.value), [data[index:64]]))
        data = data[64:]

        if counter >= 8:
            __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)
            send_message(Message(int(Commands.ACK.value), []))
            counter = 1
        else:
            counter += 1

        packets_left -= 1
        index += 64

    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)
    __unitialize_can()

def erase_memory():
    __initialize_can()
    send_message(Message(Commands.ERASE_MEMORY.value, [0x00, 0x06]))    
    __wait_for_bootloader_command_response()
    __wait_for_bootloader_command_response()
    __unitialize_can()


# Private functions
def __initialize_can():
    error_handler(PCAN_BASIC.InitializeFD(CHANNEL, CHANNEL_PARAMETERS))
    
def __unitialize_can():
    error_handler(PCAN_BASIC.Uninitialize(CHANNEL))

def __write_memory_order(memory_adress: int, data : List[int]) :
    msg_content = __int_to_byte_array(memory_adress) + [255 if len(data) == 256 else len(data)]
    send_message(Message(Commands.WRITE_MEMORY.value, msg_content))    
    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)

    while len(data) > 0:
        send_message(Message(Commands.WRITE_MEMORY.value, data[0:64]))
        data = data[64:]
        
    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)

def __wait_for_bootloader_command_response(response_code = 0) -> List[int]:
    response = [ ]
    msg = __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)
    msg = __wait_for_bootloader_message()
    
    while msg.data[0].value != 0x79 :
        for x in msg.data:
            response.append(x.value)
        msg = __wait_for_bootloader_message()
        
    return response
            
def __wait_for_bootloader_message(matches_first_byte=None) -> Message:
    t1_ms = __get_current_time_ms()
    
    while __get_current_time_ms() - t1_ms < TIMEOUT_MS:
        sleep(UPDATE_PERIOD_S)
        message = read_message()
        
        if message and VERBOSE:
            print(message)
            
        if (message and not matches_first_byte) or (message and (message.data[0].value == matches_first_byte)):
            return message
    
    raise BootloaderException()

def __int_to_byte_array(x : int) -> List[int]:
    result = []
    
    for i in range(int(log2(x) / 8) + 1):
        result.insert(0, (x >> (i*8)) & 0xff)
    
    return result
def __get_current_time_ms() -> int:
    return int(time() * 1000)

