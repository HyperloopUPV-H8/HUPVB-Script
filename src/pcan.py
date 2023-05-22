from .PCANBasic import *
from typing import *

CHANNEL = PCAN_USBBUS1
CHANNEL_PARAMETERS  = b'f_clock_mhz=60, nom_brp=3, nom_tseg1=15, nom_tseg2=4, nom_sjw=2, data_brp=3, data_tseg1=3, data_tseg2=1, data_sjw=1'
PCAN_BASIC = PCANBasic()
DLC_TO_LEN = { 0:0 , 1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:12, 10:16, 11:20, 12:24, 13:32, 14:48, 15:64 }

class Message:
    id : int
    data : List[int]
    
    def __init__(self, id : int, data : List[int]) -> None:
        self.id = id
        self.data = data
    
    def __str__(self):
        content = " ".join([ hex(x.value)[2:] for x in self.data ])
        return f'{self.id} | {content}'


def error_handler(error_code):
    if(error_code != PCAN_ERROR_OK):
        print(PCAN_BASIC.GetErrorText(error_code, 0x09))
        exit()

def send_message(msg : Message) -> int:
    tp_msg = TPCANMsgFD()
    tp_msg.ID = msg.id
    #tp_msg.LEN = len(msg.data)
    tp_msg.DLC = 15
    tp_msg.MSGTYPE = PCAN_MESSAGE_FD
    
    for i in range(len(msg.data)):
        tp_msg.DATA[i] = msg.data[i]
    
    result = PCAN_BASIC.WriteFD(CHANNEL, tp_msg)
    return result

def read_message() -> Optional[Message]:
    TPCANMsgFD
    result = PCAN_BASIC.ReadFD(CHANNEL)
    if(result[0] == PCAN_ERROR_OK):
        len = DLC_TO_LEN[result[1].DLC]
        return Message(result[1].ID, [ c_uint8(result[1].DATA[i]) for i in range(len) ])
    return None