from .pcan import send_message, read_message, Message, error_handler, PCAN_BASIC, CHANNEL, CHANNEL_PARAMETERS

from time import sleep, time
from enum import Enum
from tqdm import tqdm
from typing import List
from math import ceil


VERBOSE = False
TIMEOUT_MS = 50000
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
    
def upload_code(file_path) :
    print(file_path)
    print(f"- 👨‍💻 Upload code from file: {file_path}")
    print(f"|    Bootloader version : {get_version().value}")
    print("|    Erasing memory")
    erase_memory()
    sleep(0.01)
    print("|    Uploading code...")
    __upload_code(file_path)
    print("- Done 🥳")
    
def get_version() -> int : 
    __initialize_can()
    send_message(Message(int(Commands.GET_VERSION.value), []))

    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)
    msg = __wait_for_bootloader_message()
    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)

    __unitialize_can()
    return msg.data[0]

def read_memory(sector: int) -> List[int]:
    if((sector < 0) or (sector > 7)):
        raise BootloaderException("Sector must be between 0 and 7")

    __initialize_can()
    send_message(Message(int(Commands.READ_MEMORY.value), [sector]))

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

    send_message(Message(int(Commands.WRITE_MEMORY.value), [sector]))

    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)

    send_message(Message(int(Commands.WRITE_MEMORY.value), [int(Commands.ACK.value)]))

    packets_left = 2048
    counter = 1
    while packets_left > 0:
        send_message(Message(int(Commands.WRITE_MEMORY.value),data[:64]))
        data = data[64:]

        if counter >= 8:
            msg = __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)
            send_message(Message(int(Commands.WRITE_MEMORY.value), [int(Commands.ACK.value)]))

            counter = 1
        else:
            counter += 1

        packets_left -= 1
       

    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)
    __unitialize_can()

def erase_memory():
    __initialize_can()
    send_message(Message(Commands.ERASE_MEMORY.value, [0x00, 0x05]))    
    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)
    __wait_for_bootloader_message(matches_first_byte=Commands.ACK.value)

    __unitialize_can()


# Private functions
def __upload_code(file_path: str):
    page_size_in_bytes = 32768*4
    max_pages = 6

    file = open(file=file_path, mode='rb')
    # end = False

    data = file.read()
    variable = len(data)
    number_of_sectors = ceil(variable/page_size_in_bytes)
    if (variable > (max_pages*page_size_in_bytes)):
        print(f"|    The file is too big")
        return 
    

    pbar = tqdm(range(number_of_sectors), colour='green', leave=True, position=0)#Progress bar chula chula
    for i in pbar:
        pbar.set_description("Sector " + str(i) + " of " + str(number_of_sectors-1))
            
        #Si hemos llegado al final del archivo, rellenamos con 0xff
        aux = len(data)
        if aux < 32768*4:
            end = True
            data += b'\xff' * (32768*4 - len(data))

        write_memory(i, data[0:32768*4])
        data = data[32768*4:]

        # if end:
        #     break
       
    
    
    remaining_data = file.read()
    file.close()

    #Redundancia por si acaso
    if len(remaining_data) > 0:
        print(f"|    The file is too big, erasing memory")
        erase_memory()
        raise BootloaderException("The file is too big")
    

def __initialize_can():
    error_handler(PCAN_BASIC.InitializeFD(CHANNEL, CHANNEL_PARAMETERS))
    
def __unitialize_can():
    error_handler(PCAN_BASIC.Uninitialize(CHANNEL))

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
    print("\nTimed out waiting for bootloader message\n")
    raise BootloaderException()

def __get_current_time_ms() -> int:
    return int(time() * 1000)

