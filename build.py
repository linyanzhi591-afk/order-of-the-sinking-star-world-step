"""构建独立原生载荷；安装和游玩不需要编译器。"""
import base64
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
BIN = Path(r'C:\Program Files (x86)\mingw64\bin')
SYMBOLS = dict(iat_module=0x7c0258, iat_proc=0x7c0260, iat_pid=0x7c01f8,
               iat_key=0x7c0000, native_step=0x8022e4, game_delta=0x804018,
               delta_return=0x26246a, positive_loop=0x26427d, after_loop=0x264002)

def build():
    variants = {}
    with tempfile.TemporaryDirectory(dir=ROOT, prefix='tmp-build-') as directory:
        tmp = Path(directory)
        for source in ('world_step.c', 'world_step.S'):
            subprocess.run([str(BIN/'gcc.exe'), '-c', '-O2', '-mcmodel=small', '-ffreestanding',
                            '-fno-stack-protector', '-fno-asynchronous-unwind-tables', '-fno-ident',
                            str(ROOT/source), '-o', str(tmp/(source+'.o'))], check=True)
        for rva in (0x113c000, 0x1146000, 0x1143000):
            script = tmp/'layout.ld'
            script.write_text(f'SECTIONS {{ .text {rva:#x} : {{ *(.text*) *(.rdata*) }} .data {rva+0x2000:#x} : {{ *(.data*) *(.bss*) }} /DISCARD/ : {{ *(.eh_frame*) *(.pdata*) *(.xdata*) }} }}')
            exe = tmp/'payload.exe'
            defs = [a for name, value in SYMBOLS.items() for a in ('--defsym', f'{name}={value:#x}')]
            subprocess.run([str(BIN/'ld.exe'), '-mi386pep', '--image-base', '0', '-T', str(script),
                            *defs, '--entry', 'world_delta_hook', '--disable-auto-import',
                            str(tmp/'world_step.c.o'), str(tmp/'world_step.S.o'), '-o', str(exe)], check=True)
            b = exe.read_bytes()
            pe = struct.unpack_from('<I', b, 60)[0]
            assert struct.unpack_from('<II', b, pe+24+112+5*8) == (0, 0), '载荷不能包含重定位'
            table = pe+24+struct.unpack_from('<H', b, pe+20)[0]
            blob = bytearray(0x3000)
            for i in range(struct.unpack_from('<H', b, pe+6)[0]):
                off = table+i*40
                name, size, address, rawsize, raw = struct.unpack_from('<8sIIII', b, off)
                name = name.rstrip(b'\0').decode()
                if name == '.idata':
                    assert not any(b[raw:raw+size])
                    continue
                assert name in ('.text', '.data') and rva <= address < rva+0x3000
                assert address-rva+size <= len(blob)
                blob[address-rva:address-rva+size] = b[raw:raw+size]
            symbols = {}
            for line in subprocess.check_output([str(BIN/'nm.exe'), str(exe)], text=True).splitlines():
                fields = line.split()
                if len(fields) == 3 and fields[2] in ('world_delta_hook', 'world_gate_hook', 'world_filter', 'world_settings'):
                    symbols[fields[2]] = int(fields[0], 16)
            assert len(symbols) == 4
            variants[str(rva)] = dict(rva=rva, data=base64.b64encode(blob).decode(), symbols=symbols)
    output = ROOT/'payload.json'
    output.write_text(json.dumps(variants, indent=2)+'\n', encoding='utf8', newline='\n')
    print('载荷 SHA-256：', hashlib.sha256(output.read_bytes()).hexdigest())

if __name__ == '__main__':
    build()
