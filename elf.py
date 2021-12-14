from exceptions import *
import commands as cmd
import typing

HEADER_SECTION_LENGTH = 16
COMMAND_SIZE = 4
COMPRESSED_COMMAND_SIZE = 2
ENDIAN = "little"


class SHTConsts:
    NAME_TEXT = int.from_bytes(bytes("\x1b\x00\x00\x00", encoding="raw_unicode_escape"), ENDIAN)
    NAME_SYMTAB = int.from_bytes(bytes("\x01\x00\x00\x00", encoding="raw_unicode_escape"), ENDIAN)
    NAME_STRTAB = int.from_bytes(bytes("\x09\x00\x00\x00", encoding="raw_unicode_escape"), ENDIAN)
    TYPE_PROGBITS = int.from_bytes(bytes("\x01\x00\x00\x00", encoding="raw_unicode_escape"), ENDIAN)
    TYPE_SYMTAB = int.from_bytes(bytes("\x02\x00\x00\x00", encoding="raw_unicode_escape"), ENDIAN)
    TYPE_STRTAB = int.from_bytes(bytes("\x03\x00\x00\x00", encoding="raw_unicode_escape"), ENDIAN)


class ByteArray:
    def __init__(self, arr):
        self.__arr = arr

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.__arr[item]
        elif isinstance(item, slice):
            return b"".join(self.__arr[item])

    def get_slice(self, f, t):
        return ByteArray(self.__arr[f:t])

    def __repr__(self):
        return str(self.__arr)


class SectionHeaderElement:
    def __init__(self, line: ByteArray):
        self.__line = line
        self.__OFFSET = 4
        self.__cursor = 0

        self.name = self.take4()
        self.type = self.take4()
        self.flags = self.take4()
        self.address = self.take4()
        self.offset = self.take4()
        self.size = self.take4()
        self.link = self.take4()
        self.info = self.take4()
        self.addralign = self.take4()
        self.entsize = self.take4()
        # print(self)

    def int_offset(self):
        return int.from_bytes(self.offset, ENDIAN)

    def int_name(self):
        return int.from_bytes(self.name, ENDIAN)

    def int_size(self):
        return int.from_bytes(self.size, ENDIAN)

    def is_text(self):
        # print(int.from_bytes(self.name, ENDIAN), SHTConsts.NAME_TEXT)
        return int.from_bytes(self.name, ENDIAN) == SHTConsts.NAME_TEXT

    def is_symtab(self):
        return int.from_bytes(self.name, ENDIAN) == SHTConsts.NAME_SYMTAB

    def is_strtab(self):
        return int.from_bytes(self.name, ENDIAN) == SHTConsts.NAME_STRTAB

    def take4(self):
        self.__cursor += self.__OFFSET
        return self.__line[self.__cursor - self.__OFFSET:self.__cursor]

    def __repr__(self):
        return " ".join(map(lambda x: hex(x)[2:].rjust(8, "0"),
                            [int.from_bytes(el, "big") for el in [self.type, self.address, self.offset, self.size]]))


class SymtabElement:
    def __init__(self, line: ByteArray, get_name):
        self.__cursor = 0
        self.__line = line
        name = int.from_bytes(self.take(4), ENDIAN)
        if name == 0:
            self.name = ""
        else:
            self.name = get_name(name)
        self.value = int.from_bytes(self.take(4), ENDIAN)
        self.size = int.from_bytes(self.take(4), ENDIAN)
        self.info = self.take(1)
        self.other = self.take(1)
        self.__shndx = self.take(2)

        self.binding = None
        self.type = None
        self.visibility = None

        self.parse_info()
        self.parse_shndx()

    def take(self, b):
        self.__cursor += b
        return self.__line[self.__cursor - b:self.__cursor]

    @property
    def shndx(self):
        if isinstance(self.__shndx, str):
            return self.__shndx
        else:
            return str(self.__shndx)

    def parse_info(self):
        bindings = {
            0: "LOCAL",
            1: "GLOBAL",
            2: "WEAK",
            10: "LOOS",
            12: "HIOS",
            13: "LOPROC",
            15: "HIPROC"
        }
        types = {
            0: "NOTYPE",
            1: "OBJECT",
            2: "FUNC",
            3: "SECTION",
            4: "FILE",
            5: "COMMON",
            6: "TLS",
            10: "LOOS",
            12: "HIOS",
            13: "LOPROC",
            15: "HIPROC"
        }
        visibilities = {
            0: "DEFAULT",
            1: "INTERNAL",
            2: "HIDDEN",
            3: "PROTECTED"
        }

        self.binding = bindings.get(int.from_bytes(self.info, ENDIAN) >> 4)
        self.type = types.get(int.from_bytes(self.info, ENDIAN) & 15)
        self.visibility = visibilities.get(int.from_bytes(self.other, ENDIAN) & 3)

    def parse_shndx(self):
        m = {
            0: "UNDEF",
            65521: "ABS"
        }
        if isinstance(self.__shndx, bytes):
            self.__shndx = int.from_bytes(self.__shndx, ENDIAN)
        a = m.get(self.__shndx)
        if a:
            self.__shndx = a

    def __repr__(self):
        return self.name + " " + hex(self.value) + " ".join(
            [str(self.size), self.binding, self.type, self.visibility]) + " " + self.shndx

    def as_list(self) -> typing.List:
        return [self.value, self.size, self.type, self.binding, self.visibility, self.shndx, self.name]


class ElfFile:
    # noinspection PyTypeChecker
    def __init__(self, file):
        arr = []
        byte = file.read(1)
        while byte != b"":
            # print(byte)
            arr.append(byte)
            byte = file.read(1)
        self.__arr = ByteArray(arr)

        self.e_shoff = None
        self.e_shnum = None
        self.e_shentsize = 40

        self.text_header: SectionHeaderElement = None
        self.symtab_header: SectionHeaderElement = None
        self.strtab_header: SectionHeaderElement = None

    def parse_header(self):
        self.e_shoff = int.from_bytes(self.__arr[16 + 4 * 4:16 + 4 * 5], ENDIAN)
        self.e_shnum = int.from_bytes(self.__arr[16 + 4 * 8:16 + 4 * 8 + 2], ENDIAN)
        self.e_shentsize = int.from_bytes(self.__arr[16 + 4 * 8 - 2:16 + 4 * 8], ENDIAN)
        # print(self.e_shoff, self.e_shnum, self.e_shentsize)

    def parse_section_header_table(self):
        arr = []
        for i in range(self.e_shnum):
            ba = self.__arr.get_slice(self.e_shoff + i * self.e_shentsize, self.e_shoff + self.e_shentsize * (i + 1))
            shc = SectionHeaderElement(ba)
            arr.append(shc)
            if shc.is_text():
                self.text_header = shc
            elif shc.is_symtab():
                self.symtab_header = shc
            elif shc.is_strtab():
                self.strtab_header = shc

        if not (self.strtab_header and self.symtab_header and self.text_header):
            print(self.text_header)
            print(self.symtab_header)
            print(self.strtab_header)
            raise BadSectionHeaderTable("\n".join(map(str, arr)))

    def parse_commands(self):
        def __take(cursor):
            cursor += COMMAND_SIZE
            return cursor, self.__arr[cursor - COMMAND_SIZE:cursor]

        def __take_compressed(cursor):
            cursor += COMPRESSED_COMMAND_SIZE
            return cursor, self.__arr[cursor - COMPRESSED_COMMAND_SIZE:cursor]

        def __check_compressed():
            return cmd.is_compressed(self.__arr[cursor:cursor + COMMAND_SIZE])

        res = []
        offset = int.from_bytes(self.text_header.offset, ENDIAN)
        print(offset)
        size = int.from_bytes(self.text_header.size, ENDIAN)
        cursor = offset
        while cursor < offset + size:
            if __check_compressed():
                cursor, command = __take_compressed(cursor)
            else:
                cursor, command = __take(cursor)

            res.append((hex(cursor - 4), cmd.parse_line(bin(int.from_bytes(command, "little"))[2:].rjust(COMMAND_SIZE * 8, "0"))))
        return res

    def parse_symtab(self):
        cursor = self.symtab_header.int_offset()
        res = []
        while cursor < self.symtab_header.int_size() + self.symtab_header.int_offset():
            el = SymtabElement(self.__arr[cursor:cursor + 16], self.get_name_form_strtab)
            # print(el)
            res.append(el)
            cursor += 16

        return res

    def get_name_form_strtab(self, start):
        offset = self.strtab_header.int_offset()
        size = self.strtab_header.int_size()
        cursor = start + self.strtab_header.int_offset()
        w = b""
        while cursor < offset + size:
            symbol = self.__arr[cursor]
            if symbol == b"\x00":
                break
            else:
                w += symbol
            cursor += 1
        return w.decode("utf-8")


def parse(filename: str) -> (typing.List[typing.Tuple], typing.List[SymtabElement]):
    with open(filename, "rb") as f:
        file = ElfFile(f)
        file.parse_header()
        file.parse_section_header_table()
        symtab = file.parse_symtab()
        cmds = file.parse_commands()
        return cmds, symtab
