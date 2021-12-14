from registers import get_register

RTYPE_OPCODE = "0110011"
ITYPE_OPCODE_GROUP1 = "0010011"
ITYPE_OPCODE_GROUP2 = "0000011"
STYPE_OPCODE = "0100011"
BTYPE_OPCODE = "1100011"
JAL_OPCODE = "1101111"
JALR_OPCODE = "1100111"
LUI_OPCODE = "0110111"
AUIPC_OPCODE = "0010111"
SYSTEM_OPCODE = "1110011"
RV32M_OPCODE = "0110011"


class Const:
    def __init__(self, value, radix, length):
        self.default_radix = radix
        if isinstance(value, str):
            self.value: int = int(value, radix)
        elif isinstance(value, int):
            self.value: int = value
        else:
            raise TypeError("wrong input type")
        self.length = length

    def bin(self):
        return bin(self.value)[2:].rjust(self.length, "0")

    def hex(self):
        return hex(self.value)[2:]

    def __repr__(self):
        if self.default_radix == 16:
            return f"Const({hex(self.value)[2:]})"
        elif self.default_radix == 2:
            return f'Const({bin(self.value)[2:].rjust(self.length, "0")})'
        return f"Const({str(self.value)})"

    def __eq__(self, other):
        if isinstance(other, str):
            return self.bin() == other
        elif isinstance(other, int):
            return self.value == other
        return self.value == other.value

    def __hash__(self):
        return self.value.__hash__()


class Register(Const):
    def __init__(self, value, radix=2, length=None):
        if not length:
            super().__init__(value, radix, len(value))
        else:
            super().__init__(value, radix, length)

    def __repr__(self):
        return get_register(self.value)

    def __str__(self):
        return self.__repr__()


class Immediate(Const):
    def __init__(self, value, radix=2, repr_radix=10, length=None):
        if isinstance(value, str):
            super().__init__(value, radix, len(value))
        else:
            super().__init__(value, radix, length)
        self.repr_radix = repr_radix

    def __repr__(self):
        if self.repr_radix == 10:
            return str(self.value)
        elif self.repr_radix == 16:
            return hex(self.value)
        else:
            return bin(self.value)[2:]

    def __str__(self):
        return self.__repr__()


class Funct3(Const):
    def __init__(self, value, radix=None):
        length = 3
        if not radix:
            if isinstance(value, str):
                radix = 2
            else:
                if len(str(value)) == length:
                    radix = 2
                else:
                    radix = 16
                    value = int(str(value), radix)
        super().__init__(value, radix, length)

    def __repr__(self):
        return f"Funct3({hex(self.value)})"


class Funct7(Const):
    def __init__(self, value, radix=None):
        length = 7
        if not radix:
            if len(str(value)) == length:
                radix = 2
            else:
                radix = 16
                value = int(str(value), radix)
        super().__init__(value, radix, length)

    def __repr__(self):
        return f"Funct7({hex(self.value)})"


class Opcode(Const):
    def __init__(self, value, radix=2):
        super().__init__(value, radix, 7)

    def __repr__(self):
        return f"Opcode({super().__repr__()})"


class Command:
    def __init__(self, name, t):
        self.name = name
        self.t = t

    def __repr__(self):
        return f"cmd({self.name} {self.t}Type)"

    def parse(self, cmd):
        raise NotImplementedError()

    @staticmethod
    def get_key_values(cmd):
        raise NotImplementedError()


class Instruction:
    def __init__(self, line):
        self.__line = line

    def __getitem__(self, item):
        return (self.__line[item])[::-1]

    def __repr__(self):
        return self.__line

    def __int__(self):
        return int(self.__line)

    def get(self, f, t):
        return self.__line[f:t]


class UnknownCommand(Command):
    def __init__(self, info):
        super().__init__(f"unknown command: {info}", None)

    def parse(self, cmd):
        return self.name

    @staticmethod
    def get_key_values(cmd):
        pass


class RType(Command):
    def __init__(self, name, funct3: Funct3, funct7: Funct7, opcode: Opcode):
        super().__init__(name, "R")
        self.funct3 = funct3
        self.funct7 = funct7
        self.opcode = opcode

    def parse(self, cmd):
        rd = cmd[7:12]
        rs1 = cmd[15:20]
        rs2 = cmd[20:25]
        return self.name + " " + ", ".join(map(str, [Register(rd), Register(rs1), Register(rs2)]))

    @staticmethod
    def get_key_values(cmd):
        return Opcode(cmd[0:7]), Funct3(cmd[12:15], 2), Funct7(cmd[25:32])


class IType(Command):
    def parse(self, cmd):
        rd = cmd[7:12]
        rs1 = cmd[15:20]
        if self.funct3 in [Funct3(1), Funct3(5)] and self.opcode == ITYPE_OPCODE_GROUP1:
            imm = cmd[20:25]
        else:
            if int(cmd[31]):
                imm = cmd[20:31]
                imm = int(imm, 2)
                imm -= 2 ** 11
            else:
                imm = cmd[20:32]
        if self.opcode == Opcode(ITYPE_OPCODE_GROUP1):
            return self.name + " " + ", ".join(map(str, [Register(rd), Register(rs1), Immediate(imm, length=12)]))
        else:
            return self.name + " " + str(Register(rd)) + ", " + f"{Immediate(imm, length=12)}({Register(rs1)})"

    @staticmethod
    def get_key_values(cmd):
        funct3 = Funct3(cmd[12:15])
        opcode = Opcode(cmd[0:7])
        if funct3 in [Funct3(1), Funct3(5)] and opcode == ITYPE_OPCODE_GROUP1:
            funct7 = Funct7(cmd[25:32])
        else:
            funct7 = None
        return opcode, funct3, funct7

    def __init__(self, name, funct3: Funct3, funct7, opcode: Opcode):
        super().__init__(name, "I")
        self.funct3 = funct3
        self.funct7 = funct7
        self.opcode = opcode


class SType(Command):
    def __init__(self, name, funct3: Funct3, opcode: Opcode):
        super().__init__(name, "S")
        self.funct3 = funct3
        self.opcode = opcode

    def parse(self, cmd):
        if int(cmd[31]):
            imm = cmd[7:12] + cmd[25:31]
            imm = int(imm, 2)
            imm -= 2 ** 11
        else:
            imm = cmd[7:12] + cmd[25:32]
        rs1 = cmd[15:20]
        rs2 = cmd[20:25]
        return self.name + " " + str(Register(rs2)) + ", " + f"{Immediate(imm, repr_radix=16)}({Register(rs1)})"

    @staticmethod
    def get_key_values(cmd):
        return Opcode(cmd[0:7]), Funct3(cmd[12:15])


class BType(Command):
    def __init__(self, name, funct3: Funct3, opcode: Opcode):
        super().__init__(name, "B")
        self.funct3 = funct3
        self.opcode = opcode

    def parse(self, cmd):
        # todo fix parse
        if int(cmd[31]):
            imm = cmd[8:12] + cmd[25:31] + cmd[7]
            imm = int(imm, 2)
            imm -= 2 ** 11
        else:
            imm = (cmd[8:12] + cmd[25:31] + cmd[7] + cmd[31])[::-1] + "0"
        rs1 = cmd[15:20]
        rs2 = cmd[20:25]

        return self.name + " " + ", ".join(map(str, [Register(rs1), Register(rs2), Immediate(imm)]))

    @staticmethod
    def get_key_values(cmd):
        return Opcode(cmd[0:7]), Funct3(cmd[12:15])


class UType(Command):
    def __init__(self, name, opcode: Opcode):
        super().__init__(name, "U")
        self.opcode = opcode

    def parse(self, cmd):
        rd = cmd[7:12]
        # imm = bin(int(cmd[12:32], 2) << 12)[2:].rjust(33, "0")
        imm = cmd[12:32]

        return self.name + " " + str(Register(rd)) + ", " + str(Immediate(imm, repr_radix=16))

    @staticmethod
    def get_key_values(cmd):
        return Opcode(cmd[0:7])


class JType(Command):
    def __init__(self, name, opcode: Opcode):
        super().__init__(name, "J")
        self.opcode = opcode

    def parse(self, cmd: Instruction):
        rd = cmd[7:12]
        imm = "0" + cmd[12:]
        imm = imm[20] + imm[1:10] + imm[11] + imm[12:19]
        # print(imm)
        # imm = bin(int(imm[::-1], 2) << 1)[2:].rjust(len(imm) + 1, "0")
        return self.name + " " + str(Register(rd)) + " " + str(Immediate(imm, repr_radix=2))

    @staticmethod
    def get_key_values(cmd):
        return Opcode(cmd[0:7])


class CompressedCommand(Command):
    def __init__(self, name, opcode: Opcode, ):
        super().__init__(name, "C")

    def parse(self, cmd):
        pass

    @staticmethod
    def get_key_values(cmd):
        pass


class SystemType(Command):
    def __init__(self, name, opcode: Opcode, value):
        super().__init__(name, "I")
        self.opcode = opcode
        self.value = value

    def parse(self, cmd):
        return self.name

    @staticmethod
    def get_key_values(cmd):
        value = cmd[20:32]
        return Opcode(cmd[0:7]), Const(value, 2, 12)


class CommandList:
    def __init__(self, cmdlist):
        self.cmdlist = cmdlist

        def _get_keys(cmd: Command):
            if isinstance(cmd, RType):
                return cmd.opcode, cmd.funct3, cmd.funct7
            elif isinstance(cmd, IType):
                return cmd.opcode, cmd.funct3, cmd.funct7
            elif isinstance(cmd, SType):
                return cmd.opcode, cmd.funct3
            elif isinstance(cmd, BType):
                return cmd.opcode, cmd.funct3
            elif isinstance(cmd, UType):
                return cmd.opcode
            elif isinstance(cmd, JType):
                return cmd.opcode
            elif isinstance(cmd, SystemType):
                return cmd.opcode, cmd.value

        self._cmdmap = dict((_get_keys(cmd), cmd) for cmd in cmdlist)
        self._opcodes = dict((cmd.opcode, type(cmd)) for cmd in cmdlist)

        print(self._opcodes)
        print(self._cmdmap)

    def get_command(self, item: tuple) -> Command:
        res = self._cmdmap.get(item)
        if not res:
            return UnknownCommand(item)
        return res

    def get_command_type(self, opcode) -> Command:
        return self._opcodes.get(opcode)


# https://github.com/MPSU/APS-info/blob/master/lect-pm/pic/isariscv.png

CMDLIST = CommandList([
    # RTYPE:
    RType("add", Funct3(0), Funct7(0), Opcode(RTYPE_OPCODE)),
    RType("sub", Funct3(0), Funct7(20), Opcode(RTYPE_OPCODE)),
    RType("xor", Funct3(4), Funct7(0), Opcode(RTYPE_OPCODE)),
    RType("or", Funct3(6), Funct7(0), Opcode(RTYPE_OPCODE)),
    RType("and", Funct3(7), Funct7(0), Opcode(RTYPE_OPCODE)),
    RType("sll", Funct3(1), Funct7(0), Opcode(RTYPE_OPCODE)),
    RType("srl", Funct3(5), Funct7(0), Opcode(RTYPE_OPCODE)),
    RType("sra", Funct3(5), Funct7(20), Opcode(RTYPE_OPCODE)),
    RType("slt", Funct3(2), Funct7(0), Opcode(RTYPE_OPCODE)),
    RType("sltu", Funct3(3), Funct7(0), Opcode(RTYPE_OPCODE)),
    # IType group 1:
    IType("addi", Funct3(0), None, Opcode(ITYPE_OPCODE_GROUP1)),
    IType("xori", Funct3(4), None, Opcode(ITYPE_OPCODE_GROUP1)),
    IType("ori", Funct3(6), None, Opcode(ITYPE_OPCODE_GROUP1)),
    IType("andi", Funct3(7), None, Opcode(ITYPE_OPCODE_GROUP1)),
    IType("slli", Funct3(1), Funct7(0), Opcode(ITYPE_OPCODE_GROUP1)),
    IType("srli", Funct3(5), Funct7(0), Opcode(ITYPE_OPCODE_GROUP1)),
    IType("srai", Funct3(5), Funct7(20), Opcode(ITYPE_OPCODE_GROUP1)),
    IType("slti", Funct3(2), None, Opcode(ITYPE_OPCODE_GROUP1)),
    IType("sltiu", Funct3(3), None, Opcode(ITYPE_OPCODE_GROUP1)),
    # ITYPE group 2:
    IType("lb", Funct3(0), None, Opcode(ITYPE_OPCODE_GROUP2)),
    IType("lh", Funct3(1), None, Opcode(ITYPE_OPCODE_GROUP2)),
    IType("lw", Funct3(2), None, Opcode(ITYPE_OPCODE_GROUP2)),
    IType("lbu", Funct3(4), None, Opcode(ITYPE_OPCODE_GROUP2)),
    IType("lbh", Funct3(5), None, Opcode(ITYPE_OPCODE_GROUP2)),
    # SType:
    SType("sb", Funct3(0), Opcode(STYPE_OPCODE)),
    SType("sh", Funct3(1), Opcode(STYPE_OPCODE)),
    SType("sw", Funct3(2), Opcode(STYPE_OPCODE)),
    # BType:
    BType("beq", Funct3(0), Opcode(BTYPE_OPCODE)),
    BType("bne", Funct3(1), Opcode(BTYPE_OPCODE)),
    BType("blt", Funct3(4), Opcode(BTYPE_OPCODE)),
    BType("bge", Funct3(5), Opcode(BTYPE_OPCODE)),
    BType("bltu", Funct3(6), Opcode(BTYPE_OPCODE)),
    BType("bgeu", Funct3(7), Opcode(BTYPE_OPCODE)),
    # JType and IType group:
    JType("jal", Opcode(JAL_OPCODE)),
    IType("jalr", Funct3(0), None, Opcode(JALR_OPCODE)),
    # UType:
    UType("lui", Opcode(LUI_OPCODE)),
    UType("auipc", Opcode(AUIPC_OPCODE)),
    # ecall, ebreak:
    SystemType("ecall", Opcode(SYSTEM_OPCODE), Const(0, 10, 12)),
    SystemType("ebreak", Opcode(SYSTEM_OPCODE), Const(1, 10, 12)),

    # RV32M
    RType("mul", Funct3(0), Funct7(1), Opcode(RV32M_OPCODE)),
    RType("mulh", Funct3(1), Funct7(1), Opcode(RV32M_OPCODE)),
    RType("mulhsu", Funct3(2), Funct7(1), Opcode(RV32M_OPCODE)),
    RType("mulhu", Funct3(3), Funct7(1), Opcode(RV32M_OPCODE)),
    RType("div", Funct3(4), Funct7(1), Opcode(RV32M_OPCODE)),
    RType("divu", Funct3(5), Funct7(1), Opcode(RV32M_OPCODE)),
    RType("rem", Funct3(6), Funct7(1), Opcode(RV32M_OPCODE)),
    RType("remu", Funct3(7), Funct7(1), Opcode(RV32M_OPCODE))

])


def is_compressed(line):
    # todo compressed
    return False


def parse_line(line):
    instruction = Instruction(line[::-1])
    opcode = instruction[0:7]
    cmd = CMDLIST.get_command(
        CMDLIST.get_command_type(Opcode(opcode)).get_key_values(instruction)
    )

    return cmd.parse(instruction)
