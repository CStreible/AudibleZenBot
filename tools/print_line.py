import sys
if len(sys.argv) < 3:
    print('usage: print_line.py <line> <file> [end]')
    sys.exit(2)
start=int(sys.argv[1])
path=sys.argv[2]
end=None
if len(sys.argv) >=4:
    end=int(sys.argv[3])
with open(path,'r',encoding='utf-8') as f:
    lines=f.readlines()
if end is None:
    end = start
for i in range(start-1, end):
    print(f"{i+1:4}: {repr(lines[i])}")
