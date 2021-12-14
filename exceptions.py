# command parse exceptions
class UnknownCommandException(Exception):
    pass


# elf file parse exceptions
class BadSectionHeaderTable(Exception):
    pass
