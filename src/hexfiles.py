from enum import Enum
from dataclasses import dataclass
from typing import *
import re



class InstructionCodes(Enum):
    CODE = 0
    ADRESS = 4

@dataclass
class MemoryBlock():
    address : int
    content : List[int]

@dataclass
class HexInstruction():
    length : int
    address : int
    instruction_code : int
    content : List[int]
    check_sum : int




def decode_hex_file(file_path : str, upload_func : Callable[[int, List[int]], None]) :
    hex_instructions = __parse_hex_file(file_path)
    hex_instructions = __group_hex_instructions(hex_instructions)
    
    base_adress = 0
    for instruction in hex_instructions:        
        if __is_code_instruction(instruction):
            adress = base_adress + instruction.address
            upload_func(adress, instruction.content)
        elif __is_address_instruction(instruction):
            base_adress = (instruction.content[0] << 8 + instruction.content[1]) << 16


def __group_hex_instructions(hex_instructions : List[HexInstruction]) -> List[HexInstruction]:
    hex_instructions = [x for x in hex_instructions]
    result = []
    
    while hex_instructions:
        instruction = hex_instructions.pop(0)
        __align_instruction(instruction)
        if  __is_code_instruction(instruction):
            __mege_with_all_following_neighbors(instruction, hex_instructions)
        result.append(instruction)
        
    return result

def __mege_with_all_following_neighbors(instruction : HexInstruction,hex_instructions : List[HexInstruction]):
    while hex_instructions:
        next_instruction = hex_instructions[0]
        if not __is_code_instruction(hex_instructions[0]) or not __are_in_neighbors_addreeses(instruction, next_instruction):
            break
        __merge_instructions(instruction, hex_instructions.pop(0))
    
def __merge_instructions(instruction : HexInstruction, instruction2 : HexInstruction) -> HexInstruction:
    instruction.content.extend(instruction2.content)
    
def __align_instruction(instruction : HexInstruction):
    if instruction.address %32 != 0:
        instruction.address -= 16
        instruction.content = [0] * 16 + instruction.content

def __is_code_instruction(instruction : HexInstruction) -> bool:
    return instruction.instruction_code == InstructionCodes.CODE.value

def __is_address_instruction(instruction : HexInstruction) -> bool:
    return instruction.instruction_code == InstructionCodes.ADRESS.value

def __are_in_neighbors_addreeses(i : HexInstruction, i2: HexInstruction):
    return i.address + len(i.content) == i2.address

def __parse_hex_file(file_path : str) -> List[HexInstruction]:
    file = open(file=file_path, mode='r')
    contents = [__parse_hex_line(line) for line in file.read().split("\n") if len(line) != 0]
    return contents

def __parse_hex_line(line : str) -> HexInstruction:
    line = re.findall("..", line[1:])    
    length = __hex_to_int(line[0])
    content_boundary = 4 + length
    address = __hex_to_int("".join(line[1:3]))
    code = __hex_to_int(line[3])
    content = []
    
    if(code == InstructionCodes.CODE.value or code == InstructionCodes.ADRESS.value):
        content = [__hex_to_int(x) for x in line[4:content_boundary]]
        
    check_sum = __hex_to_int("".join(line[content_boundary:]))
    return HexInstruction(length, address, code, content, check_sum)

def __hex_to_int(hex: str) -> int:
    return int("0x"+hex, base=16)