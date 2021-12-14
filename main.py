from elf import *
import typing


def main(filename):
    commands, symtab = parse(filename)
    print(*commands, sep="\n")
    print(format_symtab(symtab))


def format_symtab(symtab: typing.List[SymtabElement]):
    header_f = "%s %-15s %7s %-8s %-8s %-8s %6s %s\n"
    row_f = "[%4i] 0x%-15X %5i %-8s %-8s %-8s %6s %s\n"
    res = ""
    for i, el in enumerate(symtab):
        # noinspection PyStringFormat
        res += "[%4i] 0x%-15X %5i %-8s %-8s %-8s %6s %s\n" % (i, *el.as_list())

    return res


if __name__ == '__main__':
    main("test.elf")
