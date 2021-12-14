import commands


with open("test.bin") as inp:
    def _reverse_line(line):
        return line[::-1]

    for line in inp.readlines():
        line = line.strip()
        print(commands.parse_line(line))

    # for line in inp.readlines():
    #     line = line.strip().replace(" ", "").split(":")[1][:9]
    #     print(line)
