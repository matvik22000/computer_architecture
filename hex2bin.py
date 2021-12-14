with open('test.hex') as h, open('test.bin', 'w') as b:
    f = True
    for line in h.readlines():
        if not f: b.write("\n")
        else: f = False
        line = line.strip().replace(" ", "").replace("\t", "").split(":")[1][:8]
        # print(line)
        b.write(bin(int(line, 16))[2:].rjust(32, "0"))
        # print(len(bin(int(line, 16))[2:].rjust(32, "0")))
